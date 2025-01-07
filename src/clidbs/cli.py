import click
from click import Context
import os
from typing import Optional, List, Tuple, Any
import docker
from docker.client import DockerClient
import requests
from packaging import version
import time

from .notifications import send_discord_notification
from .config import Config
from .databases import (
    get_database_config, 
    list_supported_databases, 
    DATABASES, 
    DatabaseCredentials,
    credentials_manager
)
from .style import (
    print_success,
    print_error,
    print_warning,
    print_db_info,
    print_db_list,
    print_supported_dbs,
    print_action,
    print_help_menu
)
from .functions import (
    check_docker_available,
    install_docker,
    get_container_name,
    find_container,
    get_db_info,
    get_host_ip,
    get_connection_string,
    get_cli_command,
    generate_password,
    run_command
)

from . import __version__

_ssl_manager = None

def get_ssl_manager():
    """Lazy load the SSL manager after Docker checks."""
    global _ssl_manager
    if _ssl_manager is None:
        from .ssl import ssl_manager
        _ssl_manager = ssl_manager
    return _ssl_manager

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
    # Skip Docker check for install-docker command
    ctx = click.get_current_context()
    if ctx.invoked_subcommand != 'install-docker':
        check_docker_available()
    pass

@main.command()
@click.argument('db_name')
@click.option('--type', 'db_type', type=click.Choice(list(DATABASES.keys())), default='postgres', help='Database type')
@click.option('--version', help='Database version')
@click.option('--access', type=click.Choice(['public', 'private']), default='public', help='Access type')
@click.option('--user', help='Database user to create')
@click.option('--port', type=int, help='Port to expose the database on')
@click.option('--discord-webhook', help='Discord webhook URL for notifications')
def create(db_name: str, db_type: str, version: Optional[str], access: str, user: str, 
          port: Optional[int], discord_webhook: Optional[str]):
    """Create a new database.
    
    Example: clidb create mydb --type postgres --version 16
    """
    try:
        client: DockerClient = docker.from_env()
        
        # Get database configuration
        db_config = get_database_config(db_type, version)
        
        # Use db_name as user if not specified
        if not user:
            user = db_name
            
        # Use default port if not specified
        if not port:
            port = db_config.default_port
        
        # Generate secure password
        password = generate_password()
        
        # Prepare environment variables
        environment = db_config.get_env_vars(db_name, user, password)
        
        # Configure ports
        ports = {f'{db_config.default_port}/tcp': port}
        
        # Configure network mode based on access type
        network_mode = 'bridge' if access == 'public' else 'host'
        
        # Prepare container configuration
        container_config = {
            'image': db_config.image,
            'name': get_container_name(db_type, db_name),
            'environment': environment,
            'ports': ports,
            'network_mode': network_mode,
            'detach': True
        }
        
        # Add optional configurations
        if db_config.volumes:
            container_config['volumes'] = db_config.volumes
        if db_config.command:
            container_config['command'] = db_config.command
        
        # Create and start container
        container = client.containers.run(**container_config)
        
        # Get the appropriate host
        host = get_host_ip() if access == 'public' else 'localhost'
        
        # Store credentials
        creds = DatabaseCredentials(
            db_type=db_type,
            version=version,
            user=user,
            password=password,
            port=port,
            host=host,
            access=access,
            name=db_name
        )
        credentials_manager.store_credentials(creds)
        
        # Generate connection details
        conn_string = get_connection_string(db_type, host, port, user, password, db_name)
        cli_command = get_cli_command(db_type, host, port, user, password, db_name)
        
        print_success(f"""
Database '{db_name}' created successfully!
Type: {db_config.name}
Version: {version or 'latest'}
Access: {access.upper()}
Host: {host}
Port: {port}
User: {user}
Password: {password}

Connection String (copy/paste ready):
{conn_string}

CLI Command:
{cli_command}

Tip: Use 'clidb info {db_name}' to see these details again.
""")
        
        if discord_webhook:
            # Don't send sensitive info to Discord
            safe_message = f"""Database '{db_name}' ({db_config.name} {version or 'latest'}) created successfully!
Type: {db_config.name}
Host: {host}
Port: {port}"""
            send_discord_notification(
                webhook_url=discord_webhook,
                message=safe_message
            )
            
    except Exception as e:
        print_error(f"Failed to create database: {str(e)}")
        if discord_webhook:
            send_discord_notification(
                webhook_url=discord_webhook,
                message=f"Error creating database '{db_name}': {str(e)}"
            )

