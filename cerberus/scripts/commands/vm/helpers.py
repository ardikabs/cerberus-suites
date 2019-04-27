
import time
import click
import random
import ipaddress
import subprocess
import multiprocessing

from cerberus import phpipam
from cerberus.provisioner.core import KnifeBootstrap
from cerberus.scripts.config import ConfigFileProcessor
from cerberus.utils import parser
from cerberus.vsphere import errors

from cerberus.scripts.utils import (
    prompt_y_n_question,
    Threading
)
from .services import init_vm_service
from ..ipam.services import init_ipam_service
from ..dns.services import init_dns_service

def show_vm(vm_data):
    if isinstance(vm_data, list):
        output = parser.BeautifyFormat.from_dict(
            vm_data,
            headers=["UUID", "STATUS", "IP", "NAME"],
            attr=["config.uuid", "runtime.powerState", "guest.net", "name"]
        )
    else:
        output = parser.BeautifyFormat.from_object(
            vm_data,
            headers=["UUID", "STATUS", "IP", "NAME"],
            attr=["config.uuid", "runtime.powerState", "guest.ipAddress", "name"]
        )
    click.clear()
    click.echo("\n".join(output))

def show_vm_result(results):
    for result in results:
        if not result.get("bootstrap"):
            result["bootstrap"] = "NOT YET"

    output = parser.BeautifyFormat.from_dict(
        results,
        headers=["FQDN", "IP", "NAME", "BOOTSTRAP"],
        attr=["network.fqdn", "network.address", "name", "bootstrap"],
        nested=True
    )
    click.clear()
    click.echo("\n".join(output))

def setup_service(config):
    vcenter_obj = config["vcenter"]
    service = init_vm_service(vcenter_obj)
    service.connect(
        user=vcenter_obj.get('user'),
        pwd=vcenter_obj.get('pwd')
    )
    service.datacenter = vcenter_obj.get("datacenter")
    return service

def importing_vm(config):
    service = setup_service(config)
    return service.lookup_vms()

def searching_vm(config, vm_name=None, ipaddr=None, hostname=None, uuid=None, insecure=None):
    service = setup_service(config)
    if vm_name:
        result = service.search_vms(name=vm_name)
    elif uuid:
        result = service.search_vm(uuid=uuid)
    elif ipaddr:
        if insecure: 
            result = service.search_vms(ipaddr=ipaddr)
        else: 
            result = service.search_vm(ipaddr=ipaddr)
        
    elif hostname:
        if insecure: 
            result = service.search_vms(hostname=hostname)
        else: 
            result = service.search_vms(fqdn=hostname)
    else:
        raise click.ClickException(
            message="Option or VM_NAME are needed"
        )
    return result or []

def poweringon_vm(config, vm):
    vmname = vm.name
    service = setup_service(config)
    result = service.wait_for_task("Powering On", vm.PowerOnVM_Task())
    return f"Powering On {vm.name}"

def poweringoff_vm(config, vm):
    vmname = vm.name
    service = setup_service(config)
    result = service.wait_for_task("Powering Off", vm.PowerOffVM_Task())
    return f"Powering Off {vmname}"
    
def restarting_vm(config, vm):
    vmname = vm.name
    service = setup_service(config)
    try:
        result = service.wait_for_task("Rebooting", vm.RebootGuest())
    except:
        result = service.wait_for_task("Restarting", vm.ResetVM_Task())
    return f"Restarting {vmname}"

def use_config(conf):
    global gconfig
    gconfig = conf

def creating_vm(config, specs, paralel=3):
    pool = multiprocessing.Pool(processes=paralel, initializer=use_config, initargs=(config,))
    result = pool.map(multi_create_vm, specs)
    return result

def destroying_vm(config, vms, paralel=3, **kwargs):
    specs = map(vm2dict, vms)
    pool = multiprocessing.Pool(processes=paralel, initializer=use_config, initargs=(config,))
    result = pool.map(multi_destroy_vm, specs)
    return result

def waiting_vm(specs, paralel=3):
    addresses = [spec.get('network',{}).get('address') for spec in specs]
    pool = multiprocessing.Pool(processes=paralel)
    result = pool.map(wait_to_live, addresses)
    return specs

