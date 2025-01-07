"""Docker-related utility functions."""
import shutil
import subprocess
import os
import platform
from typing import Tuple, Optional, Dict, Any
import docker
import socket
import psutil
from datetime import datetime
from .utils import format_bytes
from .print_utils import print_error, print_warning, print_success, print_action
from docker.client import DockerClient
from docker.models.containers import Container

def run_command(cmd: str) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, and stderr."""
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True
    )
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr

def check_docker_available():
    """Check if Docker is installed and provide installation instructions if not."""
    if not shutil.which('docker'):
        print_error("""
Docker is not installed! CLIDB requires Docker to run databases.

You can install Docker automatically by running:
    clidb install-docker

Or visit https://docs.docker.com/engine/install/ for manual installation instructions.
""")
        exit(1)

    try:
        import docker
        client = docker.from_env()
        client.ping()
    except Exception as e:
        print_error(f"""
Docker is installed but not running or accessible!

You can fix this by running:
    clidb install-docker

This will:
1. Start the Docker service
2. Enable Docker to start on boot
3. Add your user to the docker group

Error details: {str(e)}
""")
        exit(1)

def install_docker():
    """Install Docker automatically on this system."""
    system = platform.system().lower()
    if system != "linux":
        print_error("Automatic Docker installation is only supported on Linux systems.")
        print_warning("Please visit https://docs.docker.com/engine/install/ for installation instructions.")
        return

    distro = ""
    # Try to detect Linux distribution
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    distro = line.split("=")[1].strip().strip('"')
                    break

    print_action("Installing", "Docker")
    
    try:
        # First check if Docker is already installed but not running
        if shutil.which('docker'):
            print_warning("Docker is already installed! Configuring it...")
            
            # Try to start Docker service
            print_action("Starting", "Docker service")
            run_command("sudo systemctl start docker")
            run_command("sudo systemctl enable docker")
            
            # Add user to docker group
            print_action("Adding", "user to docker group")
            run_command(f"sudo usermod -aG docker {os.getenv('USER', os.getenv('SUDO_USER', 'root'))}")
            
            print_success("""
Docker is now configured! For the changes to take effect:
1. Log out of your current session
2. Log back in
3. Run 'docker ps' to verify everything works
""")
            return

        # Install Docker using get.docker.com script (works for most Linux distributions)
        print_action("Downloading", "Docker installation script")
        code, out, err = run_command("curl -fsSL https://get.docker.com -o get-docker.sh")
        if code != 0:
            raise Exception(f"Failed to download Docker script: {err}")

        print_action("Installing", "Docker")
        code, out, err = run_command("sudo sh get-docker.sh")
        if code != 0:
            raise Exception(f"Failed to install Docker: {err}")

        # Clean up installation script
        os.remove("get-docker.sh")

        # Start Docker service
        print_action("Starting", "Docker service")
        run_command("sudo systemctl start docker")
        run_command("sudo systemctl enable docker")

        # Add user to docker group
        print_action("Adding", "user to docker group")
        run_command(f"sudo usermod -aG docker {os.getenv('USER', os.getenv('SUDO_USER', 'root'))}")

        print_success("""
Docker has been successfully installed! For the changes to take effect:
1. Log out of your current session
2. Log back in
3. Run 'docker ps' to verify everything works
""")

    except Exception as e:
        print_error(f"Failed to install Docker: {str(e)}")
        print_warning("""
Manual installation instructions:
1. Visit: https://docs.docker.com/engine/install/
2. Choose your operating system
3. Follow the installation steps
4. Run 'clidb install-docker' again to configure Docker
""") 

def find_container(client: DockerClient, db_name: str) -> Optional[Container]:
    """Find a container by database name.
    
    Args:
        client: Docker client
        db_name: Name of the database
        
    Returns:
        Container object if found, None otherwise
    """
    # List all containers (including stopped ones)
    containers = client.containers.list(all=True)
    
    # Look for container with our naming pattern
    for container in containers:
        # Check if container name starts with clidb-*-{db_name}
        parts = container.name.split('-')
        if len(parts) >= 3 and parts[0] == 'clidb' and parts[-1] == db_name:
            return container
    
    return None

def is_port_available(port: int) -> bool:
    """Check if a port is available on localhost."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return True
    except:
        return False

def find_next_available_port(start_port: int, max_attempts: int = 100) -> Optional[int]:
    """Find the next available port starting from start_port.
    
    Args:
        start_port: Port to start checking from
        max_attempts: Maximum number of ports to check
        
    Returns:
        Available port number or None if none found
    """
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(port):
            return port
    return None

def check_container_exists(client: DockerClient, container_name: str) -> bool:
    """Check if a container exists."""
    try:
        client.containers.get(container_name)
        return True
    except docker.errors.NotFound:
        return False

def remove_container_if_exists(client: DockerClient, container_name: str):
    """Remove a container if it exists."""
    try:
        container = client.containers.get(container_name)
        container.remove(force=True)
    except docker.errors.NotFound:
        pass

def get_container_metrics(container: Container) -> Dict[str, Any]:
    """Get container metrics including CPU, memory, network, and disk I/O."""
    try:
        # Get container stats
        stats = container.stats(stream=False)
        
        # Calculate CPU usage percentage
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
        cpu_percent = 0.0
        if system_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
        
        # Calculate memory usage
        mem_usage = stats['memory_stats']['usage']
        mem_limit = stats['memory_stats']['limit']
        mem_percent = (mem_usage / mem_limit) * 100.0
        
        # Get network I/O
        networks = stats['networks'] if 'networks' in stats else {}
        net_rx = sum(net['rx_bytes'] for net in networks.values()) if networks else 0
        net_tx = sum(net['tx_bytes'] for net in networks.values()) if networks else 0
        
        # Get block I/O
        block_io = stats['blkio_stats']['io_service_bytes_recursive']
        block_read = sum(io['value'] for io in block_io if io['op'] == 'Read') if block_io else 0
        block_write = sum(io['value'] for io in block_io if io['op'] == 'Write') if block_io else 0
        
        # Get container info
        info = container.attrs
        
        return {
            "status": container.status,
            "uptime": info['State']['StartedAt'],
            "restarts": info['RestartCount'],
            "pids": len(psutil.Process().children()),
            "cpu_percent": round(cpu_percent, 2),
            "mem_usage": mem_usage,
            "mem_limit": mem_limit,
            "mem_percent": round(mem_percent, 2),
            "net_rx": net_rx,
            "net_tx": net_tx,
            "block_read": block_read,
            "block_write": block_write
        }
    except Exception as e:
        return {"error": str(e)} 