@main.command()
@click.argument('db_name')
@click.option('--reset-password', is_flag=True, help='Generate a new password')
def info(db_name: str, reset_password: bool):
    """Show connection information for a database."""
    try:
        client = docker.from_env()
        container = find_container(client, db_name)
        
        if not container:
            raise Exception(f"Database '{db_name}' not found")
        
        # Get credentials from storage or regenerate them
        creds = credentials_manager.get_credentials(db_name)
        if not creds or reset_password:
            # Get container info
            db_name, db_type = get_db_info(container.name)
            
            # Get database configuration
            db_config = get_database_config(db_type)
            
            # Generate new credentials
            password = generate_password()
            user = db_name  # Use database name as default user
            
            # Get port from container
            ports = container.attrs['NetworkSettings']['Ports']
            port = None
            for container_port, host_bindings in ports.items():
                if host_bindings:
                    port = int(host_bindings[0]['HostPort'])
                    break
            if not port:
                port = db_config.default_port
            
            # Determine access type and host
            network_mode = container.attrs['HostConfig']['NetworkMode']
            access = 'private' if network_mode == 'host' else 'public'
            host = get_host_ip() if access == 'public' else 'localhost'
            
            # Create new credentials
            creds = DatabaseCredentials(
                db_type=db_type,
                version=None,  # We don't know the version for existing containers
                user=user,
                password=password,
                port=port,
                host=host,
                access=access,
                name=db_name
            )
            
            if reset_password:
                # Update container with new password
                container.stop()
                container.remove()
                
                # Create new container with same config but new password
                environment = db_config.get_env_vars(db_name, user, password)
                ports = {f'{db_config.default_port}/tcp': port}
                network_mode = 'bridge' if access == 'public' else 'host'
                
                container_config = {
                    'image': db_config.image,
                    'name': get_container_name(db_type, db_name),
                    'environment': environment,
                    'ports': ports,
                    'network_mode': network_mode,
                    'detach': True
                }
                
                if db_config.volumes:
                    container_config['volumes'] = db_config.volumes
                if db_config.command:
                    container_config['command'] = db_config.command
                
                client.containers.run(**container_config)
            
            # Store the credentials
            credentials_manager.store_credentials(creds)
        
        # Get database configuration
        db_config = get_database_config(creds.db_type, creds.version)
        
        # Create info dictionary
        info_dict = {
            "Type": db_config.name,
            "Version": creds.version or 'latest',
            "Access": creds.access.upper(),
            "Host": creds.host,
            "Port": creds.port,
            "User": creds.user,
            "Password": creds.password
        }
        
        # Generate connection details
        conn_string = get_connection_string(
            creds.db_type, creds.host, creds.port, 
            creds.user, creds.password, creds.name
        )
        cli_command = get_cli_command(
            creds.db_type, creds.host, creds.port, 
            creds.user, creds.password, creds.name
        )
        
        print_db_info(
            f"Database Information for '{db_name}'",
            info_dict,
            conn_string,
            cli_command
        )
        
        if reset_password:
            print_warning("Password has been reset! Old connections will no longer work.")
            
    except Exception as e:
        print_error(f"Failed to get database info: {str(e)}")

