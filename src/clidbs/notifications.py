import requests
from typing import Optional

def send_discord_notification(webhook_url: str, message: str, title: Optional[str] = None) -> bool:
    """
    Send a notification to Discord using a webhook.
    
    Args:
        webhook_url: The Discord webhook URL
        message: The message to send
        title: Optional title for the message
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        data = {
            "content": message if not title else None,
            "embeds": [{
                "title": title,
                "description": message,
                "color": 5814783  # Blue color
            }] if title else None
        }
        
        response = requests.post(webhook_url, json=data)
        return response.status_code == 204
    except Exception as e:
        print(f"Failed to send Discord notification: {str(e)}")
        return False 