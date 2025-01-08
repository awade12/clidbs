"""Print utility functions."""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text
from rich.box import ROUNDED, HEAVY
from rich.console import Group
from rich.style import Style

console = Console()

# Status icons
STATUS_ICONS = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️'
}

def print_success(message: str):
    """green box for good news"""
    console.print(Panel(
        f"{message}",
        style="green",
        box=HEAVY,
        border_style="green",
        title="[bold green]Success[/bold green]",
        title_align="left"
    ))

def print_error(message: str):
    """red box for errors"""
    console.print(Panel(
        f"{message}",
        style="red",
        box=HEAVY,
        border_style="red",
        title="[bold red]Error[/bold red]",
        title_align="left"
    ))

def print_warning(message: str):
    """yellow box for warnings"""
    console.print(Panel(
        f"{message}",
        style="yellow",
        box=HEAVY,
        border_style="yellow",
        title="[bold yellow]Warning[/bold yellow]",
        title_align="left"
    ))

def print_action(action: str, db_name: str, success: bool = True):
    """quick status update with emoji"""
    if success:
        icon = STATUS_ICONS['success']
        color = "green"
        status = "successful"
    else:
        icon = STATUS_ICONS['error']
        color = "red"
        status = "failed"
    
    console.print(Panel(
        f"{icon} {action} '{db_name}' {status}",
        style=color,
        box=HEAVY,
        border_style=color,
        padding=(0, 1)
    )) 