def multi_create_vm(spec):
    if not spec.get("datastore") and not spec.get("datastore_cluster"):
        err = AttributeError("Datastore or Datastore are not set")
        raise err

    global gconfig
    
    _network = spec.get("network")

    ipam_obj = gconfig["phpipam"]
    zone_obj = gconfig[f"dns.zones.{_network.get('domain')}"]

    vsphere_service = setup_service(gconfig)
    ipam_service = init_ipam_service(ipam_obj)
    dns_service = init_dns_service(zone_obj)


    # Select VM Template
    template = vsphere_service.use_template(
        template_name=spec.get("template"), 
        template_folder=spec.get("template_path")
    )
    # Select Network Device
    network = vsphere_service.use_network(_network.get("name"))

    # Select Destination Folder
    folder = vsphere_service.use_folder(spec.get("folder"))

    # Select Compute Resource
    compute = vsphere_service.use_compute(spec.get("compute"))

    # Select Storage if N/A, just use template storage
    storage = vsphere_service.use_storage(spec.get("datastore"))

    # Setup the network configuration
    subnet = ipam_service.show_subnet(cidr=_network.get("cidr"))
    _network["subnet_id"] = subnet.id
    _network["fqdn"] = f"{spec.get('hostname')}.{_network.get('domain')}"

    network_config = dict(
        dns_domain=_network.get("domain"),
        dns_server=_network.get("dns")
    )

    if not _network.get("dhcp"):
        # Setup address if dhcp is not set
        ipaddr = ipam_service.reserve_ipaddr(
            subnet_id=subnet.id
        ).data

        _network["address"] = ipaddr

        network_config = dict(network_config,
            ipv4_address=ipaddr,
            gateway_address=subnet.gateway.ip_addr,
            subnet_mask=getattr(subnet.calculation, "Subnet netmask")
        )

    # Try/Except used for checking if virtual machine cloning task have an error, 
    # will delete an IP Address on IPAM Server as well

    try:
        clone_name = spec.get("name")
        vm = None

        # Attributes for Virtual Machine Specification
        attributes = dict(
            hostname=spec.get("hostname"),
            domain=_network.get("domain"),
            num_cpus=spec.get("num_cpus"),
            memory=spec.get("memory"),
            dhcp=_network.get("dhcp", False),
            network_config=network_config
        )

        # Setup Specification (ConfigSpec, CustomSpec, CloneSpec)
        configspec, customspec, clonespec = vsphere_service.setup_specifications(
            storage=storage,
            network=network,
            compute=compute,
            **attributes
        )

        if not storage and spec.get("datastore_cluster"):
            vm = vsphere_service.clone_vm_with_sdrs(
                name=clone_name, 
                template=template, 
                folder=folder, 
                clonespec=clonespec,
                dscluster=spec.get("datastore_cluster")
            )
        else:
            vm = vsphere_service.clone_vm(
                name=clone_name, 
                template=template, 
                folder=folder, 
                clonespec=clonespec
            )
        
        # VM Reconfiguring Task
        configuring = vsphere_service.wait_for_task(
            f"VM Reconfiguring {clone_name}",
            vm.ReconfigVM_Task(spec=configspec)
        )
        
        # VM Customizing Task
        costumizing = vsphere_service.wait_for_task(
            f"VM Customizing {clone_name}",
            vm.CustomizeVM_Task(spec=customspec)
        )

        # VM PoweringOn Task
        poweringon = vsphere_service.wait_for_task(
            f"Powering On {clone_name}", 
            vm.PowerOnVM_Task()
        )
        
        while True:
            address = vm.guest.ipAddress
            if address is not None:
                _network["address"] = vm.guest.ipAddress
                break

        post_creating(
            config=gconfig, 
            **dict(
                hostname=spec.get("hostname"),
                network=_network
            )
        )

        spec["network"] = _network

    except Exception as exc:
        ipam_service.release_ipaddr(
            address=_network.get("address"),
            subnet_id=_network.get("subnet_id")
        )
        raise RuntimeError(exc)
    
    return spec

