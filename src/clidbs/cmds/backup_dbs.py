from typing import Optional
import click

from ..style import (
    print_backup_list,
    print_backup_result,
    create_loading_status
)

from ..functions.backup_utils import backup_manager

@click.command(name='backup')
@click.argument('db_name')
@click.option('--description', help='Description of the backup')
def backup_cmd(db_name: str, description: Optional[str] = None):
    """Create a backup of a database.
    
    Example: clidb backup mydb --description "Before major update"
    """
    with create_loading_status(f"💾 Creating backup of '{db_name}'...") as status:
        success = backup_manager.create_backup(db_name, description)
        if success:
            status.update(f"✅ Backup of '{db_name}' completed successfully!")
        else:
            status.update(f"❌ Backup of '{db_name}' failed!")
    print_backup_result("Backup", db_name, success)

@click.command(name='restore')
@click.argument('db_name')
@click.argument('timestamp')
def restore_cmd(db_name: str, timestamp: str):
    """Restore a database from backup.
    
    Example: clidb restore mydb 20240101_120000
    """
    with create_loading_status(f"📥 Restoring '{db_name}' from backup...") as status:
        success = backup_manager.restore_backup(db_name, timestamp)
        if success:
            status.update(f"✅ Restore of '{db_name}' completed successfully!")
        else:
            status.update(f"❌ Restore of '{db_name}' failed!")
    print_backup_result("Restore", db_name, success, timestamp)

@click.command(name='backups')
@click.option('--db', help='Filter backups by database name')
def list_backups_cmd(db: Optional[str] = None):
    """List available backups.
    
    Example: clidb backups --db mydb
    """
    backups = backup_manager.list_backups(db)
    print_backup_list(backups)

@click.command(name='delete-backup')
@click.argument('db_name')
@click.argument('timestamp')
def delete_backup_cmd(db_name: str, timestamp: str):
    """Delete a backup.
    
    Example: clidb delete-backup mydb 20240101_120000
    """
    success = backup_manager.delete_backup(db_name, timestamp)
    print_backup_result("Delete backup", db_name, success, timestamp)