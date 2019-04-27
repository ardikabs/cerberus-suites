
from cerberus.phpipam.core import PHPIPAMService

def init_ipam_service(ipam_obj):
    service = PHPIPAMService(
        app_id=ipam_obj.get("app_id"),
        endpoint=ipam_obj.get("endpoint"),
        user=ipam_obj.get("user"),
        pwd=ipam_obj.get("pwd")
    )
    return service