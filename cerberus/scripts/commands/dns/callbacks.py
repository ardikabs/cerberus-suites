
import click
from cerberus.scripts.config import ConfigFileProcessor

def check_domain(ctx, param, value):
    if value:
        _split = value.split(".")
        value = _split[0]
        if len(_split) > 1:
            ctx.params["zone"] = ".".join(_split[1:])
    return value

def check_availability_zone(allow_null=True):

    def validate(ctx, param, value):
        config = ctx.obj["CONFIG"]
        available_zones = config["dns.zones"]["available"]
        value = value if value else ctx.params.get("zone")
        if value and value not in available_zones:
            raise click.exceptions.BadParameter(
                message=f"Zone ({value}) not found in configuration file ({ctx.obj['CONFIG_PATH']})",
                param_hint=param.name
            )
        
        if not allow_null and value is None:
            raise click.exceptions.BadOptionUsage(
                message=f"Zone need to be defined",
                option_name="zone"
            )
        return value
    return validate

def check_existing_record_with_name(name, rtype=None):

    def filtering(data):
        comparator = (name in data.get("name"))
        if rtype:
            comparator = comparator and data.get("rtype") == rtype
        return comparator
    return filtering

def check_existing_record_with_content(content, rtype=None):

    def filtering(data):
        comparator = (data.get("content") == content)
        if rtype:
            comparator = comparator and data.get("rtype") == rtype
        return comparator
    return filtering