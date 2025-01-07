"""Docker-related utility functions."""
import shutil
import subprocess
import os
import platform
from typing import Tuple
from ..style import print_error, print_warning, print_success, print_action

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