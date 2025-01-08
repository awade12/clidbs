"""Command to show the current version of CLIDB."""
import click
from ..style import print_success
from .. import __version__

@click.command(name='version')
def version_cmd():
    """Show the current version of CLIDB.
    
    Example: clidb version
    """
    print_success(f"CLIDB version {__version__}")