

import time
import click
from click_aliases import ClickAliasedGroup

from cerberus.scripts.utils import (
    prompt_y_n_question,
    Threading
)
from cerberus import __version__
from cerberus.scripts.config import ConfigFileProcessor
from . import (
    callbacks,
    services,
    helpers
)

@click.group("vm", help="Virtual Machine related operations", cls=ClickAliasedGroup)
@click.option("--vhost", "host", type=click.STRING, help="VMWare vSphere host")
@click.option("--vuser", "user", type=click.STRING, help="VMWare vSphere user")
@click.option("--vpass", "pwd", type=click.STRING, help="VMWare vSphere password")
@click.option("--vport", "port", default=443, type=click.INT, help="VMWare vSphere port", show_default=True)
@click.option("--vssl", "ssl", is_flag=True, help="VMWare vSphere SSL", show_default=True)
@click.option("--datacenter", type=click.STRING, help="VM vSphere Datacenter", show_default=True)
@click.pass_context
def cli(ctx, **parameters):
    required = ("host","port","user","pwd","ssl","datacenter",)
    config = ctx.obj["CONFIG"]
    vcenter_obj = config["vcenter"]
    for req in required:
        if req not in vcenter_obj:
            raise click.BadParameter(
                message=f"Variable ({req}) on configuration file are REQUIRED to interact with vCenter Server Appliance",
                param_hint=req
            )
    
    for k in parameters:
        if parameters[k]:
            vcenter_obj[k] = parameters[k]    
    
@cli.command("find", help="Find available virtual machine in vCenter Server Appliance")
@click.argument("vm_name", required=False, nargs=-1)
@click.option("--ipaddr", help="Virtual Machine IPv4 address")
@click.option("--hostname", help="Virtual Machine hostname")
@click.option("--uuid", help="Virtual Machine UUID Instance")
@click.option("-i","--insecure-search", "insecure", is_flag=True, help="Insecure Search (mean searching with ignoring vmware-tools)")
@click.pass_context
def find(ctx, vm_name, ipaddr, hostname, uuid, insecure):
    config = ctx.obj["CONFIG"]
    parameters = {
        "config": config, 
        "vm_name": vm_name, 
        "ipaddr": ipaddr, 
        "hostname": hostname, 
        "uuid": uuid, 
        "insecure": insecure
    }

    param = vm_name or ipaddr or hostname or uuid
    if not param:
        raise click.ClickException("No argument or option found")

    finding = Threading(helpers.searching_vm, **parameters)
    finding_progressbar = click.progressbar(finding.progress, label=f"Searching Virtual Machine ") 
    with finding_progressbar as progressbar:
        for progress in progressbar:
            if finding.exception:
                raise click.ClickException(finding.exception)

            if progress is not None: 
                result = progress
                break
    if not result:
        click.echo(f"No virtual machine are found")
        ctx.exit(1)
    helpers.show_vm(result)

@cli.command("start", help="Start a virtual machine in vCenter Server Appliance")
@click.argument("vm_name", required=False)
@click.option("--hostname", help="VM hostname")
@click.option("--uuid", help="VM UUID Instance")
@click.option("-i","--insecure-search", "insecure", is_flag=True, help="Insecure Search (mean searching with ignoring vmware-tools)")
@click.pass_context
def start(ctx, vm_name, uuid, hostname, insecure):
    config = ctx.obj["CONFIG"]
    parameters = {
        "config": config, 
        "vm_name": vm_name, 
        "hostname": hostname,
        "uuid": uuid,
        "insecure": insecure
    }

    param = vm_name or hostname or uuid
    searching = Threading(helpers.searching_vm, **parameters)
    searching_progressbar = click.progressbar(searching.progress, label=f"Searching Virtual Machine ") 
    with searching_progressbar as progressbar:
        for progress in progressbar:
            if searching.exception:
                raise click.ClickException(searching.exception)
                
            if progress is not None: 
                result = progress
                break

    if not result:
        raise click.ClickException()
        ctx.exit(1)

    if uuid:
        vm = result
    else:
        result = list(filter(lambda x: x['runtime.powerState'] == 'poweredOff', progress))
        
        click.echo(f"==> {len(result)} virtual machines found")
        for index, vm in enumerate(result):
            click.echo(f"[{index+1}] {vm['name']} ({ vm['guest.net'][0] if vm.get('guest.net') else '-'})")

        try:
            answer = int(input("Choose the index number of virtual machine to start: "))
            vm = result[answer-1]['obj']
        except:
            click.ClickException(
                message=f"Wrong choice. Abort!"
            )
        
        if vm.runtime.powerState == "poweredOn":
            click.echo(f"Virtual machine [{vm.name}] already {vm.runtime.powerState}")
            ctx.exit(0)    
    
    parameters = {
        "config": config,
        "vm": vm
    }

    poweringon = Threading(helpers.poweringon_vm, **parameters)
    poweringon_progressbar = click.progressbar(poweringon.progress, label=f"Starting Virtual Machine [{vm.name}]") 
    with poweringon_progressbar as progressbar:
        for progress in progressbar:
            if poweringon.exception:
                raise click.ClickException(poweringon.exception)

            if progress is not None: 
                result = progress
                break

    
    click.echo(f"Virtual machine [{vm.name}] already {vm.runtime.powerState}")    

