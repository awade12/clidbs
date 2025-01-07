"""Print utility functions."""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text
from rich.box import ROUNDED
from rich.console import Group

console = Console()

def print_success(message: str):
    """green box for good news"""
    console.print(Panel(message, style="green", box=ROUNDED))

def print_error(message: str):
    """red box for errors"""
    console.print(Panel(f"[red bold]Error:[/red bold] {message}", style="red", box=ROUNDED))

def print_warning(message: str):
    """yellow box for warnings"""
    console.print(Panel(f"[yellow bold]Warning:[/yellow bold] {message}", style="yellow", box=ROUNDED))

def print_action(action: str, db_name: str, success: bool = True):
    """quick status update with emoji"""
    if success:
        emoji = "✅"
        color = "green"
    else:
        emoji = "❌"
        color = "red"
    
    console.print(f"[{color}]{emoji} {action} '{db_name}' {success and 'successful' or 'failed'}[/{color}]") 