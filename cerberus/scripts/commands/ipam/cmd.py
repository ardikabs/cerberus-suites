
import click
from click_aliases import ClickAliasedGroup

from cerberus.phpipam import errors as phpipam_err
from cerberus.scripts.config import ConfigFileProcessor
from cerberus.scripts.utils import prompt_y_n_question
from . import (
    services,
    helpers
)

@click.group("ipam", help="IPAM related operations", cls=ClickAliasedGroup)
@click.pass_context
def cli(ctx):
    pass

@cli.command("check", help="Check an available ip address in the IPAM server")
@click.argument("subnet_cidr")
@click.option("-r", "--reserve", is_flag=True, help="Reserved an available ip address")
@click.pass_context
def check(ctx, subnet_cidr, reserve):
    config = ctx.obj["CONFIG"]
    phpipam_obj = config["phpipam"]
    service = services.init_ipam_service(phpipam_obj)

    try:
        if reserve:
            result = service.reserve_ipaddr(subnet_cidr=subnet_cidr)
        else:
            result = service.check_free_ipaddr(subnet_cidr=subnet_cidr)
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        ctx.exit(1)

    click.echo(f"IPv4 address: {result.data} ({'reserved' if reserve else 'free'})")

@cli.command("find", help="Find available ip address in the IPAM server")
@click.argument("ipaddr", required=False)
@click.option("--cidr", help="Subnet CIDR for the address")
@click.option("--hostname", help="Hostname of the address")
@click.option("-y", "--yes", is_flag=True)
@click.pass_context
def find(ctx, ipaddr, cidr, hostname, yes):
    config = ctx.obj["CONFIG"]
    phpipam_obj = config["phpipam"]
    service = services.init_ipam_service(phpipam_obj)

    try:
        if ipaddr:
            result = service.show_ipaddr(address=ipaddr, subnet_cidr=cidr)
        elif hostname:
            result = service.show_ipaddr(hostname=hostname, subnet_cidr=cidr)
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        ctx.exit(1)

    subnets = helpers.resolve_subnet(service, result)
    helpers.show_ip(result, subnets)

@cli.command(aliases=["new", "make"], help="Create a new ip address in the IPAM server")
@click.argument("ipaddr")
@click.option("--cidr", required=True, help="Subnet CIDR for the address")
@click.option("--hostname", help="Hostname of the address")
@click.option("--description", help="Description of the address")
@click.option("--note", help="Note for the address")
@click.option("-y", "--yes", is_flag=True)
@click.pass_context
def create(ctx, ipaddr, cidr, hostname, description, note, yes):
    config = ctx.obj["CONFIG"]
    phpipam_obj = config["phpipam"]
    service = services.init_ipam_service(phpipam_obj)

    try:
        payload = {
            "ip":ipaddr,
            "hostname": hostname,
            "description": description,
            "note": note
        }
        result = service.add_ipaddr(payload=payload, subnet_cidr=cidr, show_result=True)
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        ctx.exit(1)
    
    subnets = helpers.resolve_subnet(service, result)
    helpers.show_ip(result, subnets)

@cli.command(aliases=["put"], help="Update existing ip address in the IPAM server")
@click.argument("ipaddr")
@click.option("--cidr", required=True, help="Subnet CIDR for the address")
@click.option("--hostname", help="Hostname of the address")
@click.option("--description", help="Description of the address")
@click.option("--note", help="Note for the address")
@click.option("-y", "--yes", is_flag=True)
@click.pass_context
def update(ctx, ipaddr, cidr, hostname, description, note, yes):
    config = ctx.obj["CONFIG"]
    phpipam_obj = config["phpipam"]
    service = services.init_ipam_service(phpipam_obj)

    try:
        payload = {
            "hostname": hostname,
            "description": description,
            "note": note
        }
        result = service.update_ipaddr(address=ipaddr, payload=payload, subnet_cidr=cidr)
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        ctx.exit(1)
    
    click.echo(f"Info: {result.message} [{ipaddr}]")

@cli.command(aliases=["rm"], help="Remove an ip address from IPAM server")
@click.argument("ipaddr")
@click.option("--cidr", required=True, help="Subnet CIDR for the address")
@click.option("-y", "--yes", is_flag=True)
@click.pass_context
def remove(ctx, ipaddr, cidr, yes):
    config = ctx.obj["CONFIG"]
    phpipam_obj = config["phpipam"]
    service = services.init_ipam_service(phpipam_obj)

    try:
        result = service.release_ipaddr(address=ipaddr, subnet_cidr=cidr)
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        ctx.exit(1)
    
    click.echo(f"Info: {result.message} [{ipaddr}]")
