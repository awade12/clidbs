"""Backup and restore functionality for databases."""
import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import docker
import boto3
from botocore.exceptions import ClientError
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
        self.s3_client = None
        self.s3_bucket = None

    def configure_s3(self, aws_access_key_id: str, aws_secret_access_key: str, bucket: str, region: str = 'us-east-1') -> bool:
        """Configure S3 credentials and bucket for backups.
        
        Args:
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            bucket: S3 bucket name
            region: AWS region (default: us-east-1)
            
        Returns:
            bool: True if configuration was successful
        """
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region
            )
            
            # Test the connection by listing buckets
            self.s3_client.list_buckets()
            
            # Check if bucket exists, create if it doesn't
            try:
                self.s3_client.head_bucket(Bucket=bucket)
            except ClientError:
                self.s3_client.create_bucket(Bucket=bucket)
            
            self.s3_bucket = bucket
            return True
        except Exception as e:
            print_error(f"Failed to configure S3: {str(e)}")
            self.s3_client = None
            self.s3_bucket = None
            return False

    def _upload_to_s3(self, file_path: Path, s3_key: str) -> bool:
        """Upload a file to S3.
        
        Args:
            file_path: Local file path
            s3_key: S3 object key
            
        Returns:
            bool: True if upload was successful
        """
        if not self.s3_client or not self.s3_bucket:
            raise Exception("S3 not configured. Call configure_s3() first.")
        
        try:
            self.s3_client.upload_file(str(file_path), self.s3_bucket, s3_key)
            return True
        except Exception as e:
            print_error(f"Failed to upload to S3: {str(e)}")
            return False

    def _download_from_s3(self, s3_key: str, local_path: Path) -> bool:
        """Download a file from S3.
        
        Args:
            s3_key: S3 object key
            local_path: Local file path to save to
            
        Returns:
            bool: True if download was successful
        """
        if not self.s3_client or not self.s3_bucket:
            raise Exception("S3 not configured. Call configure_s3() first.")
        
        try:
            self.s3_client.download_file(self.s3_bucket, s3_key, str(local_path))
            return True
        except Exception as e:
            print_error(f"Failed to download from S3: {str(e)}")
            return False

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

    def create_backup(self, db_name: str, description: Optional[str] = None, use_s3: bool = False) -> bool:
        """Create a backup of a database.
        
        Args:
            db_name: Name of the database to backup
            description: Optional description of the backup
            use_s3: Whether to store the backup in S3
            
        Returns:
            bool: True if backup was successful
        """
        try:
            if use_s3 and not self.s3_client:
                raise Exception("S3 not configured. Call configure_s3() first.")

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
            
            # After creating the local backup, upload to S3 if requested
            if use_s3:
                s3_key = f"backups/{db_name}/{timestamp}.backup"
                if not self._upload_to_s3(backup_path, s3_key):
                    raise Exception("Failed to upload backup to S3")
                
                # Update metadata with S3 information
                self.metadata[db_name][-1].update({
                    "s3_bucket": self.s3_bucket,
                    "s3_key": s3_key
                })
                self._save_metadata()
            
            return True
            
        except Exception as e:
            print_error(f"Failed to create backup: {str(e)}")
            return False

    def restore_backup(self, db_name: str, timestamp: str, from_s3: bool = False) -> bool:
        """Restore a database from backup.
        
        Args:
            db_name: Name of the database to restore
            timestamp: Timestamp of the backup to restore
            from_s3: Whether to restore from S3
            
        Returns:
            bool: True if restore was successful
        """
        try:
            if from_s3 and not self.s3_client:
                raise Exception("S3 not configured. Call configure_s3() first.")

            # Find the backup metadata
            backup = self._find_backup(db_name, timestamp)
            if not backup:
                raise Exception(f"No backup found with timestamp {timestamp}")

            # If restoring from S3, download the backup first
            if from_s3:
                if "s3_key" not in backup:
                    raise Exception("This backup is not stored in S3")
                
                temp_path = self.backup_dir / f"temp_{db_name}_{timestamp}.backup"
                if not self._download_from_s3(backup["s3_key"], temp_path):
                    raise Exception("Failed to download backup from S3")
                backup_path = temp_path
            else:
                backup_path = Path(backup["path"])

            client = docker.from_env()
            container = find_container(client, db_name)
            if not container:
                raise Exception(f"Database '{db_name}' not found")

            # Get database credentials
            creds = credentials_manager.get_credentials(db_name)
            if not creds:
                raise Exception(f"No credentials found for database '{db_name}'")
            
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
            
            # Clean up temporary file if using S3
            if from_s3 and temp_path.exists():
                temp_path.unlink()

            return True
            
        except Exception as e:
            print_error(f"Failed to restore backup: {str(e)}")
            return False

    def _find_backup(self, db_name: str, timestamp: str) -> Optional[Dict]:
        """Find a backup by database name and timestamp."""
        if db_name not in self.metadata:
            return None
        
        for backup in self.metadata[db_name]:
            if backup["timestamp"] == timestamp:
                return backup
        return None

    def list_backups(self, db_name: Optional[str] = None, include_s3: bool = True) -> List[Dict]:
        """List available backups.
        
        Args:
            db_name: Optional database name to filter backups
            include_s3: Whether to include S3 backup information
            
        Returns:
            List of backup metadata
        """
        backups = super().list_backups(db_name)
        if include_s3:
            for backup in backups:
                backup["in_s3"] = "s3_key" in backup
        return backups

    def delete_backup(self, db_name: str, timestamp: str, delete_from_s3: bool = True) -> bool:
        """Delete a backup.
        
        Args:
            db_name: Name of the database
            timestamp: Timestamp of the backup to delete
            delete_from_s3: Whether to also delete from S3 if present
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            backup = self._find_backup(db_name, timestamp)
            if not backup:
                raise Exception(f"No backup found with timestamp {timestamp}")

            # Delete from S3 if requested and backup exists there
            if delete_from_s3 and "s3_key" in backup:
                try:
                    self.s3_client.delete_object(
                        Bucket=backup["s3_bucket"],
                        Key=backup["s3_key"]
                    )
                except Exception as e:
                    print_warning(f"Failed to delete from S3: {str(e)}")

            # ... [existing delete code] ...

            return True
            
        except Exception as e:
            print_error(f"Failed to delete backup: {str(e)}")
            return False

# Initialize backup manager as singleton
backup_manager = BackupManager() 