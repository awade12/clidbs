"""ssl cert stuff"""
import subprocess
import os
import socket
from pathlib import Path
from typing import Optional, List, Tuple
import docker
import time

class SSLManager:
    def __init__(self):
        self.docker_client = docker.from_env()

    def verify_domain(self, domain: str) -> Tuple[bool, str]:
        """check if domain points to this server"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            server_ip = s.getsockname()[0]
            s.close()

            domain_ip = socket.gethostbyname(domain)
            if domain_ip == server_ip:
                return True, "domain check good"
            return False, f"domain {domain} points to {domain_ip}, but server is at {server_ip}"
        except Exception as e:
            return False, f"domain check failed: {str(e)}"

    def setup_nginx(self) -> Tuple[bool, str]:
        """install and set up nginx"""
        try:
            subprocess.run(["apt-get", "update"], check=True)
            subprocess.run(["apt-get", "install", "-y", "nginx"], check=True)

            subprocess.run(["systemctl", "stop", "nginx"], check=False)

            nginx_root = Path("/etc/nginx")
            for d in ["sites-available", "sites-enabled"]:
                dir_path = nginx_root / d
                if dir_path.exists():
                    for f in dir_path.iterdir():
                        f.unlink()
                else:
                    dir_path.mkdir(parents=True)

            nginx_conf = """
            user www-data;
            worker_processes auto;
            pid /run/nginx.pid;

            events {
                worker_connections 768;
            }

            http {
                sendfile on;
                tcp_nopush on;
                types_hash_max_size 2048;
                server_names_hash_bucket_size 64;

                include /etc/nginx/mime.types;
                default_type application/octet-stream;

                access_log /var/log/nginx/access.log;
                error_log /var/log/nginx/error.log;

                include /etc/nginx/conf.d/*.conf;
                include /etc/nginx/sites-enabled/*;
            }
            """
            (nginx_root / "nginx.conf").write_text(nginx_conf)

            default_conf = """
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 404;
}
"""
            (nginx_root / "sites-available/default").write_text(default_conf)
            default_link = nginx_root / "sites-enabled/default"
            if default_link.exists():
                default_link.unlink()
            default_link.symlink_to(nginx_root / "sites-available/default")

            result = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
            if result.returncode != 0:
                return False, f"bad nginx config: {result.stderr}"

            subprocess.run(["systemctl", "start", "nginx"], check=True)
            time.sleep(2)  

            return True, "nginx setup done"
        except subprocess.CalledProcessError as e:
            return False, f"nginx setup failed: {e.stderr if e.stderr else str(e)}"
        except Exception as e:
            return False, f"nginx setup failed: {str(e)}"

    def setup_certbot(self) -> Tuple[bool, str]:
        """install certbot"""
        try:
            subprocess.run(["apt-get", "install", "-y", "certbot", "python3-certbot-nginx"], check=True)
            return True, "certbot installed"
        except subprocess.CalledProcessError as e:
            return False, f"certbot install failed: {e.stderr if e.stderr else str(e)}"
        except Exception as e:
            return False, f"certbot install failed: {str(e)}"

    def configure_site(self, domain: str, port: int) -> Tuple[bool, str]:
        """set up nginx for domain"""
        try:
            config = f"""
server {{
    listen 80;
    listen [::]:80;
    server_name {domain};

    location / {{
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
            sites_available = Path("/etc/nginx/sites-available")
            sites_enabled = Path("/etc/nginx/sites-enabled")

            config_file = sites_available / domain
            config_file.write_text(config)

            link_file = sites_enabled / domain
            if link_file.exists():
                link_file.unlink()
            link_file.symlink_to(config_file)

            result = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
            if result.returncode != 0:
                return False, f"bad site config: {result.stderr}"

            subprocess.run(["systemctl", "reload", "nginx"], check=True)
            return True, "site config done"
        except Exception as e:
            return False, f"site config failed: {str(e)}"

    def setup_ssl(self, domain: str, email: str, db_type: str, port: int, container_name: str) -> Tuple[bool, str]:
        """set up ssl for database"""
        try:
            success, message = self.verify_domain(domain)
            if not success:
                return False, message

            success, message = self.setup_nginx()
            if not success:
                return False, message

            success, message = self.setup_certbot()
            if not success:
                return False, message

            success, message = self.configure_site(domain, port)
            if not success:
                return False, message

            cmd = [
                "certbot", "--nginx",
                "-d", domain,
                "--email", email,
                "--agree-tos",
                "--non-interactive",
                "--redirect"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return False, f"certbot failed: {result.stderr}"

            if db_type == 'postgres':
                try:
                    container = self.docker_client.containers.get(container_name)
                    cert_path = f"/etc/letsencrypt/live/{domain}"
                    
                    container.exec_run("mkdir -p /var/lib/postgresql/ssl")
                    
                    with open(f"{cert_path}/fullchain.pem", 'rb') as f:
                        container.put_archive("/var/lib/postgresql/ssl", f.read())
                    with open(f"{cert_path}/privkey.pem", 'rb') as f:
                        container.put_archive("/var/lib/postgresql/ssl", f.read())
                    
                    container.exec_run("chown -R postgres:postgres /var/lib/postgresql/ssl")
                    container.exec_run("chmod 600 /var/lib/postgresql/ssl/privkey.pem")
                    
                    ssl_conf = """
ssl = on
ssl_cert_file = '/var/lib/postgresql/ssl/fullchain.pem'
ssl_key_file = '/var/lib/postgresql/ssl/privkey.pem'
"""
                    container.exec_run(f'bash -c "echo \'{ssl_conf}\' >> /var/lib/postgresql/data/postgresql.conf"')
                    
                    container.restart()
                except Exception as e:
                    return False, f"postgres ssl setup failed: {str(e)}"

            return True, "ssl setup done"
        except Exception as e:
            return False, f"ssl setup failed: {str(e)}"

    def remove_ssl(self, domain: str) -> Tuple[bool, str]:
        """remove ssl setup"""
        try:
            subprocess.run(["certbot", "delete", "--cert-name", domain, "--non-interactive"], check=False)

            for path in [f"/etc/nginx/sites-available/{domain}", f"/etc/nginx/sites-enabled/{domain}"]:
                if os.path.exists(path):
                    os.unlink(path)

            subprocess.run(["systemctl", "reload", "nginx"], check=True)
            return True, "ssl removed"
        except Exception as e:
            return False, f"ssl removal failed: {str(e)}"

ssl_manager = SSLManager() 