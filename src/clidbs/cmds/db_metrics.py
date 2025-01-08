import click
import docker
import os
import time

from ..style import print_error, print_db_metrics
from ..functions.docker_utils import find_container, get_container_metrics

@click.command(name='metrics')
@click.argument('db_name')
@click.option('--watch', is_flag=True, help='Watch metrics in real-time (updates every 2 seconds)')
def metrics_cmd(db_name: str, watch: bool):
    """Show detailed metrics for a database.
    
    Example: clidb metrics mydb
    """
    try:
        client = docker.from_env()
        container = find_container(client, db_name)
        
        if not container:
            raise Exception(f"Database '{db_name}' not found")
        
        if watch:
            try:
                while True:
                    # Clear screen
                    os.system('cls' if os.name == 'nt' else 'clear')
                    
                    # Get and display metrics
                    metrics = get_container_metrics(container)
                    print_db_metrics(db_name, metrics)
                    
                    # Wait before next update
                    time.sleep(2)
            except KeyboardInterrupt:
                print("\nStopped watching metrics")
                return
        else:
            metrics = get_container_metrics(container)
            print_db_metrics(db_name, metrics)
            
    except Exception as e:
        print_error(f"Failed to get metrics: {str(e)}")