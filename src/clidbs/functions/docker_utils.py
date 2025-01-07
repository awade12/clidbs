"""Docker-related utility functions."""
import shutil
import subprocess
import os
import platform
from typing import Tuple, Optional
from ..style import print_error, print_warning, print_success, print_action
import docker
import socket
import psutil
from datetime import datetime

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

def is_port_available(port: int) -> bool:
    """Check if a port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', port))
            return True
        except OSError:
            return False

def find_next_available_port(start_port: int, max_attempts: int = 100) -> Optional[int]:
    """
    Find the next available port starting from start_port.
    
    Args:
        start_port: Port to start searching from
        max_attempts: Maximum number of ports to try
        
    Returns:
        Next available port or None if no ports are available
    """
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(port):
            return port
    return None 

def check_container_exists(client: docker.DockerClient, name: str) -> bool:
    """Check if a container with the given name exists (running or stopped)."""
    try:
        containers = client.containers.list(all=True)  # all=True includes stopped containers
        return any(container.name == name for container in containers)
    except Exception:
        return False

def remove_container_if_exists(client: docker.DockerClient, name: str) -> bool:
    """
    Remove a container if it exists (running or stopped).
    
    Args:
        client: Docker client
        name: Container name
        
    Returns:
        bool: True if container was removed, False if it didn't exist
    """
    try:
        container = client.containers.get(name)
        container.remove(force=True)  # force=True will stop it if running
        return True
    except docker.errors.NotFound:
        return False
    except Exception as e:
        raise Exception(f"Failed to remove existing container: {str(e)}") 

def get_container_metrics(container) -> dict:
    """
    Get detailed metrics for a container.
    
    Args:
        container: Docker container object
        
    Returns:
        Dictionary containing metrics
    """
    try:
        # Get container stats
        stats = container.stats(stream=False)
        
        # CPU Usage
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        cpu_percent = 0.0
        if system_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"]) * 100.0
        
        # Memory Usage
        mem_usage = stats["memory_stats"]["usage"]
        mem_limit = stats["memory_stats"]["limit"]
        mem_percent = (mem_usage / mem_limit) * 100.0
        
        # Network I/O
        net_stats = stats["networks"]["eth0"] if "networks" in stats and "eth0" in stats["networks"] else {"rx_bytes": 0, "tx_bytes": 0}
        
        # Block I/O
        io_stats = {"read_bytes": 0, "write_bytes": 0}
        if "blkio_stats" in stats and "io_service_bytes_recursive" in stats["blkio_stats"]:
            for stat in stats["blkio_stats"]["io_service_bytes_recursive"]:
                if stat["op"] == "Read":
                    io_stats["read_bytes"] += stat["value"]
                elif stat["op"] == "Write":
                    io_stats["write_bytes"] += stat["value"]
        
        # Get container info
        info = container.attrs
        
        # Format uptime
        created = datetime.strptime(info["Created"].split(".")[0], "%Y-%m-%dT%H:%M:%S")
        uptime = datetime.now() - created
        
        return {
            "status": info["State"]["Status"],
            "uptime": str(uptime).split(".")[0],  # Remove microseconds
            "cpu_percent": round(cpu_percent, 2),
            "mem_usage": mem_usage,
            "mem_limit": mem_limit,
            "mem_percent": round(mem_percent, 2),
            "net_rx": net_stats["rx_bytes"],
            "net_tx": net_stats["tx_bytes"],
            "block_read": io_stats["read_bytes"],
            "block_write": io_stats["write_bytes"],
            "pids": stats["pids_stats"]["current"] if "pids_stats" in stats else 0,
            "restarts": info["RestartCount"] if "RestartCount" in info else 0
        }
    except Exception as e:
        return {
            "error": str(e)
        }

def format_bytes(bytes_value: int) -> str:
    """Format bytes into human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.2f} PB" 