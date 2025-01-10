import click
import os
from typing import Optional, List, Tuple, Any
import docker
from docker.client import DockerClient
import time

from ..notifications import notification_manager, EventType
from ..databases import (
    get_database_config, 
    DATABASES, 
    DatabaseCredentials,
    credentials_manager
)
from ..style import (
    print_success,
    print_error,
    print_warning,
    print_action,
    create_loading_status,
    create_progress,
    get_db_icon
)
from ..functions import (
    get_container_name,
    find_container,
    get_db_info,
    get_host_ip,
    get_connection_string,
    get_cli_command,
    generate_password)
from ..functions.docker_utils import (
    find_next_available_port,
    check_container_exists,
    remove_container_if_exists,
)

@click.command(name='create')
@click.argument('db_name', required=False)
@click.option('--type', 'db_type', type=click.Choice(list(DATABASES.keys())), help='Database type')
@click.option('--version', help='Database version')
@click.option('--access', type=click.Choice(['public', 'private']), help='Access type')
@click.option('--user', help='Database user to create')
@click.option('--port', type=int, help='Port to expose the database on')
@click.option('--discord-webhook', help='Discord webhook URL for notifications')
@click.option('--force', is_flag=True, help='Force creation by removing existing container if it exists')
def create_cmd(db_name: Optional[str], db_type: Optional[str], version: Optional[str], access: Optional[str], 
          user: Optional[str], port: Optional[int], discord_webhook: Optional[str], force: bool = False):
    """Create a new database."""
    
    def create_database(db_name, db_type, version, access, port, discord_webhook, force):
        nonlocal user
        try:
            client: DockerClient = docker.from_env()
            
            with create_loading_status(f"🔍 Checking configuration for {get_db_icon(db_type)} {db_type} database...") as status:
                # Get database configuration
                db_config = get_database_config(db_type, version)
                
                # Check if container already exists
                container_name = get_container_name(db_type, db_name)
                if check_container_exists(client, container_name):
                    if not force:
                        raise Exception(
                            f"A database named '{db_name}' already exists. Use --force to remove it and create a new one, "
                            f"or use a different name."
                        )
                    status.update(f"🗑️ Removing existing database '{db_name}' (--force flag used)")
                    remove_container_if_exists(client, container_name)
                
                # Use db_name as user if not specified
                if not user:
                    user = db_name
                    
                # Handle port allocation
                status.update("🔍 Finding available port...")
                if not port:
                    port = db_config.default_port
                
                # If port is taken, find next available port
                if not find_next_available_port(port, max_attempts=1):
                    next_port = find_next_available_port(port + 1, max_attempts=100)
                    if next_port:
                        print_warning(f"Port {port} is already in use. Using port {next_port} instead.")
                        port = next_port
                    else:
                        raise Exception(f"Could not find an available port starting from {port}")
                
                # Generate secure password
                status.update("🔑 Generating secure credentials...")
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
                    'name': container_name,
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

            # Create progress bar for container creation
            progress = create_progress()
            with progress:
                task = progress.add_task(f"🚀 Creating {db_type} database...", total=100)
                
                # Pull image (30%)
                progress.update(task, advance=10, description=f"📥 Pulling {db_type} image...")
                try:
                    client.images.pull(db_config.image)
                except Exception as e:
                    print_warning(f"Could not pull latest image: {str(e)}")
                progress.update(task, advance=20)
                
                # Create and start container (40%)
                progress.update(task, advance=10, description="🏗️ Creating container...")
                container = client.containers.run(**container_config)
                progress.update(task, advance=30)
                
                # Wait for container to be healthy (30%)
                progress.update(task, description="🏥 Waiting for database to be healthy...")
                time.sleep(3)  # Give it a moment to start
                container.reload()  # Refresh container state
                
                if container.status != 'running':
                    raise Exception(f"Container failed to start. Logs:\n{container.logs().decode()}")
                
                progress.update(task, advance=30, description="✨ Finalizing setup...")
                
                # Get the appropriate host
                host = get_host_ip() if access == 'public' else 'localhost'
                
                # Store credentials with webhook URL
                creds = DatabaseCredentials(
                    db_type=db_type,
                    version=version,
                    user=user,
                    password=password,
                    port=port,
                    host=host,
                    access=access,
                    name=db_name,
                    webhook_url=discord_webhook
                )
                credentials_manager.store_credentials(creds)
                
                # Generate connection details
                conn_string = get_connection_string(db_type, host, port, user, password, db_name)
                cli_command = get_cli_command(db_type, host, port, user, password, db_name)
                
                # Complete progress
                progress.update(task, completed=100, description="✅ Database created successfully!")
            
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
            
            # Send notification
            notification_manager.send_notification(
                event_type=EventType.DB_CREATED,
                db_info={
                    "name": db_name,
                    "type": db_config.name,
                    "version": version,
                    "host": host,
                    "port": port,
                    "access": access
                },
                webhook_url=discord_webhook
            )
                
        except Exception as e:
            print_error(f"Failed to create database: {str(e)}")
            notification_manager.send_notification(
                event_type=EventType.DB_CREATION_FAILED,
                db_info={"name": db_name, "type": db_type},
                webhook_url=discord_webhook,
                error_message=str(e)
            )

    # Set defaults for non-interactive mode
    db_type = db_type or 'postgres'
    access = access or 'public'
    create_database(db_name, db_type, version, access, port, discord_webhook, force)

