
import os
import click
import configparser

from cerberus import __version__
from .config import ConfigFileProcessor
from .commands import init_command


@click.group(invoke_without_command=True)
@click.version_option(
    version=__version__, 
    prog_name="Cerberus",
    message=('%(prog)s v%(version)s')
)
@click.option("--config-file", 
    type=click.File(),
    help="Selected configuration file."
)
@click.pass_context
def cli(ctx, config_file):
    """ 
    The available commands for execution to Cerberus are listed below.\n
    """

    cfp = ConfigFileProcessor()
    if config_file:
        cfp.config_files.append(config_file.name)
        cfp.config_searchpath.append(os.path.abspath(os.path.dirname(config_file.name)))

    try:

        config = cfp.read_config()
        if not config:
            raise ValueError("Invalid configuration file")

    except configparser.DuplicateOptionError as e:
        raise click.ClickException(f"Config ({e.source}). " 
                    f"Option <{e.option}> in section ({e.section}) "
                    f"already exist [line {e.lineno}]"
        )
    except configparser.DuplicateSectionError as e:
        raise click.ClickException(f"Config ({e.source}). " 
                    f"Duplicate section ({e.section}) [line {e.lineno}]"
        )
    except:
        raise click.ClickException(
            message=f"No configuration file found or invalid configuration file format ({cfp.config_path})"
        )
        
    ctx.ensure_object(dict)
    ctx.obj["CONFIG"] = config
    ctx.obj["CONFIG_PATH"] = cfp.config_path

init_command(cli)