@cli.command("restart", help="Restart a virtual machine in vCenter Server Appliance")
@click.argument("vm_name", required=False)
@click.option("--ipaddr", help="IP address for virtual machine")
@click.option("--hostname", help="VM hostname")
@click.option("--uuid", help="VM UUID Instance")
@click.option("-i","--insecure-search", "insecure", is_flag=True, help="Insecure Search (mean searching with ignoring vmware-tools)")
@click.option("-y", "--yes", is_flag=True, help="Answer yes for all prompt question")
@click.pass_context
def restart(ctx, vm_name, ipaddr, hostname, uuid, insecure, yes):
    config = ctx.obj["CONFIG"]
    config = ctx.obj["CONFIG"]
    parameters = {
        "config": config, 
        "vm_name": vm_name, 
        "ipaddr": ipaddr, 
        "hostname": hostname, 
        "uuid": uuid,
        "insecure": insecure
    }

    searching = Threading(helpers.searching_vm, **parameters)
    
    param = vm_name or ipaddr or hostname or uuid
    searching_progressbar = click.progressbar(searching.progress, label=f"Searching Virtual Machine ") 
    with searching_progressbar as progressbar:
        for progress in progressbar:
            if searching.exception:
                click.echo(f"Error: {searching.exception}")
                ctx.exit(1)
                break
                
            if progress is not None: 
                result = progress
                break

    if not result:
        raise click.ClickException()
        ctx.exit(1)

    if uuid:
        vm = result
    else:
        result = list(filter(lambda x: x['runtime.powerState'] == 'poweredOn', result))
        click.echo(f"==> {len(result)} virtual machines found")
        for index, vm in enumerate(result):        
            click.echo(f"[{index+1}] {vm['name']} ({ vm['guest.net'][0] if vm.get('guest.net') else '-'})")
        
        try:
            answer = int(input("Choose the index number of virtual machine to restart: "))
            vm = result[answer-1]['obj']
        except:
            raise click.ClickException(
                message=f"Wrong choice. Abort!"
            )
        
    answer = yes or prompt_y_n_question(
        f"Are you sure to stop virtual machine [{vm.name}] in datacenter [{config['vcenter']['datacenter']}] ?",
        default="no"
    )
    if not answer:
        ctx.exit(0)
    
    parameters = {
        "config": config,
        "vm": vm
    }

    restarting = Threading(helpers.restarting_vm, **parameters)
    restarting_progressbar = click.progressbar(restarting.progress, label=f"Restarting Virtual Machine [{vm.name}]") 
    with restarting_progressbar as progressbar:
        for progress in progressbar:
            if restarting.exception:
                raise click.ClickException(restarting.exception)

            if progress is not None: 
                result = progress
                break


    click.echo(f"Virtual machine [{vm.name}] restarted")

