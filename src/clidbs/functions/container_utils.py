"""Container-related utility functions."""
from typing import Optional, Tuple
from docker.client import DockerClient
from docker.models.containers import Container

def get_container_name(db_type: str, db_name: str) -> str:
    """Convert db_name to full container name."""
    return f"clidb-{db_type}-{db_name}"

def find_container(client: DockerClient, db_name: str) -> Optional[Container]:
    """Find a container by database name."""
    containers = client.containers.list(all=True)
    for container in containers:
        # Split container name into parts
        parts = container.name.split('-')
        # Check if it's our container (starts with clidb- and ends with db_name)
        if len(parts) >= 3 and parts[0] == "clidb" and '-'.join(parts[2:]) == db_name:
            return container
    return None

def get_db_info(container_name: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract db_name and type from container name."""
    parts = container_name.split('-')
    if len(parts) >= 3 and parts[0] == "clidb":
        db_type = parts[1]
        db_name = '-'.join(parts[2:])
        return db_name, db_type
    return None, None 