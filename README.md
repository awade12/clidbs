# CLIDB

A command-line tool for managing local development databases using Docker.

## Features

- Create and manage PostgreSQL, MySQL, MongoDB, and Redis databases
- Automatic port allocation for multiple databases
- SSL/TLS support with automatic certificate generation
- Performance metrics monitoring
- Database backup and restore functionality
- Discord notifications for database events
- Docker installation helper

## Installation

```bash
pip install clidb
```

## Usage

### Creating a Database

```bash
clidb create mydb --type postgres --version 16
```

### Managing Databases

```bash
# List all databases
clidb list

# Get database info
clidb info mydb

# Start/stop databases
clidb start mydb
clidb stop mydb

# Remove a database
clidb remove mydb
```

### Monitoring

```bash
# View real-time metrics
clidb metrics mydb --watch
```

### Backup and Restore

```bash
# Create a backup
clidb backup mydb --description "Pre-deployment backup"

# List available backups
clidb backups --db mydb

# Restore from backup
clidb restore mydb 20240101_120000

# Delete a backup
clidb delete-backup mydb 20240101_120000
```

### SSL Configuration

```bash
clidb ssl mydb example.com --email admin@example.com
```

### Discord Notifications

You can enable Discord notifications for database events by providing a webhook URL:

```bash
clidb create mydb --discord-webhook https://discord.com/api/webhooks/...
```

Or set it via environment variable:

```bash
export CLIDB_DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
```

### Docker Installation

If Docker is not installed, you can use:

```bash
clidb install-docker
```

## License

MIT 