@cli.command("stop", help="Stop a virtual machine in vCenter Server Appliance")
@click.argument("vm_name")
@click.option("--ipaddr", help="IP address for virtual machine")
@click.option("--hostname", help="VM hostname")
@click.option("--uuid", help="VM UUID Instance")
@click.option("-i","--insecure-search", "insecure", is_flag=True, help="Insecure Search (mean searching with ignoring vmware-tools)")
@click.option("-y", "--yes", is_flag=True, help="Answer yes for all prompt question")
@click.pass_context
def stop(ctx, vm_name, ipaddr, hostname, uuid, insecure, yes):
    config = ctx.obj["CONFIG"]
    parameters = {
        "config": config, 
        "vm_name": vm_name, 
        "ipaddr": ipaddr, 
        "hostname": hostname, 
        "uuid": uuid,
        "insecure": insecure
    }

    
    param = vm_name or ipaddr or hostname or uuid
    searching = Threading(helpers.searching_vm, **parameters)
    searching_progressbar = click.progressbar(searching.progress, label=f"Searching Virtual Machine ") 
    with searching_progressbar as progressbar:
        for progress in progressbar:
            if searching.exception:
                raise click.ClickException(searching.exception)
                
            if progress is not None: 
                result = progress
                break

    if not result:
        click.echo(f"No virtual machine are found")
        ctx.exit(1)

    if uuid:
        vm = result
    else:
        result = list(filter(lambda x: x['runtime.powerState'] == 'poweredOn', progress))
        click.echo(f"==> {len(result)} virtual machines found")
        for index, vm in enumerate(result):        
            click.echo(f"[{index+1}] {vm['name']} ({ vm['guest.net'][0] if vm.get('guest.net') else '-'})")
        
        try:
            answer = int(input("Choose the index number of virtual machine to stop: "))
            vm = result[answer-1]['obj']
        except:
            raise click.ClickException(
                message=f"Wrong choice. Abort!"
            )

    if vm.runtime.powerState == "poweredOff":
        raise click.ClickException(
            message=f"Virtual machine [{vm.name}] already {vm.runtime.powerState}"
        )
    
    answer = yes or prompt_y_n_question(
        f"Are you sure to stop virtual machine [{vm.name}] in datacenter [{config['vcenter']['datacenter']}] ?",
        default="no"
    )
    if not answer:
        ctx.exit(0)
    
    parameters = {
        "config": config,
        "vm": vm
    }

    poweringoff = Threading(helpers.poweringoff_vm, **parameters)
    poweringoff_progressbar = click.progressbar(poweringoff.progress, label=f"Powering Off Virtual Machine [{vm.name}]") 
    with poweringoff_progressbar as progressbar:
        for progress in progressbar:
            if poweringoff.exception:
                raise click.ClickException(poweringoff.exception)

            if progress is not None: 
                result = progress
                break

    click.echo(f"Virtual machine [{vm.name}] already {vm.runtime.powerState}")

