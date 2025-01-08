import click
import docker

from ..databases import (
    get_database_config, 
    DatabaseCredentials,
    credentials_manager
)
from ..style import (
    print_error,
    print_warning,
    print_db_info,
)
from ..functions import (
    get_container_name,
    find_container,
    get_db_info,
    get_host_ip,
    get_connection_string,
    get_cli_command,
    generate_password,
)



@click.command(name='reset-password')
@click.argument('db_name')
@click.option('--reset-password', is_flag=True, help='Generate a new password')
def reset_password_cmd(db_name: str, reset_password: bool):
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