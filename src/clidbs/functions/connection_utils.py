"""Connection-related utility functions."""
import os
import socket

def get_host_ip() -> str:
    """Get the host's public IP address."""
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