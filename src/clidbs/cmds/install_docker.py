import click
from ..style import create_loading_status, print_success
from ..functions import install_docker

@click.command(name='install-docker')
def install_docker_cmd():
    """Install Docker automatically on this system.
    
    Example: clidb install-docker
    """
    with create_loading_status("🐳 Installing Docker...") as status:
        install_docker()
        status.update("✅ Docker installed successfully!")
    print_success("✅ Docker installed successfully!")