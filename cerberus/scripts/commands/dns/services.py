
from cerberus.dns.core import DNSService

def init_dns_service(zone_obj):
    service = DNSService(
        zone=zone_obj.get('name'),
        nameserver=zone_obj.get("server"),
        keyring_name=zone_obj.get("keyring_name"),
        keyring_value=zone_obj.get("keyring_value")
    )
    return service