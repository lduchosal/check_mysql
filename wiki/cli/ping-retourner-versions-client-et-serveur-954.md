---
id: 954
title: "PING / Retourner versions client et serveur"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T11:10:36
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: cli
section_title: "CLI (commandes Nagios)"
---

# #954 — PING / Retourner versions client et serveur

Ajouter une commande `ping` à check_mysql qui vérifie la connectivité et retourne la version du client et celle du serveur.

## Comportement attendu

- `check_mysql ping` se connecte (direct ou tunnel SSH, comme les autres commandes) et affiche :
  - la version du client (PyMySQL)
  - la version du serveur MySQL/MariaDB (`SELECT VERSION()` / `server_info`)
- Sortie Nagios standard : `PING OK - client x.y.z, server a.b.c` → exit 0
- Échec de connexion : `PING CRITICAL - <message>` → exit 2

## Garde-fous

- Tests sans serveur MySQL réel (mock client Protocol, fakes, CliRunner)
- `pdm run check` vert (pyright strict, interrogate, cliquet metrics-gate)

---

## Résolution

### Modifications
- check_mysql/services/ping_service.py : nouveau PingService — RTT en valeur, versions en headline, CriticalError si serveur injoignable
- check_mysql/cli/commands/ping.py : nouvelle commande `ping` (sans seuils par défaut)
- check_mysql/cli/commands/__init__.py : enregistrement de la commande
- check_mysql/cli/handlers.py : seuils warning/critical passés en Optional[str] (ping n'a pas de seuils)
- check_mysql/core/mysql_client.py : get_versions() — SELECT VERSION() + pymysql.__version__
- check_mysql/core/models.py : get_versions() ajouté au MySQLClientProtocol
- typings/pymysql/__init__.pyi : déclaration de __version__ pour pyright strict
- tests/fixtures/mock_mysql_client.py : paramètre versions sur le mock
- tests/unit/test_ping_service.py : 3 tests (versions, défauts fixture, CRITICAL)
- tests/unit/test_mysql_client.py : TestVersions (2 tests)
- tests/integration/test_cli_integration.py : TestPingCommand (2 tests e2e CliRunner) + `ping` dans le test --help
- README.md : features, usage, tableau des commandes, définitions Nagios, arborescence, exemple de sortie

### Comportements obtenus
- `check_mysql ping` → `MYSQL OK - client PyMySQL 1.1.1, server 8.4.0 | ping=1.23ms`, exit 0 (bannière MYSQL, cohérente avec les autres commandes)
- Serveur injoignable (MySQLConnectionError/SSHTunnelError) → `MYSQL CRITICAL - Cannot connect to …`, exit 2 (et non UNKNOWN 3 : pour un ping, l'injoignabilité est l'alerte)
- Perfdata `ping=<rtt>ms` ; seuils -W/-C optionnels applicables au RTT
- Fonctionne en direct et via tunnel SSH (même chemin run_check que les autres commandes)

### Garde-fous
- Smoke test réel : `check_mysql ping` vers un port fermé → `MYSQL CRITICAL - Cannot connect to MySQL at 127.0.0.1:33099: (2003, …)`, exit 2
- ruff format/lint, flake8(+docstrings), pyright strict (0 erreur), interrogate 100 %, refurb, vulture : verts
- pytest : 145 passed, sans serveur MySQL ; ping_service.py et get_versions couverts à 100 %
- metrics-gate : échoue uniquement sur les fichiers de la tâche parallèle en cours (sql_service.py / longrunning_service.py à 37.5 % de couverture, format de sql.py) — aucun manquement imputable à cette carte ; à re-vérifier quand la carte SQL/counters sera posée
---

[← retour à cli](index.md) · [voir log](../log/2026-07-04.md)
