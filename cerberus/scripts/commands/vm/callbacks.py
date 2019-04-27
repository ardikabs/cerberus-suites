
import click

def convert2list(ctx, param, value):
    if value:
        return value.split(',')
    return value

def upper(ctx, param, value):
    if value:
        return value.upper()
    return value
    
def lower(ctx, param, value):
    if value:
        return value.lower()
    return value

def check_availability_datacenter(allow_null=True):

    def validate(ctx, param, value):
        config = ctx.obj["CONFIG"]
        datacenters = list(config["vcenter.datacenters"].keys())

        if not allow_null and value is None:
            raise click.exceptions.BadOptionUsage(
                message=f"Datacenter need to be defined"
            )      
        elif value is None:
            value = datacenters[0]
        
        if value not in datacenters:
            raise click.exceptions.BadParameter(
                message=f"vCenter Datacenter ({value}) not found in configuration file ({ctx.obj['CONFIG_PATH']})",
                param_hint=param.name
            )
        return value.upper()
    return validate