@cli.command(aliases=["new", "make"], help="Create a virtual machine in vCenter Server Appliance")
@click.argument("service")
@click.option("-e", "--environment", help="Environment name of virtual machine")
@click.option("-c", "--category", help="Category name of virtual machine")
@click.option("--folder", type=click.STRING, help="Destination folder for virtual machine (inherited from configuration file)")
@click.option("--cpus", type=click.INT, default=1, help="Number of CPUs for virtual machine (Core)", show_default=True)
@click.option("--memory", type=click.IntRange(min=1024, max=1024*64), default=1024, help="Memory size for virtual machine (MB)", show_default=True)
@click.option("--replicas", type=click.INT, default=1, help="Number of replicas for virtual machine", show_default=True)
@click.option("--paralel", type=click.INT, default=4, help="Limit the number of paralel works", show_default=True)
@click.option("-b", "--bootstrap", is_flag=True, help="If selected, virtual machines will start bootstrap after available")
@click.option("-d", "--debug", is_flag=True, help="Debugging virtual machine creation process")
@click.pass_context
def create(ctx, service, environment, category, folder, cpus, memory, replicas, paralel, bootstrap, debug):
    config = ctx.obj["CONFIG"]
    
    if environment not in config["vcenter.environments"]["available"]:
        raise click.ClickException(f"Environment {environment !r} are not available. Check ({ctx.obj['CONFIG_PATH']})")
        
    if not config.get(f"vcenter.categories.{environment}.{category}"):
        raise click.ClickException(f"Category {category !r} in Environment {environment !r} are not set. Check ({ctx.obj['CONFIG_PATH']})")
    
    if memory % 1024 != 0:
        raise click.ClickException(f"Memory size should be multiple of 1024 MB")

    _environment = config[f"vcenter.environments.{environment}"]
    _category = config[f"vcenter.categories.{environment}.{category}"]
    
    template_path = _category.get("template_path") or _environment.get("template_path")
    template = _category.get("template") or _environment.get("template")
    datastore = _category.get("datastore") or _environment.get("datastore")
    datastore_cluster = _category.get("datastore_cluster") or _environment.get("datastore_cluster")
    compute = _category.get("compute") or _environment.get("compute") 
    network = _category.get("network") or _environment.get("network")
    folder = folder or _category.get("folder") or _environment.get("folder")
    name_format = _category.get("name_format") or _environment.get("name_format")
    hostname_format = _category.get("hostname_format") or _environment.get("hostname_format")

    click.echo(f"\nCerberus v{__version__}\n")
    click.echo(f"==== Summary of Requirements ====")
    click.echo(f"Service: {service !r}")
    click.echo(f"Environment: {environment !r}")
    click.echo(f"Category: {category !r}")
    click.echo(f"Template: {template !r}")
    click.echo(f"Folder: {folder !r}")
    click.echo(f"Number of CPUs: {cpus !r} Core")
    click.echo(f"Memory Size: {memory !r} MB")
    click.echo(f"Replicas: {replicas !r}")
    click.echo(f"Bootstrap: {'yes' if bootstrap else 'no'}\n")

    _name = str.upper(name_format.format(
        prefix=_environment["prefix"],
        service=service,
        category=_category["name"]
    ))
    _hostname = str.lower(hostname_format.format(
        service=service,
        category=_category["name"]
    ))

    searching = Threading(helpers.searching_vm, **{
        "config": config,
        "vm_name": _name
    })
    
    searching_progressbar = click.progressbar(searching.progress, label=f"Setting up the requirement ") 
    with searching_progressbar as progressbar:
        for progress in progressbar:
            if searching.exception:
                raise click.ClickException(searching.exception)

            if progress is not None: 
                result = progress
                break

    vms_with_similar_name = list(map(lambda x: x["name"], result))
    _replicas = []
    order = 1
    while True:
        number = order
        if config["vcenter"].get("zfill", False):
            number = str(order).zfill(2)

        name = f"{_name}-{number}"
        hostname = f"{_hostname}-{number}"

        if len(_replicas) >= replicas:
            break
        
        if name not in vms_with_similar_name and (name, hostname) not in _replicas:
            _replicas.append((name, hostname))
        order += 1
    
    if not config.get(f"vcenter.networks.{network}"):
        raise click.ClickException(f"Network {network !r} are not set, please check the configuration file ({ctx.obj['CONFIG_PATH']})")
    
    network_config = config.get(f"vcenter.networks.{network}")
    specs = [
        {
            "name": name,
            "hostname": str.lower(hostname),
            "environment": environment,
            "category": category,
            "template": template,
            "template_path": template_path,
            "num_cpus": cpus,
            "memory": memory,
            "datastore": datastore,
            "datastore_cluster": datastore_cluster,
            "compute": compute,
            "folder": folder,
            "network": network_config,
            "bootstrap": bootstrap,
            "debug": debug
        } for name, hostname in _replicas
    ]
    
    helpers.make_summary(specs)

    creating = Threading(helpers.creating_vm, **{
        "config": config,
        "specs": specs,
        "paralel": paralel
    })
    
    result_vms = helpers.waiting_process(thread=creating, title="Creating virtual machines")

    waiting = Threading(helpers.waiting_vm, **{
        "specs": result_vms,
        "paralel": paralel
    })

    result_vms = helpers.waiting_process(thread=waiting, title="Waiting virtual machines to live")

    if bootstrap:
        bootstraping = Threading(helpers.bootstraping_vm, **{
            "config": config,
            "specs": result_vms,
            "paralel": paralel
        })
        result_vms = helpers.waiting_process(thread=bootstraping, title="Bootstraping virtual machines")

    helpers.show_vm_result(result_vms)
    helpers.make_logs(config, result_vms, action="Create")

