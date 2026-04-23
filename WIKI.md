# 🥐 Croissant2Ban — Wiki

> An intrusion prevention system that monitors service logs in real time, counts authentication failures, and automatically blocks offending IPs via `iptables`.

---

## Table of Contents

1. [How it works](#1-how-it-works)
2. [Requirements](#2-requirements)
3. [Installation](#3-installation)
4. [Configuration](#4-configuration)
   - [Whitelist](#41-whitelist)
   - [Services](#42-services)
   - [Built-in service profiles](#43-built-in-service-profiles)
5. [Running the daemon](#5-running-the-daemon)
   - [CLI flags](#51-cli-flags)
   - [Run as a systemd service](#52-run-as-a-systemd-service)
6. [Client tool (c2b-client)](#6-client-tool-c2b-client)
7. [Log files](#7-log-files)
8. [Writing custom regex patterns](#8-writing-custom-regex-patterns)
9. [Troubleshooting](#9-troubleshooting)
10. [Security considerations](#10-security-considerations)

---

## 1. How it works

```
 Service log file        croissant2ban daemon            iptables (kernel)
 ─────────────────       ──────────────────────          ─────────────────
 /var/log/auth.log  ───► tail lines in real time
                         extract IP via regex
                         increment counter[IP]
                         counter >= BAN_THRESHOLD  ────► iptables -I INPUT 1
                                                          -s <IP> -j DROP
                         elapsed >= bantime        ────► iptables -D INPUT
                                                          -s <IP> -j DROP
```

1. The daemon opens every **enabled** log file and seeks to the end (it ignores history, only new lines matter).
2. Each new line is matched against the service's `regex`. If the pattern matches, the captured IP's failure counter is incremented.
3. When the counter reaches `BAN_THRESHOLD` (default: 5), the IP is inserted at the top of the `INPUT` chain with a `DROP` target.
4. After `bantime` seconds the rule is automatically removed.
5. IPs in the **whitelist** are never banned and are unbanned immediately if somehow caught.
6. Every 30 seconds the daemon syncs its internal state against live iptables rules, so manual unbans from the client are picked up automatically.

---

## 2. Requirements

| Requirement  | Minimum version    | Notes                               |
| ------------ | ------------------ | ----------------------------------- |
| Python       | 3.8 +              | Uses f-strings and `subprocess.run` |
| iptables     | any                | Must be installed and in `$PATH`    |
| Linux kernel | any with netfilter | Tested on Debian/Ubuntu             |
| Run as       | **root**           | Required to modify iptables rules   |

Python standard library only — no third-party packages needed apart from your own `db.py` module.

---

## 3. Installation

```bash
# 1. Clone or copy the project
git clone https://github.com/yourname/croissant2ban.git
cd croissant2ban

# 2. Create the required directories
mkdir -p conf db logs

# 3. Put your config in place
cp examples/croissant.json conf/croissant.json

# 4. Make the client executable
chmod +x c2b-client.py

# 5. Run (must be root)
sudo python3 croissant2ban.py
```

**Project layout:**

```
croissant2ban/
├── croissant2ban.py      # Main daemon
├── c2b-client.py         # Management client
├── db.py                 # Database helper (provide your own)
├── conf/
│   └── croissant.json    # Main configuration file
├── db/
│   └── croissant2ban.db  # SQLite database (auto-created)
└── logs/
    ├── croissant2ban.log  # Daemon log
    └── bans.log           # Ban history
```

---

## 4. Configuration

All configuration lives in `conf/croissant.json`. The file has two top-level keys: `whitelist` and `services`.

```json
{
    "whitelist": [ "127.0.0.1" ],
    "services": {
        "sshd": { ... }
    }
}
```

### 4.1 Whitelist

A JSON array of IPv4 addresses that must **never** be banned. Any IP in this list is immune to banning and is immediately unbanned if it somehow enters the ban list (e.g. from a previous run).

```json
"whitelist": [
    "127.0.0.1",
    "192.168.1.1",
    "10.0.0.5"
]
```

> ⚠️ Always add your own machine's LAN IP and your management/admin IPs here. Locking yourself out requires physical or console access to flush iptables manually.

### 4.2 Services

Each key under `"services"` is a service profile. All fields are required unless marked optional.

```json
"sshd": {
    "name":     "sshd",
    "logpath":  "/var/log/auth.log",
    "port":     22,
    "enabled":  true,
    "bantime":  600,
    "regex":    "(?:Failed password|Invalid user) \\S+(?: from)? ([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+)"
}
```

| Field     | Type    | Description                                                       |
| --------- | ------- | ----------------------------------------------------------------- |
| `name`    | string  | Display name — must match the key                                 |
| `logpath` | string  | Absolute path to the log file to monitor                          |
| `port`    | integer | Port number associated with the service (used for bantime lookup) |
| `enabled` | boolean | Set to `false` to skip this service without deleting its config   |
| `bantime` | integer | Seconds before the IP is automatically unbanned                   |
| `regex`   | string  | Regular expression to extract the offending IP — see §8           |

### 4.3 Built-in service profiles

The following profiles are included in the example config, ready to enable:

| Key         | Service         | Port | Log file                    |
| ----------- | --------------- | ---- | --------------------------- |
| `sshd`      | OpenSSH         | 22   | `/var/log/auth.log`         |
| `nginx`     | Nginx HTTP      | 80   | `/var/log/nginx/access.log` |
| `nginx-ssl` | Nginx HTTPS     | 443  | `/var/log/nginx/access.log` |
| `vsftpd`    | FTP             | 21   | `/var/log/vsftpd.log`       |
| `postfix`   | SMTP            | 25   | `/var/log/mail.log`         |
| `dovecot`   | IMAP            | 143  | `/var/log/mail.log`         |
| `mysql`     | MySQL / MariaDB | 3306 | `/var/log/mysql/error.log`  |

All services except `sshd` and `nginx`/`nginx-ssl` are shipped with `"enabled": false`. Enable only the ones running on your machine.

---

## 5. Running the daemon

```bash
sudo python3 croissant2ban.py
```

The daemon runs in the foreground and logs to both `logs/croissant2ban.log` and `stderr`.

To stop it cleanly, press `Ctrl+C`. It will flush all active bans before exiting.

```
^C
2024-01-01 12:00:00 - INFO: Cleaning up active bans...
2024-01-01 12:00:00 - WARNING: UNBANNED: 203.0.113.42
2024-01-01 12:00:00 - INFO: Done.
```

### 5.1 CLI flags

| Flag              | Argument     | Description                                                     |
| ----------------- | ------------ | --------------------------------------------------------------- |
| `-o` / `--output` | `<filepath>` | Override the default log output path (`logs/croissant2ban.log`) |

```bash
sudo python3 croissant2ban.py -o /var/log/c2b.log
```

### 5.2 Run as a systemd service

To have croissant2ban start automatically at boot, create a unit file:

```bash
sudo nano /etc/systemd/system/croissant2ban.service
```

```ini
[Unit]
Description=Croissant2Ban Intrusion Prevention System
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/croissant2ban/croissant2ban.py
WorkingDirectory=/opt/croissant2ban
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

```bash
# Reload systemd, enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable croissant2ban
sudo systemctl start croissant2ban

# Check status
sudo systemctl status croissant2ban
```

---

## 6. Client tool (c2b-client)

`c2b-client.py` is a standalone management utility. It does **not** need to run as root for read operations, but unbanning requires sudo privileges.

### Commands

#### `services` — list monitored services

```bash
./c2b-client.py services
```

```
SERVICE    | PORT   | STATUS   | LOGPATH
------------------------------------------------------------
sshd       | 22     | ENABLED  | /var/log/auth.log
nginx      | 80     | ENABLED  | /var/log/nginx/access.log
nginx-ssl  | 443    | ENABLED  | /var/log/nginx/access.log
vsftpd     | 21     | DISABLED | /var/log/vsftpd.log
postfix    | 25     | DISABLED | /var/log/mail.log
```

#### `banned` — list currently blocked IPs

```bash
./c2b-client.py banned
```

```
IP ADDRESS         | REASON
----------------------------------------
203.0.113.42       | Croissant2Ban
198.51.100.7       | Croissant2Ban
```

#### `unban <IP>` — manually remove a ban

```bash
./c2b-client.py unban 203.0.113.42
```

```
[OK] 203.0.113.42 has been removed from the blocklist.
Note: if croissant2ban is running, it will sync this change within ~30 seconds.
```

The daemon will detect the manual unban during its next iptables sync (within 30 seconds) and remove the IP from its internal state so new failures are counted normally.

#### `help` — show the help menu

```bash
./c2b-client.py help
```

---

## 7. Log files

### `logs/croissant2ban.log` — daemon activity

Every significant event is recorded here.

```
2024-01-01 12:00:00 - INFO:    Croissant2Ban (Log Parser) started.
2024-01-01 12:00:00 - INFO:    Monitoring log: /var/log/auth.log for sshd
2024-01-01 12:00:05 - INFO:    Auth failure from 203.0.113.42 (1/5)
2024-01-01 12:00:06 - INFO:    Auth failure from 203.0.113.42 (2/5)
2024-01-01 12:00:07 - INFO:    Auth failure from 203.0.113.42 (3/5)
2024-01-01 12:00:08 - INFO:    Auth failure from 203.0.113.42 (4/5)
2024-01-01 12:00:09 - INFO:    Auth failure from 203.0.113.42 (5/5)
2024-01-01 12:00:09 - WARNING: BLOCKING: 203.0.113.42 (Threshold reached)
2024-01-01 12:10:09 - WARNING: UNBANNED: 203.0.113.42
```

### `logs/bans.log` — ban history

A simple append-only record of every ban event, useful for auditing.

```
Mon Jan  1 12:00:09 2024 - 203.0.113.42 banned
Mon Jan  1 12:15:31 2024 - 198.51.100.7 banned
```

---

## 8. Writing custom regex patterns

The regex in each service profile must capture the offending **IPv4 address as capture group 1** — that is the value `re.search(...).group(1)` returns.

### Rules

- Use a standard Python regex string (JSON-escaped: `\\.` for `\.`, `\\d` for `\d`, etc.)
- The IP must be in the **first** capturing group `(...)`
- Non-capturing groups `(?:...)` can be used freely elsewhere
- The pattern is matched with `re.search()`, so it does not need to anchor to the start of the line

### Template

```
([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)
```

In JSON this becomes:

```json
"regex": "([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+)"
```

### Examples

**Match `Failed password` or `Invalid user` in SSH logs:**

```
auth.log line:  Jan  1 12:00:00 server sshd[1234]: Failed password for root from 203.0.113.42 port 54321 ssh2
regex:          (?:Failed password|Invalid user) \S+(?: from)? ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)
captured:       203.0.113.42
```

**Match 4xx errors in Nginx access logs:**

```
access.log line:  203.0.113.42 - - [01/Jan/2024:12:00:00 +0000] "GET /admin HTTP/1.1" 403 150
regex:            ^([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+) .* " (?:400|401|403|404|405|429)
captured:         203.0.113.42
```

**Match FTP login failures:**

```
vsftpd.log line:  Mon Jan  1 12:00:00 2024 [pid 5678] FAIL LOGIN: Client "203.0.113.42"
regex:            FAIL LOGIN: Client "([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)"
captured:         203.0.113.42
```

### Testing your regex before deploying

Use Python directly to validate:

```python
import re

line   = 'Jan  1 12:00:00 sshd[1234]: Failed password for root from 203.0.113.42 port 54321 ssh2'
regex  = r'(?:Failed password|Invalid user) \S+(?: from)? ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)'

match = re.search(regex, line)
if match:
    print("Captured IP:", match.group(1))   # → 203.0.113.42
else:
    print("No match — check your pattern")
```

---

## 9. Troubleshooting

### The daemon exits immediately with "No valid log files found"

- Check that the `logpath` values in `croissant.json` actually exist on disk.
- Check that the service is set to `"enabled": true`.
- Verify file permissions — the process runs as root so this is rarely an issue, but some log files (e.g. MySQL) may be owned by a dedicated user with restricted permissions.

```bash
ls -la /var/log/auth.log
ls -la /var/log/nginx/access.log
```

### IPs are not being banned

1. Confirm the daemon is running: `ps aux | grep croissant2ban`
2. Check `logs/croissant2ban.log` — are "Auth failure" lines appearing?
3. If not, your regex may not match. Test it manually as shown in §8.
4. If failures appear but no ban happens, confirm `BAN_THRESHOLD` (default 5) is being reached.

### An IP was banned but traffic is still getting through

The ban is applied to the `INPUT` chain via `iptables`. Check that no other rule higher in the chain is allowing the traffic first:

```bash
sudo iptables -L INPUT -n -v --line-numbers
```

Croissant2Ban inserts its rules at position 1 (`-I INPUT 1`), so they should always be at the top.

### I locked myself out

If you accidentally banned your own IP, you need direct/console access to the machine and run:

```bash
sudo iptables -D INPUT -s <YOUR_IP> -j DROP
```

Or flush all DROP rules at once (use with caution on production systems):

```bash
sudo iptables -F INPUT
```

> **Prevention:** Always add your admin IP(s) to the `whitelist` in `croissant.json` before starting the daemon.

### The client `unban` command says "Bad rule"

The IP is not currently in iptables — it may have already expired and been removed automatically by the daemon, or was never banned. This is a safe warning, not an error.

---

## 10. Security considerations

**Run with least privilege where possible.** The daemon requires root only to call `iptables`. If your distribution supports it, consider using `capabilities` to grant only `CAP_NET_ADMIN` instead of full root:

```bash
sudo setcap cap_net_admin+eip /usr/bin/python3
```

**Protect the config file.** The config contains log paths and regex patterns. Restrict write access so an unprivileged attacker cannot redirect log paths or neutralize patterns:

```bash
sudo chown root:root conf/croissant.json
sudo chmod 640 conf/croissant.json
```

**Review bans.log regularly.** Repeated bans from the same subnet may indicate a distributed attack that warrants a broader network-level block upstream.

**Use `bantime` wisely.** A very long `bantime` (e.g. 86400 for 24 hours) reduces re-attack risk but increases the blast radius if a legitimate IP is incorrectly banned. For most services, 600–3600 seconds is a reasonable balance.

**This tool does not protect against IPv6.** All patterns and iptables commands target IPv4 only. If your services are exposed over IPv6, additional configuration using `ip6tables` is required.
