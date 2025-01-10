import click
from click import Context
from typing import Any
import requests
from packaging import version

from .style import (
    print_warning,
    print_help_menu
)
from .functions import (
    check_docker_available
)

from .cmds.list_supported import supported_cmd
from .cmds.get_version import version_cmd
from .cmds.system_setup import install_docker_cmd
from .cmds.reset_password import reset_password_cmd
from .cmds.list_databases import list_dbs_cmd
from .cmds.backup_dbs import backup_cmd, restore_cmd, list_backups_cmd, delete_backup_cmd
from .cmds.db_metrics import metrics_cmd
from .cmds.ssl_management import ssl_cmd, remove_ssl_cmd, verify_domain_cmd
from .cmds.db_logs import logs_cmd, inspect_cmd
from .cmds.db_manage import create_cmd, stop_cmd, start_cmd, remove_cmd, recreate_cmd

from . import __version__

## TODO move this to a function file
def check_for_updates():
    """Check if there's a newer version available on PyPI."""
    try:
        response = requests.get("https://pypi.org/pypi/clidbs/json", timeout=1)
        if response.status_code == 200:
            latest_version = response.json()["info"]["version"]
            current_version = __version__
            
            if version.parse(latest_version) > version.parse(current_version):
                print_warning(f"""
A new version of CLIDB is available!
Current version: {current_version}
Latest version:  {latest_version}

To upgrade, run:
    pipx upgrade clidbs
""")
    except Exception:
        # Silently fail if we can't check for updates
        pass

class CLIDBGroup(click.Group):
    """Custom group class for CLIDB that provides styled help."""
    
    def get_help(self, ctx: Context) -> str:
        """Override to show our styled help instead of Click's default."""
        check_for_updates()  # Check for updates before showing help
        print_help_menu()
        return ""

    def invoke(self, ctx: Context) -> Any:
        """Override to check for updates before any command."""
        check_for_updates()  # Check for updates before any command
        return super().invoke(ctx)

@click.group(cls=CLIDBGroup)
def main():
    """Simple database management for your VPS."""
    ctx = click.get_current_context()
    if ctx.invoked_subcommand != 'install-docker':
        check_docker_available()
    pass

main.add_command(supported_cmd)
main.add_command(version_cmd)
main.add_command(install_docker_cmd)
main.add_command(reset_password_cmd)
main.add_command(list_dbs_cmd)
main.add_command(backup_cmd)
main.add_command(restore_cmd)
main.add_command(list_backups_cmd)
main.add_command(delete_backup_cmd)
main.add_command(metrics_cmd)
main.add_command(ssl_cmd)
main.add_command(remove_ssl_cmd)
main.add_command(verify_domain_cmd)
main.add_command(logs_cmd)
main.add_command(inspect_cmd)
main.add_command(create_cmd)
main.add_command(stop_cmd)
main.add_command(start_cmd)
main.add_command(remove_cmd)
main.add_command(recreate_cmd)

if __name__ == '__main__':
    main() 