@click.command(name='stop')
@click.argument('db_name')
def stop_cmd(db_name: str):
    """Stop a database."""
    try:
        client = docker.from_env()
        container = find_container(client, db_name)
        
        if not container:
            raise Exception(f"Database '{db_name}' not found")
        
        # Get credentials for webhook URL
        creds = credentials_manager.get_credentials(db_name)
        
        container.stop()
        print_action("Stop", db_name)
        
        if creds:
            # Get database info for notification
            db_name, db_type = get_db_info(container.name)
            notification_manager.send_notification(
                event_type=EventType.DB_STOPPED,
                db_info={"name": db_name, "type": db_type},
                webhook_url=creds.webhook_url
            )
    except Exception as e:
        print_action("Stop", db_name, success=False)
        print_error(str(e))
        if creds:
            notification_manager.send_notification(
                event_type=EventType.DB_STOP_FAILED,
                db_info={"name": db_name},
                webhook_url=creds.webhook_url,
                error_message=str(e)
            )

@click.command(name='start')
@click.argument('db_name')
def start_cmd(db_name: str):
    """Start a stopped database."""
    try:
        with create_loading_status(f"🔍 Finding database '{db_name}'...") as status:
            client = docker.from_env()
            container = find_container(client, db_name)
            
            if not container:
                raise Exception(f"Database '{db_name}' not found")
            
            # Get credentials for webhook URL
            creds = credentials_manager.get_credentials(db_name)
            
            status.update(f"🚀 Starting database '{db_name}'...")
            # Try to start the container
            container.start()
            
            # Wait a bit and check if it's actually running
            time.sleep(5)  # Give it time to start
            container.reload()  # Refresh container state
            
            if container.status != 'running':
                # Get the logs to see what went wrong
                logs = container.logs(tail=50).decode()
                raise Exception(f"Container failed to start. Logs:\n{logs}")
            
            status.update(f"✅ Database '{db_name}' started successfully!")
        
        print_action("Start", db_name)
        
        if creds:
            # Get database info for notification
            db_name, db_type = get_db_info(container.name)
            notification_manager.send_notification(
                event_type=EventType.DB_STARTED,
                db_info={"name": db_name, "type": db_type},
                webhook_url=creds.webhook_url
            )
        
    except Exception as e:
        print_error(f"Failed to start database: {str(e)}")
        if creds:
            notification_manager.send_notification(
                event_type=EventType.DB_START_FAILED,
                db_info={"name": db_name},
                webhook_url=creds.webhook_url,
                error_message=str(e)
            )

@click.command(name='remove')
@click.argument('db_name')
def remove_cmd(db_name: str):
    """Remove a database completely."""
    try:
        with create_loading_status(f"🔍 Finding database '{db_name}'...") as status:
            client = docker.from_env()
            container = find_container(client, db_name)
            
            if not container:
                raise Exception(f"Database '{db_name}' not found")
            
            # Get credentials for webhook URL before removal
            creds = credentials_manager.get_credentials(db_name)
            webhook_url = creds.webhook_url if creds else None
            
            # Get database info before removal for notification
            db_name, db_type = get_db_info(container.name)
            
            status.update(f"🗑️ Removing database '{db_name}'...")
            container.remove(force=True)
            
            status.update("🧹 Cleaning up credentials...")
            credentials_manager.remove_credentials(db_name)
        
        print_action("Remove", db_name)
        
        if webhook_url:
            notification_manager.send_notification(
                event_type=EventType.DB_REMOVED,
                db_info={"name": db_name, "type": db_type},
                webhook_url=webhook_url
            )
    except Exception as e:
        print_action("Remove", db_name, success=False)
        print_error(str(e))
        if webhook_url:
            notification_manager.send_notification(
                event_type=EventType.DB_REMOVE_FAILED,
                db_info={"name": db_name},
                webhook_url=webhook_url,
                error_message=str(e)
            )

@click.command(name='recreate')
@click.argument('db_name')
def recreate_cmd(db_name: str):
    """Recreate a database container from its stored configuration."""
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

