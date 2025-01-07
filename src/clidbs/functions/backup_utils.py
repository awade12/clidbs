"""Backup and restore functionality for databases."""
import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import docker
from .docker_utils import find_container
from .print_utils import print_error, print_warning, print_success, print_action
from ..databases import get_database_config, DatabaseCredentials, credentials_manager
import subprocess

class BackupManager:
    """Manages database backups and restores."""
    
    def __init__(self):
        self.backup_dir = Path.home() / ".config" / "clidb" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.backup_dir / "backup_metadata.json"
        self._load_metadata()

    def _load_metadata(self):
        """Load backup metadata from file."""
        if self.metadata_file.exists():
            with self.metadata_file.open('r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}
            self._save_metadata()

    def _save_metadata(self):
        """Save backup metadata to file."""
        with self.metadata_file.open('w') as f:
            json.dump(self.metadata, f, indent=2)

    def _get_backup_path(self, db_name: str, timestamp: str) -> Path:
        """Get the path for a backup file."""
        return self.backup_dir / f"{db_name}_{timestamp}.backup"

    def create_backup(self, db_name: str, description: Optional[str] = None) -> bool:
        """
        Create a backup of a database.
        
        Args:
            db_name: Name of the database to backup
            description: Optional description of the backup
            
        Returns:
            bool: True if backup was successful
        """
        try:
            client = docker.from_env()
            container = find_container(client, db_name)
            if not container:
                raise Exception(f"Database '{db_name}' not found")

            # Get database credentials
            creds = credentials_manager.get_credentials(db_name)
            if not creds:
                raise Exception(f"No credentials found for database '{db_name}'")

            # Get database configuration
            db_config = get_database_config(creds.db_type, creds.version)
            
            # Generate timestamp for backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self._get_backup_path(db_name, timestamp)
            
            # Create backup based on database type
            if creds.db_type == "postgres":
                # Use docker exec to run pg_dump inside the container
                cmd = [
                    "docker", "exec",
                    "-e", f"PGPASSWORD={creds.password}",
                    container.name,
                    "pg_dump",
                    "-U", creds.user,
                    "-d", db_name,
                    "-F", "c"  # Use custom format for better compression
                ]
                
                # Execute pg_dump and save output to file
                with open(backup_path, 'wb') as f:
                    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)
                    if result.returncode != 0:
                        raise Exception(f"pg_dump failed: {result.stderr.decode()}")
                    
            elif creds.db_type == "mysql" or creds.db_type == "mariadb":
                # Use docker exec for MySQL backup
                cmd = [
                    "docker", "exec",
                    "-e", f"MYSQL_PWD={creds.password}",
                    container.name,
                    "mysqldump",
                    "-u", creds.user,
                    db_name
                ]
                
                with open(backup_path, 'wb') as f:
                    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)
                    if result.returncode != 0:
                        raise Exception(f"mysqldump failed: {result.stderr.decode()}")
                    
            elif creds.db_type == "mongo":
                # Use docker exec for MongoDB backup
                cmd = [
                    "docker", "exec",
                    container.name,
                    "mongodump",
                    "--uri", f"mongodb://{creds.user}:{creds.password}@localhost:27017/{db_name}",
                    "--archive"
                ]
                
                with open(backup_path, 'wb') as f:
                    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)
                    if result.returncode != 0:
                        raise Exception(f"mongodump failed: {result.stderr.decode()}")
            else:
                # For other databases, just copy the data directory
                data_dir = container.attrs['Mounts'][0]['Source']
                shutil.copytree(data_dir, backup_path)

            # Store backup metadata
            if db_name not in self.metadata:
                self.metadata[db_name] = []
            
            self.metadata[db_name].append({
                "timestamp": timestamp,
                "path": str(backup_path),
                "description": description,
                "type": creds.db_type,
                "version": creds.version,
                "size": os.path.getsize(backup_path)
            })
            self._save_metadata()
            
            return True
            
        except Exception as e:
            print_error(f"Failed to create backup: {str(e)}")
            return False

    def restore_backup(self, db_name: str, timestamp: str) -> bool:
        """
        Restore a database from backup.
        
        Args:
            db_name: Name of the database to restore
            timestamp: Timestamp of the backup to restore
            
        Returns:
            bool: True if restore was successful
        """
        try:
            if db_name not in self.metadata:
                raise Exception(f"No backups found for database '{db_name}'")
            
            # Find the backup with the given timestamp
            backup = None
            for b in self.metadata[db_name]:
                if b["timestamp"] == timestamp:
                    backup = b
                    break
            
            if not backup:
                raise Exception(f"No backup found with timestamp {timestamp}")
            
            client = docker.from_env()
            container = find_container(client, db_name)
            if not container:
                raise Exception(f"Database '{db_name}' not found")

            # Get database credentials
            creds = credentials_manager.get_credentials(db_name)
            if not creds:
                raise Exception(f"No credentials found for database '{db_name}'")
            
            backup_path = Path(backup["path"])
            if not backup_path.exists():
                raise Exception(f"Backup file not found: {backup_path}")

            # Restore based on database type
            if backup["type"] == "postgres":
                cmd = f"psql -U {creds.user} -h localhost -p {creds.port} {db_name} < {backup_path}"
            elif backup["type"] in ["mysql", "mariadb"]:
                cmd = f"mysql -u {creds.user} -p{creds.password} -h localhost -P {creds.port} {db_name} < {backup_path}"
            elif backup["type"] == "mongo":
                cmd = f"mongorestore --uri='mongodb://{creds.user}:{creds.password}@localhost:{creds.port}/{db_name}' --archive={backup_path}"
            else:
                # For other databases, stop container and replace data directory
                container.stop()
                data_dir = container.attrs['Mounts'][0]['Source']
                shutil.rmtree(data_dir)
                shutil.copytree(backup_path, data_dir)
                container.start()
                return True

            # Execute restore command
            exit_code = container.exec_run(cmd).exit_code
            if exit_code != 0:
                raise Exception(f"Restore command failed with exit code {exit_code}")
            
            return True
            
        except Exception as e:
            print_error(f"Failed to restore backup: {str(e)}")
            return False

    def list_backups(self, db_name: Optional[str] = None) -> List[Dict]:
        """
        List available backups.
        
        Args:
            db_name: Optional database name to filter backups
            
        Returns:
            List of backup metadata
        """
        if db_name:
            return self.metadata.get(db_name, [])
        
        all_backups = []
        for db, backups in self.metadata.items():
            for backup in backups:
                backup["database"] = db
                all_backups.append(backup)
        return all_backups

    def delete_backup(self, db_name: str, timestamp: str) -> bool:
        """
        Delete a backup.
        
        Args:
            db_name: Name of the database
            timestamp: Timestamp of the backup to delete
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            if db_name not in self.metadata:
                raise Exception(f"No backups found for database '{db_name}'")
            
            # Find and remove the backup
            backup = None
            for i, b in enumerate(self.metadata[db_name]):
                if b["timestamp"] == timestamp:
                    backup = self.metadata[db_name].pop(i)
                    break
            
            if not backup:
                raise Exception(f"No backup found with timestamp {timestamp}")
            
            # Delete the backup file
            backup_path = Path(backup["path"])
            if backup_path.exists():
                if backup_path.is_dir():
                    shutil.rmtree(backup_path)
                else:
                    backup_path.unlink()
            
            # Save updated metadata
            self._save_metadata()
            return True
            
        except Exception as e:
            print_error(f"Failed to delete backup: {str(e)}")
            return False

# Initialize backup manager as singleton
backup_manager = BackupManager() 