@main.command()
@click.argument('db_name')
@click.option('--discord-webhook', help='Discord webhook URL for notifications')
def stop(db_name: str, discord_webhook: Optional[str]):
    """Stop a database."""
    try:
        client = docker.from_env()
        container = find_container(client, db_name)
        
        if not container:
            raise Exception(f"Database '{db_name}' not found")
        
        container.stop()
        print_action("Stop", db_name)
        
        if discord_webhook:
            send_discord_notification(
                webhook_url=discord_webhook,
                message=f"Database '{db_name}' stopped successfully"
            )
    except Exception as e:
        print_action("Stop", db_name, success=False)
        print_error(str(e))
        if discord_webhook:
            send_discord_notification(
                webhook_url=discord_webhook,
                message=f"Failed to stop database '{db_name}': {str(e)}"
            )

@main.command()
@click.argument('db_name')
def start(db_name: str):
    """Start a stopped database.
    
    Example: clidb start mydb
    """
    try:
        client = docker.from_env()
        container = find_container(client, db_name)
        
        if not container:
            raise Exception(f"Database '{db_name}' not found")
        
        # Try to start the container
        container.start()
        
        # Wait a bit and check if it's actually running
        time.sleep(5)  # Give it time to start
        container.reload()  # Refresh container state
        
        if container.status != 'running':
            # Get the logs to see what went wrong
            logs = container.logs(tail=50).decode()
            raise Exception(f"Container failed to start. Logs:\n{logs}")
        
        print_action("Start", db_name)
        
    except Exception as e:
        print_error(f"Failed to start database: {str(e)}")
        return

@main.command()
@click.argument('db_name')
@click.option('--discord-webhook', help='Discord webhook URL for notifications')
def remove(db_name: str, discord_webhook: Optional[str]):
    """Remove a database completely."""
    try:
        client = docker.from_env()
        container = find_container(client, db_name)
        
        if not container:
            raise Exception(f"Database '{db_name}' not found")
        
        container.remove(force=True)
        credentials_manager.remove_credentials(db_name)
        print_action("Remove", db_name)
        
        if discord_webhook:
            send_discord_notification(
                webhook_url=discord_webhook,
                message=f"Database '{db_name}' removed successfully"
            )
    except Exception as e:
        print_action("Remove", db_name, success=False)
        print_error(str(e))
        if discord_webhook:
            send_discord_notification(
                webhook_url=discord_webhook,
                message=f"Failed to remove database '{db_name}': {str(e)}"
            )

@main.command()
def list():
    """List all databases.
    
    Example: clidb list
    """
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)
        
        # Filter our containers
        our_containers = []
        for container in containers:
            db_name, db_type = get_db_info(container.name)
            if db_name and db_type:
                our_containers.append((db_name, db_type, container.status))
        
        print_db_list(our_containers)
            
    except Exception as e:
        print_error(f"Failed to list databases: {str(e)}")

@main.command(name='supported')
def list_supported():
    """List supported database types and versions."""
    print_supported_dbs(list_supported_databases())

@main.command()
@click.argument('db_name')
@click.argument('domain')
@click.option('--email', required=True, help='Email for SSL certificate notifications')
def ssl(db_name: str, domain: str, email: str):
    """Setup SSL for a database with a domain.
    
    Example: clidb ssl mydb example.com --email admin@example.com
    """
    try:
        # Find the database
        client: DockerClient = docker.from_env()
        container = find_container(client, db_name)
        
        if not container:
            raise Exception(f"Database '{db_name}' not found")
        
        # Get database info
        creds = credentials_manager.get_credentials(db_name)
        if not creds:
            raise Exception(f"No credentials found for database '{db_name}'")
        
        if creds.access != 'public':
            raise Exception("SSL can only be setup for databases with public access")
            
        # Get database configuration
        db_config = get_database_config(creds.db_type, creds.version)
        
        # Setup SSL
        ssl_manager = get_ssl_manager()
        success, message = ssl_manager.setup_ssl(
            domain=domain,
            email=email,
            db_type=creds.db_type,
            port=creds.port,
            container_name=container.name
        )
        
        if success:
            print_success(f"SSL setup successful for {domain}")
            
            # Update connection strings with https
            info_dict = {
                "Type": db_config.name,
                "Version": creds.version or 'latest',
                "Access": "PUBLIC (SSL)",
                "Domain": domain,
                "Port": creds.port,
                "User": creds.user,
                "Password": creds.password
            }
            
            # Generate HTTPS connection strings
            conn_string = get_connection_string(
                creds.db_type, domain, creds.port, 
                creds.user, creds.password, creds.name
            ).replace('http://', 'https://')
            
            cli_command = get_cli_command(
                creds.db_type, domain, creds.port, 
                creds.user, creds.password, creds.name
            )
            
            print_db_info(
                f"SSL Connection Information for '{db_name}'",
                info_dict,
                conn_string,
                cli_command
            )
        else:
            raise Exception(message)
            
    except Exception as e:
        print_error(f"Failed to setup SSL: {str(e)}")

