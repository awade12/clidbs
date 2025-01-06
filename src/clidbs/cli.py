import click
from click import Context
import docker
import os
import secrets
import string
import socket
from typing import Optional, List
from .notifications import send_discord_notification
from .config import Config
from .databases import (
    get_database_config, 
    list_supported_databases, 
    DATABASES, 
    DatabaseCredentials,
    credentials_manager
)
from .ssl import ssl_manager
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

def generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def get_container_name(db_type: str, db_name: str) -> str:
    """Convert db_name to full container name."""
    return f"clidb-{db_type}-{db_name}"

def find_container(client: docker.DockerClient, db_name: str) -> Optional[docker.models.containers.Container]:
    """Find a container by database name."""
    containers = client.containers.list(all=True)
    for container in containers:
        # Split container name into parts
        parts = container.name.split('-')
        # Check if it's our container (starts with clidb- and ends with db_name)
        if len(parts) >= 3 and parts[0] == "clidb" and '-'.join(parts[2:]) == db_name:
            return container
    return None

def get_db_info(container_name: str) -> tuple:
    """Extract db_name and type from container name."""
    parts = container_name.split('-')
    if len(parts) >= 3 and parts[0] == "clidb":
        db_type = parts[1]
        db_name = '-'.join(parts[2:])
        return db_name, db_type
    return None, None

def get_host_ip() -> str:
    """Get the host's public IP address."""
    # First try to get the IP from environment variable
    if os.getenv("CLIDB_HOST_IP"):
        return os.getenv("CLIDB_HOST_IP")
    
    try:
        # Try to get the host's IP by creating a dummy connection
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def get_connection_string(db_type: str, host: str, port: int, user: str, password: str, db_name: str) -> str:
    """Generate a connection string based on database type."""
    if db_type == 'postgres':
        return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    elif db_type == 'mysql' or db_type == 'mariadb':
        return f"mysql://{user}:{password}@{host}:{port}/{db_name}"
    elif db_type == 'mongo':
        return f"mongodb://{user}:{password}@{host}:{port}/{db_name}"
    elif db_type == 'redis' or db_type == 'keydb':
        return f"redis://:{password}@{host}:{port}"
    elif db_type == 'neo4j':
        return f"neo4j://{user}:{password}@{host}:{port}"
    elif db_type == 'clickhouse':
        return f"clickhouse://{user}:{password}@{host}:{port}/{db_name}"
    return ""

def get_cli_command(db_type: str, host: str, port: int, user: str, password: str, db_name: str) -> str:
    """Generate CLI command based on database type."""
    if db_type == 'postgres':
        return f"psql -h {host} -p {port} -U {user} -d {db_name}  # Password: {password}"
    elif db_type == 'mysql' or db_type == 'mariadb':
        return f"mysql -h {host} -P {port} -u {user} -p{password} {db_name}"
    elif db_type == 'mongo':
        return f"mongosh {host}:{port}/{db_name} -u {user} -p {password}"
    elif db_type == 'redis':
        return f"redis-cli -h {host} -p {port} -a {password}"
    elif db_type == 'keydb':
        return f"keydb-cli -h {host} -p {port} -a {password}"
    elif db_type == 'neo4j':
        return f"cypher-shell -a {host}:{port} -u {user} -p {password}"
    elif db_type == 'clickhouse':
        return f"clickhouse-client --host {host} --port {port} --user {user} --password {password} --database {db_name}"
    return ""

class CLIDBGroup(click.Group):
    """Custom group class for CLIDB that provides styled help."""
    
    def get_help(self, ctx: Context) -> str:
        """Override to show our styled help instead of Click's default."""
        print_help_menu()
        return ""

@click.group(cls=CLIDBGroup)
def main():
    """Simple database management for your VPS."""
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
        client = docker.from_env()
        
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
@click.option('--discord-webhook', help='Discord webhook URL for notifications')
def start(db_name: str, discord_webhook: Optional[str]):
    """Start a stopped database."""
    try:
        client = docker.from_env()
        container = find_container(client, db_name)
        
        if not container:
            raise Exception(f"Database '{db_name}' not found")
        
        container.start()
        print_action("Start", db_name)
        
        if discord_webhook:
            send_discord_notification(
                webhook_url=discord_webhook,
                message=f"Database '{db_name}' started successfully"
            )
    except Exception as e:
        print_action("Start", db_name, success=False)
        print_error(str(e))
        if discord_webhook:
            send_discord_notification(
                webhook_url=discord_webhook,
                message=f"Failed to start database '{db_name}': {str(e)}"
            )

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
        client = docker.from_env()
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
        client = docker.from_env()
        container = find_container(client, db_name)
        
        if not container:
            raise Exception(f"Database '{db_name}' not found")
        
        # Remove SSL
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
        success, message = ssl_manager.verify_domain(domain)
        if success:
            print_success(message)
        else:
            print_error(message)
    except Exception as e:
        print_error(f"Domain verification failed: {str(e)}")

if __name__ == '__main__':
    main() 