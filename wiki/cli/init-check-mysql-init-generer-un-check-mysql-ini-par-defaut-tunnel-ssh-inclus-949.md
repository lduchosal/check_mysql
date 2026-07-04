---
id: 949
title: "INIT / check_mysql init : générer un check_mysql.ini par défaut (tunnel SSH inclus)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T10:25:25
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: cli
section_title: "CLI (commandes Nagios)"
---

# #949 — INIT / check_mysql init : générer un check_mysql.ini par défaut (tunnel SSH inclus)

Ajouter une commande `check_mysql init` qui crée un fichier `check_mysql.ini` avec des paramètres par défaut raisonnables, y compris les réglages de tunnel SSH (ssh forwarding).

## Comportement attendu

- `check_mysql init` écrit `check_mysql.ini` dans le répertoire courant (ou au chemin passé via `-c/--config`)
- Contenu généré : section `[mysql]` active avec des défauts raisonnables (host localhost, port 3306, user monitoring, timeout 10, database commenté) + section `[ssh]` complète mais commentée (host bastion, port 22, user, private_key ~/.ssh/id_ed25519, password alternatif) — dé-commenter la section active le tunnel
- Refuse d'écraser un fichier existant ; `--force` pour outrepasser
- Le fichier est créé en mode 600 (il contiendra un mot de passe)
- Sortie claire : chemin créé + prochaine étape (éditer les credentials)

## Garde-fous attendus

- Tests d'intégration CLI (CliRunner) : création, refus d'écrasement, --force, mode 600, le fichier généré est chargeable par load_config et get_ssh_config retourne None (section commentée)
- README mis à jour (quick start + tableau des commandes)
- pdm run check entièrement vert (gate + cliquet : test_cov ne doit pas régresser)

---

## Résolution

### Modifications

- check_mysql/core/config.py : DEFAULT_CONFIG_TEMPLATE ([mysql] actif avec défauts, [ssh] complet commenté) + write_default_config(path, force) — refuse d'écraser sans force (ConfigurationError), écrit en mode 600
- check_mysql/cli/commands/init.py : commande `init` (-c/--config, --force) — succès exit 0 avec next steps, erreur exit 1 sur stderr
- check_mysql/cli/commands/__init__.py : enregistrement de la commande
- tests/unit/test_config.py : 5 tests write_default_config (mode 600, fichier chargeable avec get_ssh_config None, présence de la doc tunnel dans le template, refus d'écrasement, --force)
- tests/integration/test_cli_integration.py : 4 tests CLI (création + mode 600, refus exit 1, --force, le fichier généré alimente réellement `check_mysql uptime`)
- README.md : quick start (`check_mysql init`), ligne dans le tableau des commandes, section Configuration

### Comportements obtenus

- `check_mysql init` génère un check_mysql.ini prêt à éditer (mode 600) ; la connexion par défaut est directe, le tunnel SSH s'active en dé-commentant la section [ssh] livrée avec le template
- `check_mysql init -c /chemin/custom.ini` et `--force` fonctionnent ; un fichier existant n'est jamais écrasé silencieusement
- Smoke test réel : création (mode 600 vérifié), relance → « already exists — use --force » exit 1, `check_mysql uptime` consomme le fichier généré

### Garde-fous

- pdm run check : VERT (isort, format-check, ruff, flake8, pyright strict 0, interrogate 100 %, refurb 0, vulture 0, 87 tests passés, metrics-gate PASS)
- Couverture : 99.82 % (cliquet best-ever respecté : 99.81 → 99.82), min par fichier 98.41 %
- Snapshot enregistré dans doc/quality-history.csv
- Non commité : en attente de ta review
---

[← retour à cli](index.md) · [voir log](../log/2026-07-04.md)
