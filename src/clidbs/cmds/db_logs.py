import click
import docker
import click
from click import Context
import os
from typing import Optional, List, Tuple, Any
import docker

from ..databases import (
    credentials_manager
)
from ..style import (
    print_success,
    print_error,
)
from ..functions import (
    find_container
)

@click.command(name='logs')
@click.argument('db_name')
def logs_cmd(db_name: str):
    """Show logs for a database.
    
    Example: clidb logs mydb
    """
    try:
        client = docker.from_env()
        container = find_container(client, db_name)
        
        if not container:
            raise Exception(f"Database '{db_name}' not found")
        
        # Get all logs
        logs = container.logs(tail=100).decode()
        print_success(f"Logs for database '{db_name}':")
        print(logs)
            
    except Exception as e:
        print_error(f"Failed to get logs: {str(e)}")

@click.command(name='inspect')
@click.argument('db_name')
def inspect_cmd(db_name: str):
    """Show detailed information about a database.
    
    Example: clidb inspect mydb
    """
    try:
        client = docker.from_env()
        container = find_container(client, db_name)
        
        if not container:
            raise Exception(f"Database '{db_name}' not found")
        
        # Get container info
        info = container.attrs
        
        # Get credentials
        creds = credentials_manager.get_credentials(db_name)
        
        print_success(f"Details for database '{db_name}':")
        print("\nContainer Status:")
        print(f"Status: {info['State']['Status']}")
        print(f"Running: {info['State']['Running']}")
        print(f"Started At: {info['State']['StartedAt']}")
        print(f"Error: {info['State']['Error']}")
        
        if creds:
            print("\nDatabase Credentials:")
            print(f"Type: {creds.db_type}")
            print(f"Version: {creds.version or 'latest'}")
            print(f"User: {creds.user}")
            print(f"Password: {creds.password}")
            print(f"Port: {creds.port}")
            print(f"Host: {creds.host}")
            print(f"Access: {creds.access}")
        
        print("\nContainer Config:")
        print(f"Image: {info['Config']['Image']}")
        print(f"Command: {info['Config']['Cmd']}")
        print("Environment:")
        for env in info['Config']['Env']:
            print(f"  {env}")
            
    except Exception as e:
        print_error(f"Failed to inspect database: {str(e)}")