# Croissant2Ban

A lightweight intrusion prevention system (IPS) that monitors log files for authentication failures and automatically blocks malicious IP addresses using iptables. Inspired by Fail2Ban, Croissant2Ban provides real-time protection against brute-force attacks and unauthorized access attempts.

## Features

- Real-time log monitoring with regex pattern matching
- Automatic IP blocking using iptables
- Configurable ban thresholds and durations per service
- IP whitelist support
- SQLite database for alert tracking
- Command-line client for managing bans and monitoring services
- Automatic unban after configurable timeout periods

## Components

### croissant2ban

The main daemon that monitors log files and enforces bans.

**Key Features:**
- Monitors multiple log files simultaneously
- Configurable regex patterns for detecting authentication failures
- Automatic IP banning after threshold is reached (default: 5 attempts)
- Automatic unbanning after service-specific timeout periods
- Whitelist support to prevent blocking trusted IPs
- Logs all bans to `logs/bans.log`
- Stores alerts in SQLite database for tracking

**Requirements:**
- Must be run as root (requires iptables modification privileges)
- Python 3.x
- Dependencies: scapy, textual (see requirements.txt)

**Usage:**
```bash
sudo ./croissant2ban [options]
```

**Options:**
- `-o, --output <file>`: Specify custom log file location
- `--cli`: Enable CLI mode

**Configuration:**
Edit `conf/croissant.json` to configure:
- Services to monitor (SSH, HTTP, etc.)
- Log file paths
- Regex patterns for detecting failures
- Port numbers
- Ban duration (in seconds)
- Whitelist IPs

### c2b-client

A command-line client for interacting with Croissant2Ban and managing IP bans.

**Features:**
- List configured services and their status
- View currently banned IPs
- Manually unban specific IPs
- Query iptables rules

**Usage:**
```bash
./c2b-client <command>
```

**Commands:**
- `services`: List all configured services and their status
- `banned`: Display all currently blocked IP addresses
- `unban <IP>`: Manually remove an IP from the blocklist
- `help`: Show command usage information

**Examples:**
```bash
# View all configured services
./c2b-client services

# List banned IPs
./c2b-client banned

# Manually unban an IP
./c2b-client unban 192.168.1.100
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/deadpanda-c/croissant2ban.git
cd croissant2ban
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure services in `conf/croissant.json`

4. Make binaries executable:
```bash
chmod +x croissant2ban c2b-client
```

## Configuration

The main configuration file is `conf/croissant.json`:

```json
{
    "whitelist": [
        "127.0.0.1",
        "192.168.7.100"
    ],
    "services": {
        "sshd": {
            "name": "sshd",
            "logpath": "/var/log/auth.log",
            "port": 22,
            "enabled": true,
            "bantime": 600,
            "regex": "Connection closed by authenticating user .* ([0-9.]+) port .* \\[preauth\\]"
        }
    }
}
```

**Configuration Parameters:**
- `whitelist`: Array of IP addresses that will never be banned
- `services`: Object containing service configurations
  - `name`: Service identifier
  - `logpath`: Path to the log file to monitor
  - `port`: Service port number
  - `enabled`: Whether monitoring is active for this service
  - `bantime`: Duration in seconds before automatic unban
  - `regex`: Regular expression pattern to match authentication failures (must capture IP in group 1)

## Database

Croissant2Ban uses SQLite to store alert information in `db/croissant2ban.db`.

The database tracks:
- Timestamp of alert
- Source IP address
- Alert type
- Additional details

## Log Files

- `logs/croissant2ban.log`: Main application log
- `logs/bans.log`: Record of all banned IPs with timestamps

## Requirements

- Python 3.x
- Root/sudo privileges (for iptables modifications)
- iptables
- Python packages:
  - scapy==2.7.0
  - textual==7.3.0

## License

See LICENSE file for details.

## Security Considerations

- Always test configuration in a safe environment before production use
- Ensure whitelist includes your management IPs to prevent lockout
- Monitor logs regularly for false positives
- Keep ban thresholds reasonable to avoid blocking legitimate users
- Regularly review and clean up iptables rules

## How It Works

1. The `croissant2ban` daemon starts and reads the configuration file
2. It opens and tails all enabled log files
3. Each new log line is matched against the configured regex pattern
4. When a match is found, the source IP counter is incremented
5. If the counter reaches the threshold (default: 5), the IP is banned using iptables
6. The ban is recorded in the database and log file
7. After the configured bantime expires, the IP is automatically unbanned
8. Whitelisted IPs are never banned and are automatically unbanned if found