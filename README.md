# 🐬 Check MySQL

[![PyPI version](https://img.shields.io/pypi/v/check-mysql.svg)](https://pypi.org/project/check-mysql/)
[![Python versions](https://img.shields.io/pypi/pyversions/check-mysql.svg)](https://pypi.org/project/check-mysql/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build](https://github.com/lduchosal/check_mysql/actions/workflows/python-package.yml/badge.svg)](https://github.com/lduchosal/check_mysql/actions/workflows/python-package.yml)
[![Publish](https://github.com/lduchosal/check_mysql/actions/workflows/publish.yml/badge.svg)](https://github.com/lduchosal/check_mysql/actions/workflows/publish.yml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_check_mysql&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=lduchosal_check_mysql)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_check_mysql&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=lduchosal_check_mysql)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_check_mysql&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=lduchosal_check_mysql)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_check_mysql&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=lduchosal_check_mysql)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_check_mysql&metric=bugs)](https://sonarcloud.io/summary/new_code?id=lduchosal_check_mysql)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_check_mysql&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=lduchosal_check_mysql)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_check_mysql&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=lduchosal_check_mysql)
[![Technical Debt](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_check_mysql&metric=sqale_index)](https://sonarcloud.io/summary/new_code?id=lduchosal_check_mysql)

A comprehensive **Nagios plugin** for monitoring MySQL and MariaDB servers, either **directly** (PyMySQL) or **through an SSH tunnel** (sshtunnel/paramiko). Built with modern Python practices and designed for enterprise monitoring environments.

## ✨ Features

- 🔌 **Dual Connectivity** - Direct TCP connection or SSH tunnel through a bastion host
- 🎯 **Multiple Checks** - Connectivity ping (client/server versions), uptime, connection usage, replication health, slow queries, query latency, plus the cache-hitrate and load checks backported from [check_mysql_health](https://github.com/lausser/check_mysql_health)
- 📊 **Nagios Compatible** - Standard exit codes, performance data and range-based thresholds
- 🏗️ **Clean Architecture** - Modular design with testable components
- 🔧 **Flexible Configuration** - File-based configuration with CLI overrides (`-H`, `-P`)
- 📈 **Verbose Logging** - Multi-level debugging support (`-v`, `-vv`, `-vvv`)
- 🐍 **Modern Python** - Python 3.10+ with strict typing throughout

## 🚀 Quick Start

### Installation

```bash
# Create virtual environment (recommended)
python -m venv /usr/local/libexec/nagios/check_mysql
source /usr/local/libexec/nagios/check_mysql/bin/activate

# Install from PyPI
pip install check-mysql

# Or install from source
pip install git+https://github.com/lduchosal/check_mysql.git
```

### Basic Usage

```bash
# Guided setup: prompts for the connection (SSH tunnel supported), writes
# check_mysql.ini, shows the CREATE USER SQL, optionally creates the
# monitoring user on the server and tests the connection.
check_mysql init

# Non-interactive: just write the default template
check_mysql init --yes

# Check connectivity and report the client and server versions
check_mysql ping

# Check server uptime (alert on recent restart)
check_mysql uptime

# Check connection usage (percent of max_connections)
check_mysql connections -W 80 -C 95

# Check replication lag and thread state
check_mysql replication -W 60 -C 300

# Check the slow queries counter
check_mysql slowqueries -W 100 -C 1000

# Check SELECT 1 round-trip latency
check_mysql latency -W 100 -C 500

# Point at another server without editing the config
check_mysql uptime -H db2.example.com -P 3307
```

## 📋 Available Commands

| Command | Description | Value | Default Thresholds |
|---------|-------------|-------|--------------------|
| `init` | Guided setup: config, monitoring user (SQL shown or created for you), connection test — `--yes` for non-interactive, `--force` to overwrite | - | - |
| `ping` | Connectivity check reporting the client (PyMySQL) and server versions; CRITICAL when the server is unreachable | milliseconds | - |
| `uptime` | Seconds since server start | seconds | W:`3600:`, C:`300:` |
| `connections` | Threads_connected vs max_connections | percent | W:`80`, C:`95` |
| `replication` | Replication lag, thread state | seconds behind | W:`60`, C:`300` |
| `slowqueries` | Slow_queries counter since start | count | W:`100`, C:`1000` |
| `latency` | SELECT 1 round-trip time | milliseconds | W:`100`, C:`500` |
| `threadcache` | Thread cache hitrate (Threads_created vs Connections) | percent | W:`90:`, C:`80:` |
| `querycache` | Query cache hitrate — MariaDB only, UNKNOWN on MySQL 8+ | percent | W:`90:`, C:`80:` |
| `querycacheprunes` | Qcache_lowmem_prunes per second — MariaDB only | rate/s | W:`1`, C:`10` |
| `keycache` | MyISAM key cache hitrate | percent | W:`99:`, C:`95:` |
| `tablecache` | Table cache hitrate (Open_tables vs Opened_tables) | percent | W:`99:`, C:`95:` |
| `bufferpool` | InnoDB buffer pool hitrate | percent | W:`99:`, C:`95:` |
| `bufferpoolwaits` | Innodb_buffer_pool_wait_free per second | rate/s | W:`1`, C:`10` |
| `logwaits` | Innodb_log_waits per second | rate/s | W:`1`, C:`10` |
| `tablelocks` | Table lock contention (waited vs immediate) | percent | W:`1`, C:`2` |
| `indexusage` | Index usage vs full scans (Handler_read_*) | percent | W:`90:`, C:`80:` |
| `tmpdisktables` | Share of temporary tables created on disk | percent | W:`25`, C:`50` |
| `openfiles` | Open_files vs open_files_limit | percent | W:`80`, C:`95` |
| `longrunning` | Queries running longer than 60s (needs `PROCESS`) | count | W:`10`, C:`20` |
| `security` | Over-privileged or insecure accounts: anonymous, passwordless, wildcard `%` host, remote root, dangerous privileges reachable remotely (needs `SELECT` on `mysql.user`) | count | W:`0`, C:`5` |
| `sql` | Scalar result of an arbitrary statement (`--sql "SELECT ..."`) | scalar | - |

Thresholds are standard **Nagios ranges**: `95` alerts above 95, `300:` alerts below 300, `10:20` alerts outside the interval.

### check_mysql_health Heritage

The `threadcache` … `sql` block is backported from lausser's
[check_mysql_health](https://github.com/lausser/check_mysql_health) with the same
default thresholds. One deliberate difference: the original computes rates as
deltas between two runs persisted in a state file; check_mysql reports
**averages since server start** instead, which needs no local state. The query
cache checks (`querycache`, `querycacheprunes`) apply to MariaDB only — the
query cache was removed in MySQL 8.0 and those commands exit UNKNOWN there.

### Replication Semantics

- **OK/WARNING/CRITICAL** on `Seconds_Behind_Source` against the thresholds
- **CRITICAL immediately** when the IO or SQL thread is stopped (the last replication error is included in the output)
- **CRITICAL immediately** when the lag is NULL while threads run
- **UNKNOWN** when the server is not a replica
- Both modern (`Replica_*`/`Source_*`) and legacy (`Slave_*`/`Master_*`) column names are supported

### Security Audit Semantics

The `security` command reads `mysql.user` (one `SELECT`, no other table) and flags accounts matching any of these criteria, aligned with the [CIS Oracle MySQL Benchmark](https://www.cisecurity.org/benchmark/oracle_mysql) and `mysql_secure_installation`:

| Check | Condition on the `mysql.user` row | Reported as | Reference |
|-------|-----------------------------------|-------------|-----------|
| Anonymous account | `User` is empty | `anonymous account` | CIS 4.11 |
| Missing password | `Password` **and** `authentication_string` both empty, on a password-based plugin | `no password` | CIS 4.10 |
| Wildcard host | `Host` is `%` or empty (reachable from any address) | `wildcard host` | CIS 4.9 |
| Remote root | `User` is `root` with a host other than `localhost`/`127.0.0.1`/`::1` | `root reachable remotely` | `mysql_secure_installation` |
| Remote dangerous privileges | Non-local host holding `SUPER`, `GRANT OPTION`, `FILE`, `PROCESS` or `SHUTDOWN` — or every `*_priv` column, reported as `ALL PRIVILEGES` | `remote privileges (…)` | CIS 5.2–5.8 |

The value is the number of flagged **accounts** (an account with several findings counts once); the long output lists one `'user'@'host'` line per account and the headline breaks the count down by category. Defaults: WARNING above `0`, CRITICAL above `5`.

**What is deliberately not flagged:**

- **Locked accounts** (`account_locked = Y`) and the `mysql_no_login` plugin — they refuse every connection, no attack surface. They are excluded from the audited count.
- **Socket/external authentication** (`unix_socket`, `auth_socket`, PAM, LDAP, GSSAPI, Kerberos, Windows) — an empty credential column is normal there, not a missing password.
- **Powerful local accounts** — `root@localhost` or `debian-sys-maint@localhost` are expected on every install; privileges are only flagged on remotely reachable accounts.
- **The monitoring user's `%` host** — the `[mysql]` account must be remotely reachable to do its job; it stays subject to every other check (no password, dangerous privileges).
- **Accounts listed in `[security] allow`** — exempted from every check (see the Configuration section below).
- **Scoped host patterns** (`10.0.%`, `%.example.com`) — only the pure `%` wildcard is flagged.

**Known limits** (candidates for later versions): weak-but-not-empty passwords (offline wordlist testing à la [MySQLTuner](https://github.com/major/MySQLTuner-perl) only works for unsalted `mysql_native_password` hashes; `caching_sha2_password` is salted by design), legacy authentication plugins (`mysql_native_password`, pre-4.1 hashes — CIS 4.7), absent `validate_password` policy, presence of the `test` database, non-admin grants on the `mysql` schema (CIS 5.1), password expiry, and per-account TLS requirements.

## ⚙️ Configuration

Run `check_mysql init` for a guided setup: it prompts for the connection settings (password generated by default, SSH tunnel supported), writes `check_mysql.ini` with mode 600, prints the `CREATE USER` SQL, and can create the monitoring user on the server (with admin credentials, through the tunnel if configured) then test the connection. Or create the file by hand next to the plugin, in the working directory, or in `/usr/local/etc/nagios` / `/etc/nagios`:

### Direct Connection

```ini
[mysql]
host = db.example.com
port = 3306
user = nagios
password = secret
timeout = 10
```

### Connection Through an SSH Tunnel

```ini
[mysql]
# Host/port as seen FROM THE BASTION
host = 10.0.0.12
port = 3306
user = nagios
password = secret
timeout = 10

[ssh]
host = bastion.example.com
port = 22
user = nagios
private_key = ~/.ssh/id_ed25519
# or: password = only-if-no-key
```

When the `[ssh]` section is present, the plugin opens the tunnel first and connects to MySQL through it; remove the section to connect directly.

### MySQL Monitoring User

```sql
CREATE USER 'nagios'@'%' IDENTIFIED BY 'secret';
GRANT USAGE, REPLICATION CLIENT ON *.* TO 'nagios'@'%';
GRANT SELECT ON mysql.user TO 'nagios'@'%';
```

This is exactly what `check_mysql init` creates (or prints) for you.

`REPLICATION CLIENT` (or `REPLICATION_SLAVE_ADMIN` on MySQL 8+) is only needed for the `replication` command, and `SELECT` on `mysql.user` only for the `security` command. Add `GRANT PROCESS ON *.*` for the `longrunning` command (to see other users' queries), and the relevant `SELECT` grants for whatever the `sql` command queries.

Accounts the `security` audit must not flag (the full criteria and built-in exemptions are described under **Security Audit Semantics** above) are listed as `user@host` entries in the optional `[security]` section:

```ini
[security]
allow = backup@10.0.0.5, debian-sys-maint@localhost, app@%
```

## 🔧 Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `-c, --config` | Configuration file path | `-c /custom/path/config.ini` |
| `-H, --hostname` | MySQL host (overrides `[mysql]`) | `-H db2.example.com` |
| `-P, --port` | MySQL port (overrides `[mysql]`) | `-P 3307` |
| `-W, --warning` | Warning threshold (Nagios range) | `-W 80` |
| `-C, --critical` | Critical threshold (Nagios range) | `-C 95` |
| `-v, --verbose` | Verbosity level | `-v`, `-vv`, `-vvv` |
| `--version` | Show version | `--version` |

## 🏢 Nagios Integration

### Command Definitions

```cfg
# MySQL Commands
define command {
    command_name    check_mysql_ping
    command_line    $USER1$/check_mysql/bin/check_mysql ping -H $HOSTADDRESS$
}

define command {
    command_name    check_mysql_uptime
    command_line    $USER1$/check_mysql/bin/check_mysql uptime -H $HOSTADDRESS$
}

define command {
    command_name    check_mysql_connections
    command_line    $USER1$/check_mysql/bin/check_mysql connections -H $HOSTADDRESS$ -W 80 -C 95
}

define command {
    command_name    check_mysql_replication
    command_line    $USER1$/check_mysql/bin/check_mysql replication -H $HOSTADDRESS$ -W 60 -C 300
}

define command {
    command_name    check_mysql_slowqueries
    command_line    $USER1$/check_mysql/bin/check_mysql slowqueries -H $HOSTADDRESS$ -W 100 -C 1000
}

define command {
    command_name    check_mysql_latency
    command_line    $USER1$/check_mysql/bin/check_mysql latency -H $HOSTADDRESS$ -W 100 -C 500
}
```

### Service Definitions

```cfg
# MySQL Services
define service {
    use                     generic-service
    service_description     MYSQL_PING
    check_command           check_mysql_ping
    hostgroup_name          mysql
}

define service {
    use                     generic-service
    service_description     MYSQL_UPTIME
    check_command           check_mysql_uptime
    hostgroup_name          mysql
}

define service {
    use                     generic-service
    service_description     MYSQL_CONNECTIONS
    check_command           check_mysql_connections
    hostgroup_name          mysql
}

define service {
    use                     generic-service
    service_description     MYSQL_REPLICATION
    check_command           check_mysql_replication
    hostgroup_name          mysql-replicas
}

define service {
    use                     generic-service
    service_description     MYSQL_SLOWQUERIES
    check_command           check_mysql_slowqueries
    hostgroup_name          mysql
}

define service {
    use                     generic-service
    service_description     MYSQL_LATENCY
    check_command           check_mysql_latency
    hostgroup_name          mysql
}
```

## 🏗️ Architecture

This plugin follows **clean architecture** principles with clear separation of concerns:

```
check_mysql/
├── 📁 cli/                     # Command-line interface
│   ├── commands/               # Individual command handlers
│   │   ├── ping.py            # Ping command (versions)
│   │   ├── uptime.py          # Uptime command
│   │   ├── connections.py     # Connections command
│   │   ├── replication.py     # Replication command
│   │   ├── slowqueries.py     # Slow queries command
│   │   └── latency.py         # Latency command
│   ├── decorators.py          # Common CLI decorators
│   └── handlers.py            # Shared command execution path
├── 📁 core/                    # Core business logic
│   ├── config.py              # Configuration handling
│   ├── connection.py          # Direct / SSH tunnel connector
│   ├── mysql_client.py        # MySQL query client
│   ├── exceptions.py          # Custom exceptions
│   ├── models.py              # Dataclasses, TypedDicts, Protocols
│   ├── nagios.py              # Nagios plugin framework
│   └── logging_config.py      # Logging configuration
├── 📁 services/                # Business services
│   ├── ping_service.py        # Ping business logic
│   ├── uptime_service.py      # Uptime business logic
│   ├── connections_service.py # Connections business logic
│   ├── replication_service.py # Replication business logic
│   ├── slowqueries_service.py # Slow queries business logic
│   └── latency_service.py     # Latency business logic
└── 📁 tests/                   # Comprehensive test suite
    ├── unit/                   # Unit tests
    ├── integration/            # CLI integration tests
    ├── e2e/                    # End-to-end tests (real local MySQL server)
    └── fixtures/               # Test fixtures (mock client, datasets)
```

### Key Design Principles

- **🎯 Single Responsibility** - Each module has one clear purpose
- **🔌 Dependency Injection** - Services depend on a client Protocol, trivially mockable
- **🧪 Testable** - The default test suite runs without any MySQL server; the e2e suite drives the real binary against a local one
- **📈 Extensible** - Adding a check = one service + one command file
- **🔒 Secure** - No secrets in code, key-based SSH authentication

## 🧪 Development

### Development Setup

```bash
# Clone repository
git clone https://github.com/lduchosal/check_mysql.git
cd check_mysql

# Install with PDM (creates .venv)
pdm install
pdm install -G dev
```

### Code Quality Tools

```bash
# The full quality pipeline (format, lint, types, docstrings, tests, gate)
pdm run check

# Individual steps
pdm run lint          # ruff
pdm run typecheck     # pyright (strict)
pdm run test          # pytest + coverage (no MySQL server needed)
pdm run test-e2e      # end-to-end against the local server (check_mysql.ini)
pdm run metrics       # local quality metrics snapshot
```

See [doc/code-quality.md](doc/code-quality.md) for the full quality standard (blocking gate + best-ever ratchet).

### Building & Publishing

```bash
# Quality checks only
sh publish.sh --quality

# Full pipeline: quality, SonarCloud gate, bump, build, publish, tag
sh publish.sh --patch
```

## 🔍 Output Examples

### Successful Check

```
MYSQL OK - Server up for 10 days, 0:00:00 (864000 seconds) | uptime=864000s;3600:;300:
```

### Ping (versions)

```
MYSQL OK - client PyMySQL 1.1.1, server 8.4.0 | ping=1.23ms
```

### Warning State

```
MYSQL WARNING - Connections: 130/151 (86.09% of max_connections) | connections=86.09%;80;95
```

### Critical State (replication stopped)

```
MYSQL CRITICAL - Replication threads stopped (IO: No, SQL: Yes): error connecting to source
```

### Unknown State

```
UNKNOWN: Configuration file not found: check_mysql.ini
```

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **Access denied** | Verify the monitoring user credentials and grants |
| **SSH tunnel failures** | Check bastion reachability, key permissions (600) and known_hosts |
| **Replication UNKNOWN** | The target is not a replica — point at the right server |
| **Configuration Issues** | Validate config file syntax and search paths |

### Debug Mode

```bash
# Maximum verbosity (SQL queries, tunnel lifecycle, method traces)
check_mysql replication -vvv

# Check a specific configuration
check_mysql uptime -c /path/to/config.ini -vv
```

## 📊 Exit Codes

| Code | Status | Description |
|------|--------|-------------|
| `0` | OK | Value within acceptable range |
| `1` | WARNING | Value exceeds warning threshold |
| `2` | CRITICAL | Value exceeds critical threshold, or replication stopped |
| `3` | UNKNOWN | Error occurred during execution |

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Guidelines

- Follow [PEP 8](https://pep8.org/) style guide
- Add tests for new features
- Update documentation as needed
- `pdm run check` must be green before submitting

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [nagiosplugin](https://nagiosplugin.readthedocs.io/) framework
- Uses [PyMySQL](https://pymysql.readthedocs.io/) for MySQL connectivity
- Uses [sshtunnel](https://sshtunnel.readthedocs.io/) for bastion traversal
- Powered by [Click](https://click.palletsprojects.com/) for CLI interface

---

<div align="center">

**[⭐ Star this repository](https://github.com/lduchosal/check_mysql)** if you find it useful!

[🐛 Report Bug](https://github.com/lduchosal/check_mysql/issues) • [💡 Request Feature](https://github.com/lduchosal/check_mysql/issues) • [📖 Documentation](https://github.com/lduchosal/check_mysql/blob/main/README.md)

</div>

## 💖 Sponsor

If this project helps you, consider supporting its development:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-%E2%9D%A4-pink?logo=github)](https://github.com/sponsors/lduchosal)
