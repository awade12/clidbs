import click
import docker
from docker.client import DockerClient
from ..functions.ssl_utils import get_ssl_manager

from ..databases import (
    get_database_config,
    credentials_manager
)
from ..style import (
    print_success,
    print_error,
    print_db_info,
    create_loading_status
)
from ..functions import (
    find_container,
    get_connection_string,
    get_cli_command,
)


@click.command(name='ssl')
@click.argument('db_name')
@click.argument('domain')
@click.option('--email', required=True, help='Email for SSL certificate notifications')
def ssl_cmd(db_name: str, domain: str, email: str):
    """Setup SSL for a database with a domain.
    
    Example: clidb ssl mydb example.com --email admin@example.com
    """
    try:
        with create_loading_status(f"🔍 Checking database configuration...") as status:
            # Find the database
            client: docker.DockerClient = docker.from_env()
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
            
            status.update("🔒 Setting up SSL certificates...")
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
                status.update("✅ SSL setup completed successfully!")
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
                status.update("❌ SSL setup failed!")
                raise Exception(message)
                
    except Exception as e:
        print_error(f"Failed to setup SSL: {str(e)}")

@click.command(name='remove-ssl')
@click.argument('db_name')
@click.argument('domain')
def remove_ssl_cmd(db_name: str, domain: str):
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

@click.command(name='verify-domain')
@click.argument('domain')
def verify_domain_cmd(domain: str):
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