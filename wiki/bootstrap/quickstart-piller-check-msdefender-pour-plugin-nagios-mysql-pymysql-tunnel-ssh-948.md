---
id: 948
title: "QUICKSTART / Piller check_msdefender pour plugin Nagios MySQL (pymysql + tunnel SSH)"
status: review
who: "Claude"
due_date: 
classified_at: 2026-07-04T09:38:46
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: bootstrap
section_title: "Bootstrap & Organisation"
---

# #948 — QUICKSTART / Piller check_msdefender pour plugin Nagios MySQL (pymysql + tunnel SSH)

Piller le projet /Users/q/Projects/check_msdefender (qualité, CI, documentation, architecture, organisation) pour réaliser **check_mysql**, un plugin Nagios pour MySQL avec connexion directe (PyMySQL) et connexion par tunnel SSH.

## Objectif

Un plugin Nagios de qualité maximale (tests, doc, UX) sur le standard lduchosal établi dans kenboard/check_msdefender.

## À piller de check_msdefender

- **Architecture** : cli/ (click group + commands + decorators) / core/ (config, client, nagios, exceptions, logging_config, models Protocol+TypedDict) / services/ (un service par check, injectable, testable via Protocol)
- **Qualité** : PDM + pyproject, ruff (isort+format+lint), pyright strict + typings/*.pyi, flake8 + flake8-docstrings(-complete), interrogate ≥ 95 %, refurb, vulture, docformatter, absolufy-imports, pytest + coverage
- **Gate bloquant** : scripts/quality_metrics.py (plafonds/planchers absolus + cliquet best-ever vs doc/quality-history.csv), pdm run check composite
- **CI** : .github/workflows/python-package.yml (matrix 3.10→3.13 + job SonarCloud), publish.yml, publish.sh, sonar-project.properties, scripts/sonar_gate.py
- **Doc** : README complet (badges, quickstart, commandes, config, intégration Nagios, architecture, troubleshooting, exit codes), doc/code-quality.md, LICENSE MIT, check_mysql.ini.example
- **Organisation** : pytest.ini, .flake8, .gitignore, .env.example, tests/{unit,fixtures,integration}

## Fonctionnel

Connexion :
- Directe : PyMySQL vers host:port
- Tunnel SSH : sshtunnel (paramiko) vers un bastion, puis PyMySQL à travers le tunnel
- Configuration via check_mysql.ini (section [mysql] + section [ssh] optionnelle qui active le tunnel)

Checks (commandes CLI, sortie et exit codes Nagios 0/1/2/3, perfdata) :
- uptime : secondes depuis le démarrage (alerte si redémarrage récent, seuils bas)
- connections : Threads_connected en % de max_connections
- replication : Seconds_Behind_Source + état des threads IO/SQL (CRITICAL si arrêtés)
- slowqueries : compteur Slow_queries
- latency : temps de réponse d'un SELECT 1 en ms

UX : -c/--config, -W/--warning, -C/--critical (plages Nagios), -v/-vv/-vvv, --version, messages UNKNOWN propres.

## Garde-fous attendus

- pdm run check entièrement vert (isort, format, lint, flake8, pyright strict, interrogate, refurb, vulture, tests+coverage, metrics-gate)
- Tests unitaires (services via mock client), fixtures, intégration CLI (CliRunner) — sans besoin d'un MySQL réel
- Gate palier 1 serré (greenfield) : max_func_lines ≤ 60, c901_over_10 = 0, test_cov ≥ 80 %, docstring_cov ≥ 95 %

---

## Résolution

### Modifications

- check_mysql/ : package complet, architecture cli/core/services pillée de check_msdefender
  - core/config.py : load_config (cwd, /usr/local/etc/nagios, /etc/nagios) + get_mysql_config (overrides CLI -H/-P) + get_ssh_config ([ssh] optionnelle, clé ou mot de passe, expanduser)
  - core/connection.py : MySQLConnector — direct PyMySQL ou tunnel sshtunnel vers bastion (local_bind 127.0.0.1:0, teardown propre en cas d'échec MySQL à travers le tunnel)
  - core/mysql_client.py : MySQLClient (context manager, connexion lazy) — get_global_status/variables, get_replica_status (SHOW REPLICA STATUS + fallback SHOW SLAVE STATUS), ping (SELECT 1 chronométré)
  - core/nagios.py : NagiosPlugin (plages Nagios standard via ScalarContext, perfdata avec uom, CriticalError → exit 2, Exception → UNKNOWN 3), MySQLSummary (1re ligne = headline, suite = long output)
  - core/models.py : dataclasses MySQLConfig/SSHConfig, ServiceResult TypedDict (value requis), Protocols MySQLClientProtocol/CheckServiceProtocol
  - services/ : uptime, connections (% de max_connections), replication (colonnes modernes Replica_*/Source_* et legacy Slave_*/Master_*, CRITICAL immédiat si threads arrêtés ou lag NULL), slowqueries (+ taux/heure), latency
  - cli/ : click group + décorateurs communs (-c, -H, -P, -W, -C, -v) + handlers.run_check partagé + 5 commandes ; seuils par défaut : uptime 3600:/300:, connections 80/95, replication 60/300, slowqueries 100/1000, latency 100/500