def multi_destroy_vm(spec):
    global gconfig

    name = spec["name"]
    uuid = spec["uuid"]
    hostname = spec["hostname"]
    addresses = spec["network"]["addresses"]

    force = gconfig["force"]

    try:
        ipam_service = init_ipam_service(gconfig["phpipam"])
        ipaddr = None
        for address in addresses:
            try:
                result = ipam_service.show_ipaddr(address=address)
            except phpipam.errors.NotFound:
                continue
            else:
                ipaddr = result[0]
                spec["network"] = dict(address=address)
                break
        
        if not ipaddr:
            err = ValueError("Unable to destroy virtual machine! (Network adapter is not running or Virtual machine not alive)")
            raise err

        if hostname != ipaddr.hostname:
            err = ValueError(f"Unable to destroy virtual machine! Virtual machine hostname and IPAM record are not match ({hostname}:{ipaddr.hostname})")
            raise err
        
        records = []
        for zone in gconfig["dns.zones"]["available"]:
            section = f"dns.zones.{zone}"
            zone_obj = ConfigFileProcessor.select_storage_for(section, gconfig)
            service = init_dns_service(zone_obj)
            records.extend(service.import_records())

        record = list(filter(lambda rec: rec.get('content') == ipaddr.ip, records))

        ipam_service.release_ipaddr(ipaddr.ip, subnet_id=ipaddr.subnetId)
        
        if record:
            record = record[0]
            dns_service = init_dns_service(gconfig[f"dns.zones.{record.get('zone')}"])
            dns_service.remove_record(
                name=record.get('name'),
                rtype=record.get('rtype')
            )

            spec["fqdn"] = f"{record.get('name')}.{record.get('zone')}"
            debootstraping_vm(gconfig, spec)         
    except Exception as err:
        if not force:
            raise err
    finally:
        vsphere_service = setup_service(gconfig)
        task = vsphere_service.delete_vm(uuid=uuid)
        return spec

def bootstraping_vm(config, specs, paralel=3):
    pool = multiprocessing.Pool(processes=paralel, initializer=use_config, initargs=(config,))
    result = pool.map(multi_bootstrap_vm, specs)
    return result

def multi_bootstrap_vm(spec):
    global gconfig

    _environment = str.lower(spec.get('environment'))
    _category = str.lower(spec.get('category'))
    _ipaddr = spec.get("network").get("address") if spec.get("network") else spec.get("address")
    _fqdn = spec.get("network").get("fqdn") if spec.get("network") else spec.get("fqdn")

    knife_obj = gconfig["knife"]
    knife_env = gconfig[f"knife.environments.{_environment}"]
    knife_cat = gconfig.get(f"knife.category.{_environment}.{_category}", {})
    runlist = knife_cat.get("runlist") if knife_cat.get("runlist") else knife_env.get("runlist") 

    kbootstrap = KnifeBootstrap(
        debug=spec.get('debug', False), 
        show_err=spec.get('show_err', False)
    )

    try:
        result = kbootstrap.create(
            ssh_user=knife_obj.get("ssh_user"),
            ssh_pwd=knife_obj.get("ssh_pwd"),
            ssh_port=knife_obj.get("ssh_port"),
            databag_secret_path=knife_obj.get("databag_secret_path"),
            environment=knife_env.get("name"),
            chef_environment=knife_env.get("chef_environment"),
            ipaddr=_ipaddr,
            fqdn=_fqdn,
            runlist=runlist
        )
    except:
        spec["bootstrap"] = "ERROR"
    else:
        spec["bootstrap"] = "DONE"

    return spec

def debootstraping_vm(config, spec):
    _fqdn = spec.get('fqdn')
    knife_obj = config["knife"]
    kbootstrap = KnifeBootstrap(
        debug=spec.get("debug", False),
        show_err=spec.get('show_err', False)
    )

    try:
        result = kbootstrap.delete(_fqdn)
    except:
        spec["debootstrap"] = "ERROR"
    else:
        spec["debootstrap"] = "DONE"

    return spec

def post_creating(config, **kwargs):
    # When creation virtual machine is success
    network = kwargs.get("network")

    ipam_obj = config["phpipam"]
    ipam_service = init_ipam_service(ipam_obj)

    # phpIPAM Section
    # Update an ip address of the virtual machine with additional information (hostname, description, note)
    payload={
        "hostname": kwargs.get("hostname"),
        "description": "This IP Address managed by Cerberus Suites.",
        "note": "Don't make change on this IP Address directly!" 
    }
    
    try:
        if not network.get("dhcp", False):
            result = ipam_service.update_ipaddr(
                address=network.get("address"),
                subnet_id=network.get("subnet_id"),
                payload=payload
            )
        else:
            result = ipam_service.add_ipaddr(
                subnet_id=network.get("subnet_id"),
                payload=dict(payload, ip=network.get("address"))
            )
    except Exception as exc:
        click.echo(f"Raise error on phpIPAM server: {exc}")
    
    # DNS Section
    # Create a FQDN for virtual machine server
    try:
        zone_obj = config[f"dns.zones.{network.get('domain')}"]
        dns_service = init_dns_service(zone_obj)
        result, err = dns_service.add_record(
            name=kwargs.get('hostname'),
            content=network.get("address"),
            rtype=zone_obj.get("rtype") if zone_obj.get("rtype") else config["dns"].get("rtype", "A"),
            ttl=zone_obj.get("ttl") if zone_obj.get("ttl") else config["dns"].get("ttl", 300)
        )

        if err: 
            raise click.exceptions.UsageError(result)
    except Exception as exc:
        click.echo(f"Raise error on DNS server: {exc}")

