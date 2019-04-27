
import atexit
from . import (
    errors,
    helpers,
    tools
)
from pyVmomi import vim
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect

def network_check(vm):
    """  
    This function will be check network hardware for vmxnet3 with deviceConfigId 4000
    
    :param vm: Virtual Machine object in dictionary format
    :return: Return Virtual Machine object itself with already change to different format for the network variable
    """

    found = False
    for net in vm.get("guest.net"):
        if net.connected and net.deviceConfigId == 4000:
            vm["guest.net"] = list(net.ipAddress)
            found = True
            break
        
    if not found:
        vm["guest.net"] = None
    return vm

def filtering_by(name=None, hostname=None, ipaddr=None):
    """  
    This decorator function that will filtering virtual machine object in dictionary based on 
        name, hostname, and ip address.
    The usage of this function only on filter() function purposes
    
    :param name: Virtual machine name
    :param hostname: Virtual machine hostname
    :param ipaddr: Virtual machine ip address
    :return: Only return boolean
    """

    def _fromlist(comparator, target):
        for c in comparator:
            if c in target:
                return True
        return False
    
    def filtering(vm):
        valid = False
        if name:
            valid = _fromlist(name, str.lower(vm.get("name"))) \
                if isinstance(name, (list, tuple,)) else str.lower(name) in str.lower(vm.get("name"))  

        elif hostname:
            valid = _fromlist(hostname, str.lower(vm.get("guest.hostName", ""))) \
                if isinstance(hostname, (list, tuple,)) else str.lower(hostname) in str.lower(vm.get("guest.hostName", ""))

        elif ipaddr:
            valid = ipaddr in vm.get("guest.net", "")

        return valid
    
    return filtering
        