@cli.command(aliases=["remove", "rm"], help="Remove a virtual machine in vCenter Server Appliance")
@click.argument("vm_name", required=False)
@click.option("--fqdn", help="FQDN of virtual machine")
@click.option("--ipaddr", help="IP address for virtual machine")
@click.option("--uuid", help="Virtual Machine UUID Instance")
@click.option("--paralel", type=click.INT, default=4, help="Limit the number of paralel works", show_default=True)
@click.option("-y", "--yes", is_flag=True, help="Answer yes for all prompt question")
@click.option("-f", "--force", is_flag=True, help="Force destroy process")
@click.pass_context
def destroy(ctx, vm_name, fqdn, ipaddr, uuid, paralel, yes, force):
    config = ctx.obj["CONFIG"]
    config["force"] = force

    if fqdn:
        ipaddr = helpers.findip_from_dns(config, fqdn)

    parameters = {
        "config": config, 
        "vm_name": vm_name, 
        "ipaddr": ipaddr,
        "uuid": uuid
    }

    searching = Threading(helpers.searching_vm, **parameters)
    
    param = vm_name or fqdn or ipaddr or uuid
    searching_progressbar = click.progressbar(searching.progress, label=f"Searching Virtual Machine ") 
    with searching_progressbar as progressbar:
        for progress in progressbar:
            if searching.exception:
                raise click.ClickException(searching.exception)
                
            if progress is not None: 
                result = progress
                break

    if not result:
        click.echo(f"Warning: VM [{param.upper()}] are not available at the moment")
        ctx.exit(1)
        
    _all_vms = False
    if fqdn or uuid:
        vm = result
    
    else:
        click.echo(f"==> {len(result)} virtual machines found")
        click.echo("[*] All virtual machine on listed below")
        for index, vm in enumerate(result):        
            click.echo(f"[{index+1}] {vm['name']} ({ vm['guest.net'][0] if vm.get('guest.net') else '-'})")
        
        try:
            answer = input("Choose the index number of virtual machine to restart: ")
            if answer == "*":
                _all_vms = True
            else:
                answer = int(answer)
                vm = result[answer-1]['obj']
        except:
            raise click.ClickException(
                message=f"Wrong choice. Abort!"
            )
        
    if not _all_vms:
        answer = yes or prompt_y_n_question(
            f"Are you sure to remove virtual machine [{vm.name}] in datacenter [{config['vcenter']['datacenter']}] ?",
            default="no"
        )
    else:
        answer = yes or prompt_y_n_question(
            f"Are you sure to remove all virtual machines on the listed above from datacenter [{config['vcenter']['datacenter']}]",
            default="no"
        )

    if not answer:
        ctx.exit(0)

    parameters = {
        "config": config,
        "paralel": paralel,
    }

    if not _all_vms:
        parameters["vms"] = [vm]
    else:
        parameters["vms"] = [r["obj"] for r in result]

    destroying = Threading(helpers.destroying_vm, **parameters)
    destroying_progressbar = click.progressbar(destroying.progress, label=f"Destroying Virtual Machine [{vm_name if _all_vms else vm.name}]") 
    with destroying_progressbar as progressbar:
        for progress in progressbar:
            if destroying.exception:
                raise click.ClickException(destroying.exception)

            if progress is not None: 
                result_vms = progress
                break

    helpers.make_logs(config, result_vms, action="Delete")
    if _all_vms:
        click.echo(f"Virtual machines [{vm_name}] removed")
    else:
        click.echo(f"Virtual machine [{vm.name}] removed")

@cli.command("import", help="Import all resource from vCenter")
@click.pass_context
def importing(ctx):
    config = ctx.obj["CONFIG"]
    available_environment = config["vcenter.environments"]["available"]

    parameters = {"config": config}

    importing = Threading(helpers.importing_vm, **parameters)
    
    importing_progressbar = click.progressbar(importing.progress, label=f"Look up all available virtual machine in vCenter Server ({config['vcenter']['datacenter']})") 
    with importing_progressbar as progressbar:
        for progress in progressbar:
            if importing.exception:
                raise click.ClickException(importing.exception)

            if progress is not None: 
                result = progress
                break

    import re
    vms = []
    for vm in result:
        for env in available_environment:
            environment = config.get(f"vcenter.environments.{env.lower()}") 
            if not environment:
                continue

            prefix = environment["prefix"]
            patterns = (
                f"^{prefix}-([\w]+)-([\w]+)-([\w]+)-([\d]+)",
                f"^{prefix}-([\w]+)-([\w]+)-([\d]+)",
                f"^{prefix}-([\w]+)-([\d]+)",
                f"^{prefix}_([\w]+)-([\w]+)-([\w]+)-([\d]+)",
                f"^{prefix}_([\w]+)-([\w]+)-([\d]+)",
                f"^{prefix}_([\w]+)-([\d]+)",
            )
            match = None
            for pattern in patterns:
                match = re.search(pattern, vm["name"])
                if match:
                    break
            
            if not match:
                continue

            info = {
                "name": vm["name"],
                "uuid": vm["config.uuid"],
                "num_cpus": vm["config.hardware.numCPU"],
                "memory": vm["config.hardware.memoryMB"],
                "hostname": vm.get("guest.hostName", "-"),
                "ipv4": vm["guest.net"][0] if vm["guest.net"] else "-",
                "environment": environment["name"],
            }
            
            data = list(match.groups())
            info["order"] = int(data.pop(-1))
            info["service"] = data.pop(0).lower()
            info["category"] = data.pop(0) if data else "GENERAL"
            if data:
                info["subcategory"] = data.pop(0)
            vms.append(info)

    import json
    jsonfiles = open("cerberus.resources.json", "w")
    json.dump(vms, jsonfiles, indent=4)
