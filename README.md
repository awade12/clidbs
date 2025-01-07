# CLIDB

> Tired of the database setup hassle? CLIDB is for developers who need instant databases for their projects. No more Docker compose files, no more configuration headaches - just one command and you're ready to code.

A powerful command-line tool for managing local development databases using Docker. Simplify your database management with features like automatic port allocation, backups, metrics monitoring, and more.

## Why CLIDB?

- 🚀 **Zero to Database in Seconds**
  ```bash
  clidb create myproject-db
  ```

- 😌 **No More Setup Headaches**
  - Forget about Docker compose files
  - No manual port configuration
  - Automatic credential management

- 💪 **Perfect for:**
  - Rapid prototyping
  - Multiple client projects
  - Testing and development
  - CI/CD environments

## Features

- 🗃️ **Multiple Database Support**
  - PostgreSQL (versions 11-16)
  - MySQL (8.0, 5.7)
  - MariaDB (11.0, 10.11, 10.10)
  - Redis (7.2, 7.0, 6.2)
  - MongoDB (7.0, 6.0, 5.0)
  - Neo4j (5, 4.4)

- 🔄 **Automatic Port Management**
  - Smart port allocation for multiple instances
  - Conflict resolution for occupied ports
  - Public and private access modes

- 🔒 **Security Features**
  - Automatic password generation
  - SSL/TLS support with Let's Encrypt
  - Secure credential storage

- 📊 **Monitoring & Metrics**
  - Real-time performance monitoring
  - CPU and memory usage
  - Network and disk I/O stats
  - Container health checks

- 💾 **Backup & Restore**
  - Full database backups
  - Point-in-time restoration
  - Backup management with descriptions
  - Automatic backup rotation

- 🔔 **Notifications**
  - Discord integration
  - Event notifications for:
    - Database creation/deletion
    - Start/stop events
    - Backup operations
    - Error alerts

## Prerequisites

- Python 3.8 or higher
- Docker (can be installed using `clidb install-docker`)
- pip (Python package installer)

## Installation

```bash
# Install using pip
pip install clidb

# Or install using pipx (recommended)
pipx install clidb
```

## Quick Start

```bash
# Install Docker if needed
clidb install-docker

# Create a PostgreSQL database
clidb create mydb --type postgres --version 16

# List all databases
clidb list

# View database info
clidb info mydb
```

## Usage Guide

### Database Management

```bash
# Create a database
clidb create mydb --type postgres --version 16

# Create with specific port and access
clidb create mydb --type mysql --port 3306 --access private

# List all databases
clidb list

# Get connection info
clidb info mydb

# Start/stop databases
clidb start mydb
clidb stop mydb

# Remove a database
clidb remove mydb
```

### Backup Operations

```bash
# Create a backup
clidb backup mydb --description "Pre-deployment backup"

# List all backups
clidb backups

# List backups for specific database
clidb backups --db mydb

# Restore from backup
clidb restore mydb 20240101_120000

# Delete old backup
clidb delete-backup mydb 20240101_120000
```

### Performance Monitoring

```bash
# View current metrics
clidb metrics mydb

# Watch metrics in real-time
clidb metrics mydb --watch
```

### SSL Configuration

```bash
# Setup SSL with automatic certificate
clidb ssl mydb example.com --email admin@example.com

# Remove SSL
clidb remove-ssl mydb example.com

# Verify domain configuration
clidb verify-domain example.com
```

### Discord Notifications

Enable notifications by providing a webhook URL:

```bash
# Via command line
clidb create mydb --discord-webhook "https://discord.com/api/webhooks/..."

# Or via environment variable
export CLIDB_DISCORD_WEBHOOK="https://discord.com/api/webhooks/..."
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLIDB_DISCORD_WEBHOOK` | Discord webhook URL for notifications | None |
| `CLIDB_HOST_IP` | Override auto-detected IP address | Auto-detected |
| `CLIDB_DEFAULT_DB` | Default database type | postgres |
| `CLIDB_DEFAULT_PORT` | Default starting port | Based on DB type |

## File Locations

- **Credentials**: `~/.config/clidb/credentials.json`
- **Backups**: `~/.config/clidb/backups/`
- **Backup Metadata**: `~/.config/clidb/backups/backup_metadata.json`

## Security Best Practices

1. **Access Control**
   - Use private access mode for development
   - Enable SSL for production environments
   - Regularly rotate database passwords

2. **Backup Management**
   - Regular backups with descriptive labels
   - Test restore procedures periodically
   - Keep backup metadata up to date

3. **SSL/TLS**
   - Use valid email for Let's Encrypt notifications
   - Keep certificates up to date
   - Verify domain ownership before SSL setup

## Troubleshooting

1. **Port Conflicts**
   - CLIDB automatically finds the next available port
   - Use `--port` to specify a different port
   - Check port availability with `netstat` or `lsof`

2. **Docker Issues**
   - Run `clidb install-docker` to fix common problems
   - Check Docker daemon status
   - Verify user is in docker group

3. **Backup/Restore**
   - Ensure sufficient disk space
   - Check database connection before backup
   - Verify backup file permissions

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- GitHub Issues: [Report a bug](https://github.com/awade12/clidbs/issues)
- Documentation: [Wiki](https://github.com/awade12/clidbs/wiki)
- Discussions: [Community](https://github.com/awade12/clidbs/discussions) 