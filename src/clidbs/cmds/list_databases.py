import click
import docker

from ..style import print_error, print_db_list
from ..functions import get_db_info

@click.command(name='list')
def list_dbs_cmd():
    """List all databases.
    
    Example: clidb list
    """
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)
        
        our_containers = []
        for container in containers:
            db_name, db_type = get_db_info(container.name)
            if db_name and db_type:
                our_containers.append((db_name, db_type, container.status))
        
        print_db_list(our_containers)
            
    except Exception as e:
        print_error(f"Failed to list databases: {str(e)}")