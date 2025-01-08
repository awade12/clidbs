"""Command to list supported database types and versions."""
import click
from ..style import print_supported_dbs, create_loading_status
from ..databases import list_supported_databases

@click.command(name='supported')
def supported_cmd():
    """List supported database types and versions."""
    with create_loading_status("🔍 Getting supported databases...") as status:
        supported_dbs = list_supported_databases()
        status.update("✨ Found supported databases!")
        print_supported_dbs(supported_dbs) 