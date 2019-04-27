
AVAILABLE_COMMANDS = (
    "dns",
    "ipam",
    "vm",
)

def init_command(cli, **kwargs):
    from importlib import import_module
    for module in AVAILABLE_COMMANDS:
        cli.add_command(
            import_module(
                f".{module}", 
                package=__name__
            ).cli
        )