class VSphereService(object):
    """ VMWare vSphere Service Class

    This class has the purposes for abstracting the interaction to 
    vSphere/vCenter Server.

    """

    def __init__(self, host, port=443, ssl=False, *args, **kwargs):
        """  
            Constructor

            :param host: vSphere/vCenter host to be solved (ip address or domain name)
            :param port: vSphere/vCenter Server port number
            :param ssl: only for SSL
        """
        self.host = host
        self.port = port
        self.ssl = ssl

    def connect(self, user, pwd):
        """  
            Connect method
            This method will make a connection to the vSphere/vCenter host using
            user and password. After connection established, object saved the service instance and 
            also content object for service instance

            :param user: User credential
            :param pwd: Password credential
            :return: vim.ServiceInstance
        """
        try:
            if self.ssl:
                service_instance = SmartConnect(
                    user=user,
                    pwd=pwd,
                    host=self.host,
                    port=self.port
                )
            else:
                service_instance = SmartConnectNoSSL(
                    user=user,
                    pwd=pwd,
                    host=self.host,
                    port=self.port
                )
            atexit.register(Disconnect, service_instance)
        except BlockingIOError:
            err = errors.ServiceUnavailable(
                f"Service unavailable. Whether unresolved name [{self.host}] or port connection problem"
            )
            raise err
        except vim.fault.InvalidLogin:
            err = errors.CredentialError("Invalid User or Password")
            raise err
        except Exception as e:
            err = errors.TaskError(f"Unidentified Error ({e.__class__.__name__})")
            raise err
        else:
            self.service_instance = service_instance
            self.content = self.service_instance.RetrieveContent()
            return service_instance

    def disconnect(self):
        """  
            Disconnect method
            Literally this method will excuted automatically if the process is done.

            :return: Nothing
            :rtype: None
        """
        try:
            Disconnect(self.service_instance)
        except:
            pass

    @property
    def datacenter(self):
        """  
            Getter Datacenter attribute
            :return: Datacenter object name
            :rtype: String
        """
        try:
            self.datacenter_obj
        except AttributeError as e:
            err = AttributeError("Datacenter Attribute never initialized")
            raise err
        else:
            return self.datacenter_obj.name
    
    @datacenter.setter
    def datacenter(self, name):
        """  
            Setter Datacenter attribute
            :param: Datacenter object name
        """
        try:
            self.datacenter_obj = helpers.get_datacenter(content=self.content, name=name)
        except AttributeError:
            err = errors.SessionError("No connection established, get a connection first then initialize datacenter")
            raise err

    def clone_vm(self, name, template, folder, clonespec, **kwargs):
        """
            Create virtual machine method
            :param name: Virtual machine name
            :param template: Template virtual machine to be used (vim.VirtualMachine)
            :param folder: Destionation folder for the virtual machine object (vim.Folder)
            :param clonespec: Attribute for cloning function (vim.CloneSpec)
            :param dscluster: Datastore Cluster Name

            :return: vSphere/vCenter task object
            :rtype: vim.Task
        """
        task = template.Clone(folder=folder, name=name, spec=clonespec)
        cloning = self.__class__.wait_for_task(f"VM Cloning {name}", task, **kwargs)
        return cloning.info.result

    def clone_vm_with_sdrs(self, name, template, folder, clonespec, dscluster, **kwargs):
        if dscluster is None:
            err = ValueError("Datastore cluster can not be null")
            raise err

        podsel = vim.storageDrs.PodSelectionSpec()
        pod = helpers.get_datastorecluster(
            content=self.content,
            name=dscluster,
            datacenter=self.datacenter_obj
        )
        if pod is None:
            err = errors.UnrecognizedResourceError(f"Datastore cluster [{dscluster}] are not found")
            raise err
        
        podsel.storagePod = pod
        sps = vim.storageDrs.StoragePlacementSpec()
        sps.podSelectionSpec = podsel
        sps.cloneName = name
        sps.cloneSpec = clonespec
        sps.vm = template
        sps.folder = folder
        sps.type = "clone"

        srm = self.content.storageResourceManager
        rec = srm.RecommendDatastores(storageSpec=sps)
        key = rec.recommendations[0].key
        task = srm.ApplyStorageDrsRecommendation_Task(key=key)

        cloning = self.__class__.wait_for_task(f"VM Cloning {name}", task, **kwargs)
        return cloning.info.result.vm

    def delete_vm(self, vm=None, uuid=None, name=None):
        """
            Delete Virtual Machine
            :param vm: Virtual machine object (vim.VirtualMachine)
            :param uuid: Virtual machine instance UUID 
            :param name: Virtual machine Name
            
            :return: vSphere/vCenter task object
            :rtype: vim.Task
        """

        if not vm:
            vm = self.search_vm(uuid=uuid, name=name)

            if not vm:
                err = LookupError("Virtual machine not found")
                raise err

        if vm.runtime.powerState == "poweredOn":
            wait = self.__class__.wait_for_task(
                f"Powering Off VM {vm.name}",
                vm.PowerOffVM_Task()
            )

        task = vm.Destroy_Task()
        return task

    
    @classmethod
    def wait_for_task(cls, name, task, on_queued=None, on_success=None, on_running=None, on_error=None, *args, **kwargs):
        """
            Wait for task method.
            >>  This is categorized as class method, the purposes for watching the progress of the task.

            :param name: Task name identifier
            :param task: vCenter/vSphere task object (vim.Task) 
            :param on_queued: Callback for queued process
            :param on_success: Callback for success process
            :param on_running: Callback for running process
            :param on_error: Callback for error process

            :return: A yield process from utility function (helpers.wait_for_task())
            :rtype: Generator
        """
        callbacks = {}
        if on_queued:
            callbacks["queued"] = on_queued
        if on_success:
            callbacks["success"] = on_success
        if on_running:
            callbacks["running"] = on_running
        if on_error:
            callbacks["error"] = on_error

        result = None
        try:
            for process in helpers.wait_for_task(task, callbacks, *args, **kwargs):
                result = process
        except Exception as e:
            err = errors.TaskError(f"{name} task get error ({str(e)})")
            raise err
        else:
            return result


    def lookup_vms(self, name=None, hostname=None, ipaddr=None):
        """  
            Lookup Virtual Machines (many)
            >>  This method for doing a more fast process to lookup all virtual machine in
                selected datacenter of vSphere/vCenter with given parameter, if no parameter selected
                the result will give all the virtual machine.
            
            :param name: Virtual machine name
            :param hostname: Virtual machine hostname
            :param ipaddr: Virtual machine ip address
            :return: A list of virtual machine
            :rtype: Filter object
        """
        vm_properties = [
            "name", 
            "config.uuid", 
            "config.hardware.numCPU",
            "config.hardware.memoryMB", 
            "config.guestFullName", 
            "config.guestId", 
            "config.version", 
            "guest.net", 
            "guest.guestState", 
            "guest.hostName",
            "runtime.powerState"
        ]
        view = tools.get_container_view(
            self.service_instance,
            container=self.datacenter_obj.vmFolder,
            obj_type=[vim.VirtualMachine]
        )
        vm_data = tools.collect_properties(
            self.service_instance, 
            view_ref=view,
            obj_type=vim.VirtualMachine, 
            path_set=vm_properties,
            include_mors=True
        )
        vm_data = map(network_check, vm_data)
        if name:
            vm_data = filter(filtering_by(name=name), vm_data)
        elif hostname:
            vm_data = filter(filtering_by(hostname=hostname), vm_data)
        elif ipaddr:
            vm_data = filter(filtering_by(ipaddr=ipaddr), vm_data)
        return vm_data


    def search_vm(self, uuid=None, name=None, ipaddr=None, hostname=None):
        """  
            Search virtual machine method
            >>  This method will search only one virtual machine with given parameter.
                This method used help over vmware tool for searching the virtual machine object,
                but using name param will use the process over lookups_vms() method

            :param uuid: Virtual machine UUID instance
            :param name: Virtual machine name
            :param hostname: Virtual machine hostname
            :param ipaddr: Virtual machine ip address
            :return: A single object of virtual machine
            :rtype: vim.VirtualMachine
        """
        vm = None
        if name:
            data = list(self.lookup_vms(name=name))        
            if not data: 
                return

            return data[0]["obj"]
        
        elif uuid:
            vm = helpers.get_virtual_machine(
                content=self.content, 
                param=uuid, 
                datacenter=self.datacenter_obj, 
                idtype="uuid"
            )


        elif ipaddr:
            vm = helpers.get_virtual_machine(
                content=self.content, 
                param=ipaddr, 
                datacenter=self.datacenter_obj, 
                idtype="ipaddr"  
            )

        return vm
    
    def search_vms(self, name=None, fqdn=None, ipaddr=None, hostname=None):
        """  
            Search virtual machines method (many)
            >>  This method will search virtual machines with given parameter.
                This method are opposite from search_vm() method, which if use fqdn as parameter,
                the process will use the help of vmware tool.
            >>  Note: There is no different about FQDN and hostname, they actually use hostname thing,
                        but to differentiate hostname will use lookup_vms() method and fqdn will use
                        the help of vmware tool. 

            :param name: Virtual machine name
            :param fqdn: Virtual machine FQDN
            :param hostname: Virtual machine hostname
            :param ipaddr: Virtual machine ip address
            :return: A single object of virtual machine
            :rtype: dict
        """

        if name:
            result = self.lookup_vms(name=name) 

        elif hostname:
            result = self.lookup_vms(hostname=hostname)

        elif ipaddr:
            result = self.lookup_vms(ipaddr=ipaddr)

        elif fqdn:
            result = helpers.get_virtual_machine(
                content=self.content, 
                param=fqdn, 
                datacenter=self.datacenter_obj, 
                idtype="dns"  
            )
        
        try:
            result = list(result)
        except:
            result = []
        finally:
            return result


    def setup_specifications(self, storage, network, compute, *args, **kwargs):
        """
            Setup Specifications
            :storage vim.Datastore
            :network vim.DistributedVirtualPortgroup
            :compute vim.ClusterComputeResource or vim.ResourcePool
            :kwargs (dhcp: bool, hostname: str, domain: str, specification: dict, network_config: dict)
            :specification (num_cpus: int, memory: int)
            :network_config (
                ipv4_address: str, gateway_address: str, 
                subnet_mask: str, dns_domain: str, dns_server: list
            )

            :return 
                vm_configspec vim.ConfigSpec
                vm_customspec vim.vm.customization.Specification
                vim.CloneSpec
        """
        nic = self.make_nic(network)
        configspec = self.make_vm_configspec(
            num_cpus=kwargs.get("num_cpus", 1), 
            memory=kwargs.get("memory", 1024), 
            devices=[nic]
        )

        network_adapter = self.make_network_adapter(
            dhcp=kwargs.get("dhcp", False), 
            **kwargs.get("network_config")
        )
        identity = self.make_identity(
            hostname=kwargs.get("hostname"), 
            domainname=kwargs.get("domain")
        )
        customspec = self.make_vm_customspec(
            vm_network_adapter=network_adapter, 
            vm_identity=identity
        )

        relocatespec = self.make_vm_relocatespec(
            resource_pool=compute, 
            datastore=storage
        )
        clonespec = self.make_vm_clonespec(
            vm_relocatespec=relocatespec
        )
        return configspec, customspec, clonespec

    def make_nic(self, distributed_portgroup):
        """  
            Network Interface Card
            :distributed_portgroup vim.DistributedVirtualPortgroup

            :return vim.vm.device.VirtualDeviceSpec
        """
        dvs = distributed_portgroup.config.distributedVirtualSwitch
        dvs_port = vim.dvs.PortConnection(
            portgroupKey=distributed_portgroup.key,
            switchUuid=dvs.uuid
        )

        nic = vim.vm.device.VirtualDeviceSpec()
        nic.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        nic.device = vim.vm.device.VirtualVmxnet3()
        nic.device.key = 4000
        nic.device.addressType = "assigned"
        nic.device.wakeOnLanEnabled = True
        nic.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
        nic.device.backing.port = dvs_port
        nic.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic.device.connectable.startConnected = True
        nic.device.connectable.allowGuestControl = True
        return nic
    
    def make_network_adapter(self, dhcp=False, *args, **kwargs):
        """
            Network Adapter
            :dhcp bool
            :kwargs (ipv4_address: str, gateway_address: str, subnet_mask: str, dns_domain: str, dns_server: list)

            :return tuple(vim.vm.customization.AdapterMapping, vim.vm.customization.GlobalIPSettings)
        """
        adapter_map = vim.vm.customization.AdapterMapping()
        globalip = vim.vm.customization.GlobalIPSettings()

        if dhcp:
            adapter_map.adapter = vim.vm.customization.IPSettings()
            adapter_map.adapter.ip = vim.vm.customization.DhcpIpGenerator()
        
        else:
            adapter_map.adapter = vim.vm.customization.IPSettings()
            adapter_map.adapter.ip = vim.vm.customization.FixedIp()
            adapter_map.adapter.ip.ipAddress  = kwargs.get("ipv4_address")
            adapter_map.adapter.gateway = [kwargs.get("gateway_address")]
            adapter_map.adapter.subnetMask = kwargs.get("subnet_mask")

        adapter_map.adapter.dnsDomain = kwargs.get("dns_domain")
        globalip.dnsSuffixList = [kwargs.get("dns_domain")]
        globalip.dnsServerList = kwargs.get("dns_server")

        return adapter_map, globalip
    
    def make_identity(self, hostname, domainname, timezone="Asia/Jakarta"):
        """
            Virtual Machine Identity
            :hostname str
            :domainname str
            :timezone str

            :return vim.vm.customization.LinuxPrep
        """
        vm_identity = vim.vm.customization.LinuxPrep()
        vm_identity.domain = domainname
        vm_identity.timeZone = timezone
        vm_identity.hostName = vim.vm.customization.FixedName()
        vm_identity.hostName.name = hostname
        return vm_identity
    

    def make_vm_configspec(self, num_cpus, memory, devices=None):
        """
            Virtual Machine Config Specification
            :param num_cpus: Number of CPUs
            :param memory: Number of Memory Size
            :param devices: List of vim.vm.device.VirtualDeviceSpec

            :return: vim.vm.ConfigSpec
        """

        self.vm_configspec = vim.vm.ConfigSpec()
        self.vm_configspec.numCPUs = num_cpus
        self.vm_configspec.memoryMB = memory
        self.vm_configspec.cpuHotAddEnabled = True
        self.vm_configspec.memoryHotAddEnabled = True

        if devices:
            self.vm_configspec.deviceChange = devices

        return self.vm_configspec


    def make_vm_relocatespec(self, resource_pool: vim.ResourcePool, datastore: vim.Datastore):
        """
            Virtual Machine Relocation Specification
            :datastore vim.Datastore
            :resource_pool vim.ResourcePool

            :return vim.vm.RelocateSpec
        """
        self.vm_relocatespec = vim.vm.RelocateSpec()
        self.vm_relocatespec.pool = resource_pool
        if datastore:
            self.vm_relocatespec.datastore = datastore
        return self.vm_relocatespec


    def make_vm_customspec(self, vm_network_adapter, vm_identity):
        """
            Virtual Machine Custom Specification
            :vm_network_adapter tuple(vim.vm.customization.AdapterMapping, vim.vm.customization.GlobalIPSettings)
            :vm_identity vim.vm.customization.LinuxPrep

            :return vim.vm.customization.Specification
        """
        adapter_map, globalip = vm_network_adapter

        self.vm_customspec = vim.vm.customization.Specification()
        self.vm_customspec.nicSettingMap = [adapter_map]
        self.vm_customspec.globalIPSettings = globalip
        self.vm_customspec.identity = vm_identity
        return self.vm_customspec


    def make_vm_clonespec(self, vm_relocatespec):
        """
            Virtual Machine Clone Specification
            :vm_relocatespec vim.RelocateSpec

            :return vim.vm.CloneSpec
        """
        vm_clone_spec = vim.vm.CloneSpec()
        vm_clone_spec.location = vm_relocatespec
        vm_clone_spec.powerOn = False
        vm_clone_spec.template = False
        return vm_clone_spec

    def use_template(self, template_uuid=None, template_name=None, template_folder="Template"):
        if template_uuid:
            template_vm = helpers.get_virtual_machine(
                content=self.content,
                param=template_uuid,
                datacenter=self.datacenter_obj,
                idtype="uuid"
            )
        if template_folder:
            folder = helpers.get_main_folder(
                content=self.content, 
                name=template_folder, 
                datacenter=self.datacenter_obj
            )

            if folder is None:
                err = errors.UnrecognizedResourceError(f"Template folder [{template_folder}] are not found")
                raise err

            template_vm = helpers.get_virtual_machine(
                content=self.content, 
                param=template_name, 
                datacenter=self.datacenter_obj, 
                idtype="name", 
                folder=folder
            )

        if template_vm is None:
            err = errors.UnrecognizedResourceError(f"VM template [{template_name if template_name else template_uuid}] are not found")
            raise err

        return template_vm

    def use_network(self, network_name):
        network = helpers.get_distributed_port_group(
            content=self.content,
            name=network_name,
            datacenter=self.datacenter_obj
        )
        if network is None:
            err = errors.UnrecognizedResourceError(f"Network [{network_name}] are not found")
            raise err

        return network

    def use_folder(self, folder_path):
        parts = folder_path.split("/")
        folder = helpers.get_main_folder(content=self.content, name=parts[0], datacenter=self.datacenter_obj)
        if folder is None:
            err = errors.UnrecognizedResourceError(f"Folder [{parts[0]}] are not found")
            raise err

        if len(parts) == 1:
            return folder
        else:
            return self.find_child_folder(child_folder_path="/".join(parts[1:]), parent=folder)

    def use_compute(self, compute_name):
        parts = compute_name.split("/")
        compute = helpers.get_cluster_compute(
            content=self.content,
            name=parts[0],
            datacenter=self.datacenter_obj
        )
        if compute is None:
            err = errors.UnrecognizedResourceError(f"Compute [{parts[0]}] are not found")
            raise err

        if len(parts) > 1:
            for value in parts[1:]:
                compute = helpers.get_resource_pool(
                    content=self.content,
                    parent_rscpool=compute.resourcePool,
                    name=value
                )
            return compute
        return compute.resourcePool
    
    def use_storage(self, storage_name):
        storage = helpers.get_datastore(
            content=self.content,
            name=storage_name,
            datacenter=self.datacenter_obj
        )
        return storage

    def find_child_folder(self, child_folder_path, parent):
        part_child_folder_path = child_folder_path.split("/")
        child_name = part_child_folder_path[0]
        if not child_name.strip():
            return parent
        else:
            folder = helpers.get_child_folder(
                content=self.content, 
                name=child_name, 
                parent=parent
            )

            if folder is None:
                try:
                    folder = parent.CreateFolder(child_name)
                except:
                    folder = helpers.get_child_folder(
                        content=self.content, 
                        name=child_name, 
                        parent=parent
                    )

            return self.find_child_folder(
                child_folder_path="/".join(part_child_folder_path[1:]), 
                parent=folder
            )