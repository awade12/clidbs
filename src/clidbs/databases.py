"""Database configurations and templates for CLIDB."""
from dataclasses import dataclass
from typing import Dict, List, Optional
import json
from pathlib import Path

@dataclass
class DatabaseCredentials:
    """stores login info for a database"""
    db_type: str
    version: Optional[str]
    user: str
    password: str
    port: int
    host: str
    access: str
    name: str
    webhook_url: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "db_type": self.db_type,
            "version": self.version,
            "user": self.user,
            "password": self.password,
            "port": self.port,
            "host": self.host,
            "access": self.access,
            "name": self.name,
            "webhook_url": self.webhook_url
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DatabaseCredentials':
        return cls(**data)

class CredentialsManager:
    """handles saving and loading database passwords"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "clidb"
        self.creds_file = self.config_dir / "credentials.json"
        self._ensure_secure_directory()
        self._load_credentials()

    def _ensure_secure_directory(self):
        """create and lock down config folder"""
        # create dir if needed
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # only owner can access dir (700)
        self.config_dir.chmod(0o700)

    def _secure_file(self, path: Path):
        """lock down file access"""
        # only owner can read/write (600)
        path.chmod(0o600)

    def _load_credentials(self):
        """load saved passwords"""
        if self.creds_file.exists():
            self._secure_file(self.creds_file)
            with self.creds_file.open('r') as f:
                self.credentials = {
                    name: DatabaseCredentials.from_dict(data)
                    for name, data in json.load(f).items()
                }
        else:
            self.credentials = {}

    def _save_credentials(self):
        """save passwords securely"""
        # write to temp file first
        temp_file = self.creds_file.with_suffix('.tmp')
        with temp_file.open('w') as f:
            json.dump({
                name: creds.to_dict()
                for name, creds in self.credentials.items()
            }, f, indent=2)
        
        # lock down temp file
        self._secure_file(temp_file)
        
        # swap old file with new one
        temp_file.replace(self.creds_file)
        
        # make sure perms are right
        self._secure_file(self.creds_file)

    def store_credentials(self, creds: DatabaseCredentials):
        """save login info for a database"""
        self.credentials[creds.name] = creds
        self._save_credentials()

    def get_credentials(self, db_name: str) -> Optional[DatabaseCredentials]:
        """get login info for a database"""
        return self.credentials.get(db_name)

    def remove_credentials(self, db_name: str):
        """delete login info for a database"""
        if db_name in self.credentials:
            del self.credentials[db_name]
            self._save_credentials()

@dataclass
class DatabaseConfig:
    """settings for each type of database"""
    name: str
    image: str
    default_port: int
    environment_prefix: str
    volumes: Optional[List[str]] = None
    command: Optional[str] = None
    default_version: str = "latest"
    supported_versions: List[str] = None
    description: str = ""

    def get_env_vars(self, db_name: str, user: str, password: str) -> List[str]:
        """Get environment variables for this database type."""
        if self.environment_prefix == "POSTGRES":
            return [
                f"POSTGRES_DB={db_name}",
                f"POSTGRES_USER={user}",
                f"POSTGRES_PASSWORD={password}"
            ]
        elif self.environment_prefix == "MYSQL":
            return [
                f"MYSQL_DATABASE={db_name}",
                f"MYSQL_USER={user}",
                f"MYSQL_PASSWORD={password}",
                "MYSQL_RANDOM_ROOT_PASSWORD=yes"
            ]
        elif self.environment_prefix == "MONGO":
            return [
                f"MONGO_INITDB_DATABASE={db_name}",
                f"MONGO_INITDB_ROOT_USERNAME={user}",
                f"MONGO_INITDB_ROOT_PASSWORD={password}"
            ]
        elif self.environment_prefix == "CLICKHOUSE":
            return [
                f"CLICKHOUSE_DB={db_name}",
                f"CLICKHOUSE_USER={user}",
                f"CLICKHOUSE_PASSWORD={password}",
                "CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1"
            ]
        return []

# databases 
DATABASES: Dict[str, DatabaseConfig] = {
    "postgres": DatabaseConfig(
        name="PostgreSQL",
        image="postgres",
        default_port=5432,
        environment_prefix="POSTGRES",
        supported_versions=["16", "15", "14", "13", "12", "11"],
        description="Advanced open source relational database"
    ),
    
    "mysql": DatabaseConfig(
        name="MySQL",
        image="mysql",
        default_port=3306,
        environment_prefix="MYSQL",
        supported_versions=["8.0", "5.7"],
        description="Popular open source relational database"
    ),
    
    "mariadb": DatabaseConfig(
        name="MariaDB",
        image="mariadb",
        default_port=3306,
        environment_prefix="MYSQL",
        supported_versions=["11.2", "11.1", "11.0", "10.11", "10.10"],
        description="Community-developed fork of MySQL"
    ),
    
    "redis": DatabaseConfig(
        name="Redis",
        image="redis",
        default_port=6379,
        environment_prefix="REDIS",
        command="redis-server --requirepass ${REDIS_PASSWORD}",
        supported_versions=["7.2", "7.0", "6.2"],
        description="In-memory data structure store"
    ),
    
    "keydb": DatabaseConfig(
        name="KeyDB",
        image="eqalpha/keydb",
        default_port=6379,
        environment_prefix="REDIS",
        command="keydb-server --requirepass ${REDIS_PASSWORD}",
        supported_versions=["6.3", "6.2", "6.1"],
        description="Multithreaded fork of Redis with better performance"
    ),
    
    "clickhouse": DatabaseConfig(
        name="ClickHouse",
        image="clickhouse/clickhouse-server",
        default_port=8123,
        environment_prefix="CLICKHOUSE",
        volumes=["/var/lib/clickhouse"],
        supported_versions=["23.12", "23.11", "23.10", "23.9"],
        description="Column-oriented database for real-time analytics"
    ),
    
    "mongo": DatabaseConfig(
        name="MongoDB",
        image="mongo",
        default_port=27017,
        environment_prefix="MONGO",
        supported_versions=["7.0", "6.0", "5.0"],
        description="NoSQL document database"
    ),
    
    "neo4j": DatabaseConfig(
        name="Neo4j",
        image="neo4j",
        default_port=7687,
        environment_prefix="NEO4J",
        volumes=["/data"],
        supported_versions=["5", "4.4"],
        description="Graph database management system"
    ),
    
    "scylladb": DatabaseConfig(
        name="ScyllaDB",
        image="scylladb/scylla",
        default_port=9042,
        environment_prefix="SCYLLA",
        volumes=["/var/lib/scylla"],
        supported_versions=["5.2", "5.1", "5.0"],
        description="fast nosql db, cassandra compatible"
    ),
    
    "elasticsearch": DatabaseConfig(
        name="Elasticsearch",
        image="elasticsearch",
        default_port=9200,
        environment_prefix="ELASTIC",
        volumes=["/usr/share/elasticsearch/data"],
        supported_versions=["8.11", "8.10", "8.9"],
        description="search and analytics engine"
    ),

    "meilisearch": DatabaseConfig(
        name="Meilisearch",
        image="getmeili/meilisearch",
        default_port=7700,
        environment_prefix="MEILI",
        volumes=["/meili_data"],
        supported_versions=["v1.5", "v1.4", "v1.3"],
        description="lightning fast search engine"
    ),

    "timescaledb": DatabaseConfig(
        name="TimescaleDB",
        image="timescale/timescaledb",
        default_port=5432,
        environment_prefix="POSTGRES",
        supported_versions=["2.12", "2.11", "2.10"],
        description="time series sql database"
    ),

    "influxdb": DatabaseConfig(
        name="InfluxDB",
        image="influxdb",
        default_port=8086,
        environment_prefix="INFLUXDB",
        volumes=["/var/lib/influxdb2"],
        supported_versions=["2.7", "2.6", "2.5"],
        description="time series database"
    ),

    "cockroachdb": DatabaseConfig(
        name="CockroachDB",
        image="cockroachdb/cockroach",
        default_port=26257,
        environment_prefix="COCKROACH",
        volumes=["/cockroach/data"],
        supported_versions=["v23.1", "v22.2", "v22.1"],
        description="distributed sql database"
    )
}

def get_database_config(db_type: str, version: Optional[str] = None) -> DatabaseConfig:
    """get settings for a specific database type"""
    if db_type not in DATABASES:
        raise ValueError(f"Unsupported database type: {db_type}")
    
    config = DATABASES[db_type]
    
    if version:
        if version not in config.supported_versions:
            raise ValueError(
                f"Unsupported version {version} for {db_type}. "
                f"Supported versions: {', '.join(config.supported_versions)}"
            )
        return DatabaseConfig(
            **{**config.__dict__, "image": f"{config.image}:{version}"}
        )
    
    return config

def list_supported_databases() -> str:
    """show all available databases and their versions"""
    output = []
    for db_type, config in DATABASES.items():
        versions = ", ".join(config.supported_versions) if config.supported_versions else "latest"
        output.append(f"{config.name} ({db_type}):")
        output.append(f"  Description: {config.description}")
        output.append(f"  Versions: {versions}")
        output.append(f"  Default port: {config.default_port}")
        output.append("")
    
    return "\n".join(output) 

credentials_manager = CredentialsManager() 