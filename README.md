# CLIDB - Simple Database Management CLI

A command-line tool for managing databases on VPS systems using Docker containers. Supports multiple database types and provides ready-to-use connection strings.

## Supported Databases

- PostgreSQL (versions 11-16)
- MySQL (8.0, 5.7)
- MariaDB (11.0, 10.11, 10.10)
- Redis (7.2, 7.0, 6.2)
- MongoDB (7.0, 6.0, 5.0)
- Neo4j (5, 4.4)

## Prerequisites

- Python 3.8 or higher
- Docker installed and running
- pip (Python package installer)

## Installation

```bash
pip install clidbs
```

## Usage

### Create a Database

```bash
# Create a PostgreSQL database (latest version)
clidb create mydb

# Create a specific version
clidb create mydb --type postgres --version 16

# Create other database types
clidb create myredis --type redis --version 7.2
clidb create mymongo --type mongo
clidb create mysql1 --type mysql --version 8.0
```

The tool will output connection details including:
- Connection string (ready to copy/paste)
- CLI command with credentials
- Host/IP address (automatically detected)
- Port, user, and password

### Manage Databases

```bash
# List all databases
clidb list

# Stop a database
clidb stop mydb

# Start a database
clidb start mydb

# Remove a database
clidb remove mydb

# See supported databases and versions
clidb supported

# View database connection details
clidb info mydb

# Reset database password
clidb info mydb --reset-password

or 

# Create a ClickHouse database
clidb create myanalytics --type clickhouse --version 23.12

# Create a KeyDB instance
clidb create mycache --type keydb --version 6.3

# Create a MariaDB database with latest version
clidb create mydb --type mariadb --version 11.2
```

### Public vs Private Access

```bash
# Create with public access (default)
clidb create mydb --access public

# Create with private access (localhost only)
clidb create mydb --access private
```

### Discord Notifications

Enable notifications by:

1. Setting the webhook URL in command:
```bash
clidb create mydb --discord-webhook "YOUR_WEBHOOK_URL"
```

2. Or using environment variable:
```bash
export CLIDB_DISCORD_WEBHOOK="YOUR_WEBHOOK_URL"
```

### SSL Setup

**Important Prerequisites:**
- A clean VPS with no existing web server configurations
- No other services running on ports 80 or 443
- A domain name pointing to your VPS's IP address
- Root or sudo access to the VPS

```bash
# Setup SSL for a database
clidb ssl mydb example.com --email admin@example.com
```

The SSL setup process will:
1. Install and configure Nginx
2. Install Certbot
3. Obtain SSL certificates
4. Configure your database to use SSL

**Note:** Due to potential conflicts with existing web servers or configurations, it's highly recommended to perform SSL setup on a clean VPS installation.

## Configuration

Environment variables:
- `CLIDB_DISCORD_WEBHOOK`: Discord webhook URL
- `CLIDB_HOST_IP`: Override auto-detected IP address
- `CLIDB_DEFAULT_DB`: Default database type (defaults to "postgres")
- `CLIDB_DEFAULT_PORT`: Default port for the database

## Security

### Credential Storage
- Database credentials are stored in `~/.config/clidb/credentials.json`
- The directory has 700 permissions (only owner can access)
- The credentials file has 600 permissions (only owner can read/write)
- Credentials are stored locally on your VPS

### Best Practices
For secure operation, ensure your VPS follows these security practices:
- Use SSH key-based authentication (disable password authentication)
- Disable root SSH login
- Keep your system and packages updated
- Use strong passwords for all services
- Configure your firewall properly
- Regularly monitor system logs

### Credential Management
- Use `clidb info` to safely view stored credentials
- Use `--reset-password` to change database passwords
- Credentials are automatically removed when using `clidb remove`
- Never share or backup the credentials file in unsecured locations

## License

MIT License 