
import click

from cerberus.utils import parser
from cerberus.scripts.config import ConfigFileProcessor
from . import (
    services,
    callbacks
)

def show_dns(data):
    output = parser.BeautifyFormat.from_dict(
        data, 
        headers=["NAME", "CONTENT", "RTYPE", "TTL", "ZONE"],
        attr=["name", "content", "rtype", "ttl", "zone"]
    )
    click.echo("\n".join(output))

def searching_dns(config, available_zones, domain, content, rtype, ttl, zone):
    data = []
    if not zone:
        for zone in available_zones:
            section = f"dns.zones.{zone}"
            zone_obj = ConfigFileProcessor.select_storage_for(section, config)
            service = services.init_dns_service(zone_obj)
            data.extend(service.import_records())
    elif zone in available_zones:
        section = f"dns.zones.{zone}"
        zone_obj = ConfigFileProcessor.select_storage_for(section, config)
        service = services.init_dns_service(zone_obj)
        data.extend(service.import_records())
    else:
        raise click.BadParameter(
            message=f"Zone ({value}) not found in configuration file ({ctx.obj['CONFIG_PATH']})",
            param_hint="zone"
        )
    if not data:
        click.echo("Error: No record data found!", err=True)
        
    if content: 
        exists = filter(callbacks.check_existing_record_with_content(content, rtype=rtype), data)
    else: 
        exists = filter(callbacks.check_existing_record_with_name(domain, rtype=rtype), data)
    
    return list(exists)