- tests/ : 78 tests (unit services/config/connection/client/nagios/logging + intégration CLI CliRunner) — zéro MySQL requis (mock Protocol + fakes + monkeypatch)
- typings/ : stubs pyright strict pour nagiosplugin (copié), pymysql et sshtunnel (écrits, surface utilisée)
- Qualité/CI : pyproject.toml (PDM, scripts identiques à check_msdefender + smoke), scripts/quality_metrics.py (gate palier 1 serré greenfield : max_func_lines 60, c901 0, test_cov ≥ 80, min_file_cov ≥ 50), scripts/sonar_gate.py (clé lduchosal_check_mysql, branche main), publish.sh, .github/workflows (matrix 3.10→3.13 + SonarCloud, publish manuel), sonar-project.properties, pytest.ini, .flake8, .gitignore, .env.example
- Doc : README.md complet (badges, quickstart, tableau commandes, config directe/tunnel, user MySQL minimal, intégration Nagios cfg, architecture, exemples de sortie, troubleshooting, exit codes), doc/code-quality.md, check_mysql.ini.example, LICENSE MIT, CLAUDE.md (section qualité)
- doc/quality-history.csv : premier snapshot enregistré (metrics-record)
- Supprimé : main.py (scaffold PyCharm)

### Comportements obtenus

- check_mysql {uptime,connections,replication,slowqueries,latency} avec sortie Nagios (MYSQL OK/WARNING/CRITICAL + perfdata avec unités s/%/c/ms) et exit codes 0/1/2/3
- Connexion directe ou via tunnel SSH selon la présence de [ssh] dans check_mysql.ini ; -H/-P surchargent la cible sans éditer la config (Nagios $HOSTADDRESS$)
- replication : CRITICAL immédiat si thread IO/SQL arrêté (avec Last_IO_Error) ou lag NULL ; UNKNOWN si pas un replica ; compatible MySQL ≥ 8.0.22 et anciens serveurs
- Plages Nagios complètes acceptées en -W/-C (95, 300:, 10:20)
- Smoke test réel : --help, --version, config manquante → UNKNOWN exit 3

### Garde-fous

- pdm run check : VERT de bout en bout (isort, format-check, lint ruff, flake8+docstrings, pyright strict 0 erreur, interrogate 100 %, refurb 0, vulture 0, 78 tests passés, metrics-gate PASS)
- Couverture : 99.81 % total, min par fichier 98.18 % (planchers gate : 80 / 50)
- Métriques : max_func_lines 39 (plafond 60), c901_over_10 0, ruff_debt 0
- Gate palier 1 : PASS + snapshot enregistré dans doc/quality-history.csv
- Rien n'est commité : l'arbre de travail attend ta review (repo git sans commit initial)
---

[← retour à bootstrap](index.md) · [voir log](../log/2026-07-04.md)
