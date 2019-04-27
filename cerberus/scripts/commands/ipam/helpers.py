
import click
from cerberus.utils import parser

def resolve_subnet(service, addresses):
    result = []
    
    if isinstance(addresses, list):
        for addr in addresses:
            result.append(service.show_subnet(addr.subnetId))
    else:
        result.append(service.show_subnet(addresses.subnetId))
    return result

def show_ip(addresses, subnets):
    data = []
    if isinstance(addresses, list):
        for addr, subnet in zip(addresses, subnets):
            temp = [
                addr.ip, 
                f"{addr.hostname if addr.hostname else '-'}", 
                f"{subnet.subnet}/{subnet.mask}",
                f"{f'{addr.description[:20] !r}' if addr.description else '-'}"
            ]
            data.append(temp)
    else:
        temp = [
            addresses.ip, 
            f"{addresses.hostname if addresses.hostname else '-'}", 
            f"{subnets[0].subnet}/{subnets[0].mask}", 
            f"{f'{addresses.description[:20] !r}' if addresses.description else '-'}"
        ]
        data.append(temp)

    output = parser.BeautifyFormat.from_arr(
        data,
        headers=["IP", "HOSTNAME", "SUBNET", "DESCRIPTION"]
    )
    click.echo("\n".join(output))