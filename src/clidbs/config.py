from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path

class Config(BaseModel):
    """Configuration settings for the CLI."""
    discord_webhook_url: Optional[str] = None
    default_db_type: str = "postgres"
    default_port: int = 5432
    
    @classmethod
    def load(cls):
        """Load configuration from environment variables."""
        return cls(
            discord_webhook_url=os.getenv("CLIDB_DISCORD_WEBHOOK"),
            default_db_type=os.getenv("CLIDB_DEFAULT_DB", "postgres"),
            default_port=int(os.getenv("CLIDB_DEFAULT_PORT", "5432"))
        )
    
    def save(self):
        """Save configuration to environment file."""
        config_dir = Path.home() / ".config" / "clidb"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        env_file = config_dir / ".env"
        with env_file.open("w") as f:
            if self.discord_webhook_url:
                f.write(f"CLIDB_DISCORD_WEBHOOK={self.discord_webhook_url}\n")
            f.write(f"CLIDB_DEFAULT_DB={self.default_db_type}\n")
            f.write(f"CLIDB_DEFAULT_PORT={self.default_port}\n") 