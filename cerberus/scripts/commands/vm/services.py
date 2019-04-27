
from cerberus.vsphere.core import VSphereService

def init_vm_service(vcenter_obj):
    service = VSphereService(
        host=vcenter_obj.get("host"),
        port=vcenter_obj.get("port"),
        ssl=vcenter_obj.get("ssl")
    )
    return service