def findip_from_dns(config, fqdn):
    split = fqdn.split(".")
    hostname = split[0]
    domain = ".".join(split[1:])
    zone_obj = config[f"dns.zones.{domain}"]
    service = init_dns_service(zone_obj)
    records = service.import_records()
    filtered = list(filter(lambda x: x.get('name') == hostname, records))
    if not filtered:
        raise click.ClickException(f"FQDN ({fqdn}) not found")

    data = filtered[0]
    return data.get('content')

def make_logs(config, data, action):
    import datetime

    vcenter_obj = config["vcenter"]
    try:
        logfiles = open(vcenter_obj["log"], "a+")
        for d in data:
            payload = vcenter_obj["log_format"].format(
                timestamp=datetime.datetime.now().isoformat(),
                action=action.upper(),
                user=vcenter_obj["user"],
                datacenter=vcenter_obj["datacenter"],
                vm_name=d["name"],
                address=d.get("network", {}).get("address", "<unidentified>")
            )
            logfiles.write(f"{payload}\n")
        logfiles.close()
    except Exception as e:
        raise click.ClickException(str(e))

def make_summary(specs):
    click.echo("\n==== Summary Virtual Machines ====")
    for spec in specs:
        click.echo(f"{spec.get('name') !r}")
        click.echo(f"\thostname: {spec.get('hostname') or '<unset>'}")
        click.echo(f"\tnum_cpus: {spec.get('num_cpus') or '<unset>'}")
        click.echo(f"\tmemory: {spec.get('memory') or '<unset>'}")
        click.echo(f"\tdatastore: { spec.get('datastore') or '<unset>'}")
        click.echo(f"\tdatastore_cluster: {spec.get('datastore_cluster') or '<unset>'}")
        click.echo(f"\tcompute: {spec.get('compute') or '<unset>'}")
        click.echo(f"\tnetwork: {spec.get('network',{}).get('name') or '<unset>'}")
        click.echo(f"\tnetwork.dhcp: {spec.get('network', {}).get('dhcp')}")
        click.echo(f"\tnetwork.cidr: {spec.get('network', {}).get('cidr') or '<unset>'}")
        click.echo(f"\tnetwork.fqdn: {spec['hostname']}.{spec['network']['domain']}")
        click.echo(f"\tnetwork.dns: {spec.get('network', {}).get('dns') or '<unset>'}")
        click.echo(f"\ttemplate: {spec.get('template') or '<unset>'}")
        click.echo(f"\ttemplate_path: {spec.get('template_path') or '<unset>'}")
        click.echo("\n")

def vm2dict(vm):
    network = list(filter(lambda net: net.connected and net.deviceConfigId == 4000, vm.guest.net))
    if not network:
        err = ValueError("Unable to destroy virtual machine cause virtual machine is not running!")
        raise err

    return {
        "uuid": vm.config.uuid,
        "name": vm.name,
        "hostname": vm.guest.hostName,
        "network": dict(addresses=list(network[0].ipAddress))
    }

def wait_to_live(ipaddr):
    if ipaddr is None:
        return
        
    temp = 0
    MAX_THRESHOLD = 50

    while True:

        try:
            output = subprocess.run(
                f"ping -c 1 {ipaddr} > /dev/null",
                shell=True,
                check=True
            ) 
        except subprocess.CalledProcessError as exc:
            pass
        else:
            if output.returncode != 0:
                temp += 1
                time.sleep(5)
            else:
                break
        
        if temp > MAX_THRESHOLD:
            raise RuntimeError(f"Reached MAX TIMEOUT. Unable to reach {ipaddr}")

def waiting_process(thread, title):
    start_t = time.time()
    for progress in thread.progress:
        time.sleep(random.randint(5,10))
        elapsed_t = time.strftime("%H:%M:%S", time.gmtime(time.time() - start_t))
        click.echo(f"{title} ({elapsed_t})")

        if thread.exception is not None:
            raise click.ClickException(thread.exception)
            
        if progress is not None:
            result = progress
            break
    return result