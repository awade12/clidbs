"""ui styling stuff"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text
from rich.box import ROUNDED
from rich.console import Group
from .functions.utils import format_bytes
from .functions.print_utils import (
    console,
    print_success,
    print_error,
    print_warning,
    print_action
)
from typing import Optional

def print_db_info(title: str, info_dict: dict, connection_string: str = None, cli_command: str = None):
    """shows all db info in a nice panel"""
    table = Table(show_header=False, box=ROUNDED, expand=True, padding=(0, 1))
    table.add_column("Key", style="cyan bold")
    table.add_column("Value", style="white")
    
    for key, value in info_dict.items():
        if key in ["Password"]:
            value_style = "yellow bold"
        elif key in ["Host", "Port"]:
            value_style = "green"
        elif key in ["Type", "Version"]:
            value_style = "magenta"
        else:
            value_style = "white"
        table.add_row(f"{key}:", f"[{value_style}]{value}[/{value_style}]")

    sections = [table]
    
    if connection_string:
        sections.append("")
        sections.append(Text("Connection String:", style="cyan bold"))
        sections.append(Syntax(connection_string, "uri", theme="monokai", word_wrap=True))
    
    if cli_command:
        sections.append("")
        sections.append(Text("CLI Command:", style="cyan bold"))
        sections.append(Syntax(cli_command, "bash", theme="monokai"))
    
    console.print(Panel(
        Group(*sections),
        title=f"[bold blue]{title}[/bold blue]",
        box=ROUNDED,
        padding=(1, 2)
    ))

def print_db_list(containers: list):
    """lists all dbs in a table"""
    if not containers:
        print_warning("No databases found")
        return
    
    table = Table(
        title="[bold blue]Databases[/bold blue]",
        box=ROUNDED,
        show_lines=True,
        padding=(0, 1)
    )
    
    table.add_column("Name", style="cyan bold")
    table.add_column("Type", style="magenta")
    table.add_column("Status", style="green")
    
    for name, db_type, status in sorted(containers):
        if status == "running":
            status_style = "[green]⚡ running[/green]"
        elif status == "exited":
            status_style = "[red]⏹ stopped[/red]"
        else:
            status_style = f"[yellow]{status}[/yellow]"
            
        table.add_row(name, db_type, status_style)
    
    console.print(table)

def print_supported_dbs(db_info: str):
    """shows what dbs we support"""
    lines = db_info.split('\n')
    styled_lines = []
    
    for line in lines:
        if line.strip():
            if ':' in line:
                # Database header line
                if '(' in line:
                    name, rest = line.split('(', 1)
                    styled_lines.append(f"[cyan bold]{name}[magenta]({rest}")
                else:
                    key, value = line.split(':', 1)
                    styled_lines.append(f"[cyan bold]{key}:[white]{value}")
            else:
                # Description or version line
                styled_lines.append(f"[white]{line}")
        else:
            styled_lines.append("")
    
    console.print(Panel(
        "\n".join(styled_lines),
        title="[bold blue]Supported Databases[/bold blue]",
        box=ROUNDED,
        padding=(1, 2)
    ))

def print_help_menu():
    """the help screen with all the commands"""
    table = Table(
        title="[bold blue]CLIDB Commands[/bold blue]",
        box=ROUNDED,
        show_lines=True,
        padding=(0, 2)
    )
    
    table.add_column("Command", style="cyan bold")
    table.add_column("Description", style="white")
    table.add_column("Example", style="green")
    
    table.add_row(
        "create",
        "Create a new database",
        "clidb create mydb --type postgres --version 16"
    )
    table.add_row(
        "list",
        "List all databases",
        "clidb list"
    )
    table.add_row(
        "info",
        "Show database connection details",
        "clidb info mydb"
    )
    table.add_row(
        "metrics",
        "Show database performance metrics",
        "clidb metrics mydb --watch"
    )
    table.add_row(
        "start",
        "Start a stopped database",
        "clidb start mydb"
    )
    table.add_row(
        "stop",
        "Stop a running database",
        "clidb stop mydb"
    )
    table.add_row(
        "remove",
        "Remove a database completely",
        "clidb remove mydb"
    )
    table.add_row(
        "backup",
        "Create a database backup",
        "clidb backup mydb --description 'My backup'"
    )
    table.add_row(
        "restore",
        "Restore from backup",
        "clidb restore mydb 20240101_120000"
    )
    table.add_row(
        "backups",
        "List available backups",
        "clidb backups --db mydb"
    )
    table.add_row(
        "delete-backup",
        "Delete a backup",
        "clidb delete-backup mydb 20240101_120000"
    )
    table.add_row(
        "supported",
        "List supported database types",
        "clidb supported"
    )
    table.add_row(
        "ssl",
        "Setup SSL for a database",
        "clidb ssl mydb example.com --email admin@example.com"
    )
    table.add_row(
        "install-docker",
        "Install Docker automatically",
        "clidb install-docker"
    )
    
    options_table = Table(
        title="[bold blue]Common Options[/bold blue]",
        box=ROUNDED,
        show_lines=True,
        padding=(0, 2)
    )
    
    options_table.add_column("Option", style="yellow bold")
    options_table.add_column("Description", style="white")
    options_table.add_column("Default", style="magenta")
    
    options_table.add_row(
        "--type",
        "Database type to create",
        "postgres"
    )
    options_table.add_row(
        "--version",
        "Database version to use",
        "latest"
    )
    options_table.add_row(
        "--access",
        "Database access type (public/private)",
        "public"
    )
    options_table.add_row(
        "--port",
        "Port to expose the database on",
        "auto"
    )
    options_table.add_row(
        "--force",
        "Overwrite existing database",
        "none"
    )
    options_table.add_row(
        "--watch",
        "Watch metrics in real-time",
        "none"
    )
    options_table.add_row(
        "--discord-webhook",
        "Discord webhook URL for notifications",
        "none"
    )
    
    console.print("\n[bold blue]CLIDB - Simple Database Management[/bold blue]\n")
    console.print("[white]A modern CLI tool for managing databases on VPS systems.[/white]\n")
    console.print(table)
    console.print("\n")
    console.print(options_table)
    console.print("\n[bold]For more information, visit: [link=https://github.com/awade12/clidbs]GitHub Repository[/link][/bold]") 

def print_db_metrics(db_name: str, metrics: dict):
    """Display database metrics in a styled format."""
    if "error" in metrics:
        print_error(f"Failed to get metrics for '{db_name}': {metrics['error']}")
        return
        
    # Create main metrics panel
    main_metrics = Table(show_header=False, box=ROUNDED, expand=True)
    main_metrics.add_column("Key", style="cyan bold")
    main_metrics.add_column("Value", style="white")
    
    # Status with color
    status_color = {
        "running": "green",
        "exited": "red",
        "paused": "yellow"
    }.get(metrics["status"], "white")
    
    main_metrics.add_row("Status:", f"[{status_color}]{metrics['status'].upper()}[/{status_color}]")
    main_metrics.add_row("Uptime:", metrics["uptime"])
    main_metrics.add_row("Restarts:", str(metrics["restarts"]))
    main_metrics.add_row("Processes:", str(metrics["pids"]))
    
    # Create resource usage panel
    resource_metrics = Table(
        title="[bold blue]Resource Usage[/bold blue]",
        box=ROUNDED,
        show_header=False,
        title_justify="left"
    )
    resource_metrics.add_column("Type", style="cyan bold")
    resource_metrics.add_column("Usage", style="white")
    
    # CPU usage with color
    cpu_color = "green"
    if metrics["cpu_percent"] > 80:
        cpu_color = "red"
    elif metrics["cpu_percent"] > 60:
        cpu_color = "yellow"
    
    resource_metrics.add_row(
        "CPU:",
        f"[{cpu_color}]{metrics['cpu_percent']}%[/{cpu_color}]"
    )
    
    # Memory usage with color
    mem_color = "green"
    if metrics["mem_percent"] > 80:
        mem_color = "red"
    elif metrics["mem_percent"] > 60:
        mem_color = "yellow"
    
    resource_metrics.add_row(
        "Memory:",
        f"[{mem_color}]{metrics['mem_percent']}% ({format_bytes(metrics['mem_usage'])} / {format_bytes(metrics['mem_limit'])})[/{mem_color}]"
    )
    
    # Create I/O metrics panel
    io_metrics = Table(
        title="[bold blue]I/O Statistics[/bold blue]",
        box=ROUNDED,
        show_header=False,
        title_justify="left"
    )
    io_metrics.add_column("Type", style="cyan bold")
    io_metrics.add_column("Read", style="green")
    io_metrics.add_column("Write", style="yellow")
    
    # Network I/O
    io_metrics.add_row(
        "Network:",
        f"↓ {format_bytes(metrics['net_rx'])}",
        f"↑ {format_bytes(metrics['net_tx'])}"
    )
    
    # Disk I/O
    io_metrics.add_row(
        "Disk:",
        f"↓ {format_bytes(metrics['block_read'])}",
        f"↑ {format_bytes(metrics['block_write'])}"
    )
    
    # Combine all panels
    console.print(Panel(
        Group(
            main_metrics,
            "",  # Spacer
            resource_metrics,
            "",  # Spacer
            io_metrics
        ),
        title=f"[bold blue]Metrics for '{db_name}'[/bold blue]",
        box=ROUNDED,
        padding=(1, 2)
    )) 

def print_backup_list(backups: list):
    """Display list of backups in a table."""
    if not backups:
        print_warning("No backups found")
        return
    
    table = Table(
        title="[bold blue]Database Backups[/bold blue]",
        box=ROUNDED,
        show_lines=True,
        padding=(0, 1)
    )
    
    table.add_column("Database", style="cyan bold")
    table.add_column("Timestamp", style="yellow")
    table.add_column("Type", style="magenta")
    table.add_column("Size", style="green")
    table.add_column("Description", style="white")
    
    for backup in sorted(backups, key=lambda x: x["timestamp"], reverse=True):
        table.add_row(
            backup.get("database", ""),
            backup["timestamp"],
            backup["type"],
            format_bytes(backup["size"]),
            backup.get("description", "") or ""
        )
    
    console.print(table)

def print_backup_result(action: str, db_name: str, success: bool, timestamp: Optional[str] = None):
    """Display backup action result."""
    if success:
        if timestamp:
            print_success(f"{action} for database '{db_name}' completed successfully (timestamp: {timestamp})")
        else:
            print_success(f"{action} for database '{db_name}' completed successfully")
    else:
        print_error(f"{action} for database '{db_name}' failed") 