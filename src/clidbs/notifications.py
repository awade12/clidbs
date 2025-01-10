import requests
from typing import Optional, Dict, Any
from enum import Enum
import os
from datetime import datetime
from .config import Config

class EventType(Enum):
    """Types of events that can trigger notifications."""
    DB_CREATED = "Database Created"
    DB_CREATION_FAILED = "Database Creation Failed"
    DB_STOPPED = "Database Stopped"
    DB_STOP_FAILED = "Database Stop Failed"
    DB_STARTED = "Database Started"
    DB_START_FAILED = "Database Start Failed"
    DB_REMOVED = "Database Removed"
    DB_REMOVE_FAILED = "Database Remove Failed"
    DB_ERROR = "Database Error"
    DB_HEALTH_WARNING = "Database Health Warning"
    SSL_SETUP = "SSL Setup Complete"
    SSL_SETUP_FAILED = "SSL Setup Failed"

class NotificationManager:
    """Manages sending notifications for database events."""
    
    def __init__(self):
        self.config = Config.load()
        self._colors = {
            EventType.DB_CREATED: 3066993,  # Green
            EventType.DB_CREATION_FAILED: 15158332,  # Red
            EventType.DB_STOPPED: 15844367,  # Orange
            EventType.DB_STOP_FAILED: 15158332,  # Red
            EventType.DB_STARTED: 3066993,  # Green
            EventType.DB_START_FAILED: 15158332,  # Red
            EventType.DB_REMOVED: 10181046,  # Purple
            EventType.DB_REMOVE_FAILED: 15158332,  # Red
            EventType.DB_ERROR: 15158332,  # Red
            EventType.DB_HEALTH_WARNING: 16776960,  # Yellow
            EventType.SSL_SETUP: 3447003,  # Blue
            EventType.SSL_SETUP_FAILED: 15158332,  # Red
        }

    def _get_webhook_url(self, webhook_url: Optional[str] = None) -> Optional[str]:
        """Get webhook URL from parameter or environment."""
        return webhook_url or self.config.discord_webhook_url

    def _create_embed(self, 
                     event_type: EventType, 
                     db_info: Dict[str, Any],
                     error_message: Optional[str] = None) -> Dict[str, Any]:
        """Create a Discord embed for the notification."""
        embed = {
            "title": event_type.value,
            "color": self._colors[event_type],
            "timestamp": datetime.utcnow().isoformat(),
            "fields": []
        }

        if "name" in db_info:
            embed["fields"].append({
                "name": "Database",
                "value": db_info["name"],
                "inline": True
            })
        
        if "type" in db_info:
            embed["fields"].append({
                "name": "Type",
                "value": db_info["type"],
                "inline": True
            })
            
        if "version" in db_info:
            embed["fields"].append({
                "name": "Version",
                "value": db_info["version"] or "latest",
                "inline": True
            })

        if "host" in db_info:
            embed["fields"].append({
                "name": "Host",
                "value": db_info["host"],
                "inline": True
            })
            
        if "port" in db_info:
            embed["fields"].append({
                "name": "Port",
                "value": str(db_info["port"]),
                "inline": True
            })
            
        if "access" in db_info:
            embed["fields"].append({
                "name": "Access",
                "value": db_info["access"].upper(),
                "inline": True
            })

        if error_message:
            embed["fields"].append({
                "name": "Error Details",
                "value": f"```\n{error_message}\n```",
                "inline": False
            })

        return embed

    def send_notification(self, 
                         event_type: EventType, 
                         db_info: Dict[str, Any],
                         webhook_url: Optional[str] = None,
                         error_message: Optional[str] = None) -> bool:
        """
        Send a notification for a database event.
        
        Args:
            event_type: Type of event that occurred
            db_info: Dictionary containing database information
            webhook_url: Optional webhook URL (falls back to environment variable)
            error_message: Optional error message for failure events
            
        Returns:
            bool: True if notification was sent successfully
        """
        webhook_url = self._get_webhook_url(webhook_url)
        if not webhook_url:
            return False

        try:
            embed = self._create_embed(event_type, db_info, error_message)
            data = {"embeds": [embed]}
            
            response = requests.post(webhook_url, json=data)
            return response.status_code == 204
        except Exception as e:
            print(f"Failed to send Discord notification: {str(e)}")
            return False

notification_manager = NotificationManager() 