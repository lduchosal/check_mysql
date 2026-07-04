---
wiki:
  sections:
    - id: bootstrap
      title: Bootstrap & Organisation
    - id: cli
      title: CLI (commandes Nagios)
    - id: core
      title: Core (config, connexion, client, nagios)
    - id: services
      title: Services (checks)
    - id: quality
      title: Qualité & Gates
    - id: ci
      title: CI & Publication
    - id: doc
      title: Documentation
---

# Architecture — check_mysql

Plugin Nagios pour MySQL/MariaDB, connexion directe (PyMySQL) ou via tunnel
SSH (sshtunnel). Architecture en trois couches, pillée de check_msdefender :

```
check_mysql/
├── cli/         # click group, décorateurs communs, handlers.run_check,
│   └── commands/  # une commande par check (uptime, connections,
│                  # replication, slowqueries, latency)
├── core/        # config (.ini + overrides CLI), connection (direct/tunnel),
│                # mysql_client (requêtes SHOW/SELECT), nagios (runner,
│                # plages, perfdata), models (dataclasses/TypedDict/Protocol),
│                # exceptions, logging_config
└── services/    # un service par check ; dépend de MySQLClientProtocol,
                 # donc testable sans serveur
```

Flux d'une commande : `cli/commands/X` → `handlers.run_check` →
`config` → `MySQLConnector` (tunnel SSH optionnel) → `MySQLClient` →
`XService.get_result()` → `NagiosPlugin.check()` → sortie + exit code.

Qualité : `pdm run check` (ruff, flake8+docstrings, pyright strict,
interrogate, refurb, vulture, pytest+coverage, metrics-gate avec cliquet) —
voir doc/code-quality.md.