@main.command()
@click.argument('db_name')
@click.argument('domain')
def remove_ssl(db_name: str, domain: str):
    """Remove SSL from a database.
    
    Example: clidb remove-ssl mydb example.com
    """
    try:
        # Find the database
        client: DockerClient = docker.from_env()
        container = find_container(client, db_name)
        
        if not container:
            raise Exception(f"Database '{db_name}' not found")
        
        # Remove SSL
        ssl_manager = get_ssl_manager()
        success, message = ssl_manager.remove_ssl(domain)
        
        if success:
            print_success(f"SSL removed successfully from {domain}")
        else:
            raise Exception(message)
            
    except Exception as e:
        print_error(f"Failed to remove SSL: {str(e)}")

@main.command()
@click.argument('domain')
def verify_domain(domain: str):
    """Verify if a domain points to this server.
    
    Example: clidb verify-domain example.com
    """
    try:
        ssl_manager = get_ssl_manager()
        success, message = ssl_manager.verify_domain(domain)
        if success:
            print_success(message)
        else:
            print_error(message)
    except Exception as e:
        print_error(f"Domain verification failed: {str(e)}")

@main.command(name='install-docker')
def install_docker_command():
    """Install Docker automatically on this system.
    
    Example: clidb install-docker
    """
    install_docker()

@main.command()
@click.argument('db_name')
def logs(db_name: str):
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

@main.command()
@click.argument('db_name')
def inspect(db_name: str):
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

@main.command()
@click.argument('db_name')
def recreate(db_name: str):
    """Recreate a database container from its stored configuration.
    
    Example: clidb recreate mydb
    """
    try:
        client = docker.from_env()
        container = find_container(client, db_name)
        creds = credentials_manager.get_credentials(db_name)
        
        if not container:
            raise Exception(f"Database '{db_name}' not found")
            
        if not creds:
            raise Exception(f"No credentials found for database '{db_name}'")
        
        # Get database configuration
        db_config = get_database_config(creds.db_type, creds.version)
        
        # Remove old container
        print_action("Removing", "old container")
        container.remove(force=True)
        
        # Prepare new container configuration
        container_config = {
            'image': db_config.image,
            'name': get_container_name(creds.db_type, db_name),
            'environment': db_config.get_env_vars(db_name, creds.user, creds.password),
            'ports': {f'{db_config.default_port}/tcp': creds.port},
            'network_mode': 'bridge' if creds.access == 'public' else 'host',
            'detach': True
        }
        
        # Add optional configurations
        if db_config.volumes:
            container_config['volumes'] = db_config.volumes
        if db_config.command:
            container_config['command'] = db_config.command
        
        # Create and start new container
        print_action("Creating", "new container")
        container = client.containers.run(**container_config)
        
        print_success(f"Database '{db_name}' recreated successfully")
            
    except Exception as e:
        print_error(f"Failed to recreate database: {str(e)}")

if __name__ == '__main__':
    main() 