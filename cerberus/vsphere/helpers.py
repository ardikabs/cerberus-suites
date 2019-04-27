from pyVmomi import vim
from . import errors

## VSphere Helper ##

# Decorator Section
def datacenter_required(func):
    def wrapper(*args, **kwargs):
        if not isinstance(kwargs.get("datacenter"), vim.Datacenter):
            raise errors.UnrecognizedResourceError("Unable to resolve datacenter object")

        return func(*args, **kwargs)
    return wrapper

def parent_rscpool_required(func):
    def wrapper(*args, **kwargs):
        if not hasattr(kwargs.get("parent_rscpool"), "resourcePool"):
            raise errors.UnrecognizedResourceError("Unable to resolve parent resource pool object")

        return func(*args, **kwargs)
    return wrapper

def get_obj(content, name, vimtype=[], folder=None):
    if folder is None:
        folder = content.rootFolder

    obj = None
    container = content.viewManager.CreateContainerView(
        folder, vimtype, True)
    view = container.view
    container.Destroy()
            
    for v in view:    
        if v.name == name:
            obj = v
            break

    return obj

def get_child_obj(content, parent, name):
    obj = None
    for child in parent.childEntity:
        if child.name == name:
            obj = child
            break
    return obj
        
# Datacenter Section
def get_datacenter(content, name): 
    return get_obj(content, vimtype=[vim.Datacenter], name=name)

# Cluster Storage Section
@datacenter_required
def get_datastorecluster(content, name, datacenter): 
    return get_obj(content, folder=datacenter.datastoreFolder, vimtype=[vim.StoragePod], name=name)

# Storage Section
@datacenter_required
def get_datastore(content, name, datacenter): 
    return get_obj(content, folder=datacenter.datastoreFolder, vimtype=[vim.Datastore], name=name)


# Compute Section
@datacenter_required
def get_host_system(content, name, datacenter): 
    return get_obj(content, folder=datacenter.hostFolder, vimtype=[vim.HostSystem], name=name)

@datacenter_required
def get_cluster_compute(content, name, datacenter): 
    return get_obj(content, folder=datacenter.hostFolder, vimtype=[vim.ClusterComputeResource], name=name)

@parent_rscpool_required
def get_resource_pool(content, parent_rscpool, name):
    if not isinstance(parent_rscpool, vim.ResourcePool):
        raise errors.UnrecognizedResourceError("Parent resource pool is not kind of vim.ResourcePool")
    return get_obj(content, folder=parent_rscpool, vimtype=[vim.ResourcePool], name=name)

# Network Section
@datacenter_required
def get_distributed_port_group(content, name, datacenter): 
    return get_obj(content, folder=datacenter.networkFolder, vimtype=[vim.DistributedVirtualPortgroup], name=name)

@datacenter_required
def get_distributed_virtual_switch(content, name, datacenter): 
    return get_obj(content, folder=datacenter.networkFolder, vimtype=[vim.DistributedVirtualSwitch], name=name)

# Virtual Machine Section
@datacenter_required
def get_virtual_machine(content, param, datacenter, idtype="name", folder=None):

    if idtype == "uuid":
        return content.searchIndex.FindByUuid(
            datacenter=datacenter,
            uuid=param,
            vmSearch=True
        )
    elif idtype == "ipaddr":
        return content.searchIndex.FindByIp(
            datacenter=datacenter,
            ip=param,
            vmSearch=True
        )
    elif idtype == "dns":
        return content.searchIndex.FindAllByDnsName(
            datacenter=datacenter,
            dnsName=param,
            vmSearch=True
        )
    elif idtype == "name":
        folder = folder if folder else datacenter.vmFolder
        return get_obj(content, name=param, vimtype=[vim.VirtualMachine], folder=folder)
        
# Folder Section
def get_main_folder(content, name, datacenter): 
    return get_obj(content, folder=datacenter.vmFolder, vimtype=[vim.Folder], name=name)

def get_child_folder(content, name, parent):
    if not isinstance(parent, vim.Folder):
        raise errors.UnrecognizedResourceError("Parent folder is not kind of [vim.Folder]")
    return get_child_obj(content=content, parent=parent, name=name)

# Task Section
def wait_for_task(task, callbacks={}, *args, **kwargs):
    def no_op(task, *args, **kwargs):
        pass
    queued_callback = callbacks.get('queued', no_op)
    running_callback = callbacks.get('running', no_op)
    success_callback = callbacks.get('success', no_op)
    error_callback = callbacks.get('error', no_op)

    waiting = True
    while waiting: 
        state = task.info.state
        if state == vim.TaskInfo.State.success:
            success_callback(task, *args, **kwargs)
            waiting = False
        elif state == vim.TaskInfo.State.queued:
            queued_callback(task, *args, **kwargs)
        elif state == vim.TaskInfo.State.running:
            running_callback(task, *args, **kwargs)
        elif state == vim.TaskInfo.State.error:
            error_callback(task, *args, **kwargs)
            raise task.info.error
        
        yield task
