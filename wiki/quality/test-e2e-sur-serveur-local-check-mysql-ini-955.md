---
id: 955
title: "TEST / E2E sur serveur local (check_mysql.ini)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T11:18:08
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: quality
section_title: "Qualité & Gates"
---

# #955 — TEST / E2E sur serveur local (check_mysql.ini)

Ajouter des tests end-to-end (E2E) pour le projet.

## Exigences

- TOUT doit être testé sur le serveur MySQL local, configuré dans `check_mysql.ini` (connexion réelle, pas de mocks).
- Les tests E2E doivent s'exécuter dans le `publish` : le script `pdm run publish` (actuellement `python -m twine upload dist/* --verbose`) doit faire tourner les tests E2E avant l'upload — publish bloqué si les E2E échouent.
- Les tests unitaires/intégration existants restent sans serveur (mocks) ; seuls les E2E utilisent le serveur local.

---

## Résolution

### Modifications
- tests/e2e/test_local_server.py : suite E2E consolidée — 23 tests pilotant le binaire installé (`.venv/bin/check_mysql`) en sous-process contre le serveur local (MySQL 8.4.9) de `check_mysql.ini`
- tests/e2e/conftest.py : fixtures `ini_path` (échec explicite si l'ini manque), `mysql_settings`, `run_cli` (sous-process depuis un cwd neutre)
- pytest.ini + pyproject.toml : marker `e2e`, exclu du run par défaut via `-m "not e2e"` ; script `test-e2e` (posés par la session #951 en parallèle, validés ici)
- pyproject.toml : `publish` devenu composite `["test-e2e", "publish-upload"]` — l'upload twine est bloqué si les E2E échouent (idem, posé en parallèle, validé ici)
- publish.sh : étape 27 « End-to-End Tests (local MySQL server) » avant le SonarCloud gate ; sautée en `--ci` (les runners GitHub n'ont ni serveur ni ini gitignoré)
- doc/code-quality.md : section « Tests end-to-end (serveur local) »
- README.md, CLAUDE.md : arborescence tests/e2e, `pdm run test-e2e`, exception documentée à la règle « tests sans serveur »

### Comportements obtenus
- Couverture E2E réelle (aucun mock) : les 5 checks (uptime, connections, latency, slowqueries, replication) en OK + WARNING/CRITICAL forcés par plages Nagios déterministes (`1:`, `@0:HUGE`, `HUGE`), overrides `-H`/`-P`, init `--yes`/refus d'écrasement/parcours guidé complet (probe réelle du serveur puis check sur l'ini généré), chemins d'erreur réels (port fermé, mot de passe rejeté par le serveur → Access denied, ini manquant → UNKNOWN 3), surface CLI (`--version`, `--help`, `python -m check_mysql`, logs `-vv` sur stderr)
- `pdm run test` / `pdm run check` restent sans serveur : 183 tests mocks, 23 E2E déselectionnés
- `pdm run test-e2e` : 23/23 verts en ~3 s ; serveur down = publish bloqué, par design

### Garde-fous
- `pdm run check` : PASS complet (isort, format, lint, flake8, pyright strict, interrogate 100 %, refurb, vulture, 183 tests, cov 99.59 %)
- `metrics-gate` : PASS au palier 2 (resserré en parallèle par la tâche #951 : max_func_lines 50, test_cov 90, min_file_cov 75) ; `metrics-record` effectué
- `pdm run test-e2e` : 23/23 PASS contre le serveur réel (guided init « Connection OK », mode 600 vérifié)
- Coordination : câblage pytest.ini/pyproject/publish.sh posé concurremment par la session #951 — conservé tel quel après validation ; les deux fichiers de tests E2E redondants ont été fusionnés en un seul (test_local_server.py)
---

[← retour à quality](index.md) · [voir log](../log/2026-07-04.md)
