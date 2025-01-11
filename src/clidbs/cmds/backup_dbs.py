from typing import Optional
import click

from ..style import (
    print_backup_list,
    print_backup_result,
    create_loading_status,
    print_success,
    print_error
)

from ..functions.backup_utils import backup_manager

@click.command(name='configure-s3')
@click.option('--access-key', required=True, help='AWS access key ID')
@click.option('--secret-key', required=True, help='AWS secret access key')
@click.option('--bucket', required=True, help='S3 bucket name')
@click.option('--region', default='us-east-1', help='AWS region')
def configure_s3_cmd(access_key: str, secret_key: str, bucket: str, region: str):
    """Configure S3 for database backups.
    
    Example: clidb configure-s3 --access-key KEY --secret-key SECRET --bucket my-backup-bucket
    """
    success = backup_manager.configure_s3(access_key, secret_key, bucket, region)
    if success:
        print_success(f"S3 configured successfully with bucket '{bucket}'")
    else:
        print_error("Failed to configure S3")

@click.command(name='backup')
@click.argument('db_name')
@click.option('--description', help='Description of the backup')
@click.option('--s3', is_flag=True, help='Store backup in S3')
def backup_cmd(db_name: str, description: Optional[str] = None, s3: bool = False):
    """Create a backup of a database.
    
    Example: clidb backup mydb --description "Before major update" --s3
    """
    with create_loading_status(f"💾 Creating backup of '{db_name}'...") as status:
        success = backup_manager.create_backup(db_name, description, use_s3=s3)
        if success:
            status.update(f"✅ Backup of '{db_name}' completed successfully!")
            if s3:
                status.update(f"✅ Backup uploaded to S3!")
        else:
            status.update(f"❌ Backup of '{db_name}' failed!")
    print_backup_result("Backup", db_name, success)

@click.command(name='restore')
@click.argument('db_name')
@click.argument('timestamp')
@click.option('--from-s3', is_flag=True, help='Restore from S3 backup')
def restore_cmd(db_name: str, timestamp: str, from_s3: bool = False):
    """Restore a database from backup.
    
    Example: clidb restore mydb 20240101_120000 --from-s3
    """
    with create_loading_status(f"📥 Restoring '{db_name}' from backup...") as status:
        success = backup_manager.restore_backup(db_name, timestamp, from_s3=from_s3)
        if success:
            status.update(f"✅ Restore of '{db_name}' completed successfully!")
        else:
            status.update(f"❌ Restore of '{db_name}' failed!")
    print_backup_result("Restore", db_name, success, timestamp)

@click.command(name='backups')
@click.option('--db', help='Filter backups by database name')
@click.option('--s3-only', is_flag=True, help='Show only S3 backups')
def list_backups_cmd(db: Optional[str] = None, s3_only: bool = False):
    """List available backups.
    
    Example: clidb backups --db mydb --s3-only
    """
    backups = backup_manager.list_backups(db, include_s3=True)
    if s3_only:
        backups = [b for b in backups if b.get("in_s3", False)]
    print_backup_list(backups)

@click.command(name='delete-backup')
@click.argument('db_name')
@click.argument('timestamp')
@click.option('--keep-s3', is_flag=True, help='Keep backup in S3 when deleting locally')
def delete_backup_cmd(db_name: str, timestamp: str, keep_s3: bool = False):
    """Delete a backup.
    
    Example: clidb delete-backup mydb 20240101_120000 --keep-s3
    """
    success = backup_manager.delete_backup(db_name, timestamp, delete_from_s3=not keep_s3)
    print_backup_result("Delete backup", db_name, success, timestamp)