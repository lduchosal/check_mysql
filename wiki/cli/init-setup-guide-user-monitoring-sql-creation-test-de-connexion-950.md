---
id: 950
title: "INIT / Setup guidé : user monitoring (SQL, création, test de connexion)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T10:45:38
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: cli
section_title: "CLI (commandes Nagios)"
---

# #950 — INIT / Setup guidé : user monitoring (SQL, création, test de connexion)

Faire de `check_mysql init` la meilleure expérience de mise en route possible : au-delà de la génération du .ini (#949), guider l'utilisateur jusqu'à un monitoring fonctionnel.

## Expérience cible (mode interactif par défaut)

1. **Questions guidées** avec défauts raisonnables : host/port MySQL, user monitoring, mot de passe (généré aléatoirement par défaut), tunnel SSH oui/non (si oui : bastion host/port/user/clé privée)
2. **Écriture du check_mysql.ini** (mode 600, refus d'écrasement sans --force) — section [ssh] active si choisie, sinon commentée
3. **Affichage du SQL** de création du user monitoring (CREATE USER IF NOT EXISTS + GRANT USAGE, REPLICATION CLIENT) — copiable tel quel
4. **Proposition de créer le user maintenant** : demande des credentials admin (root, mot de passe masqué), connexion au serveur (en passant par le tunnel SSH si configuré !), exécution des statements (mot de passe passé en paramètre, identifiants échappés)
5. **Proposition de tester la connexion monitoring** : SELECT 1 chronométré + uptime, résultat affiché
6. **Récapitulatif** : fichier créé, user créé ou SQL à exécuter manuellement, prochaine étape (`check_mysql uptime`)

Un échec d'étape (création user, test) est signalé clairement mais n'interrompt pas le flux ; exit 1 si au moins une étape a échoué.

## Mode non interactif

`check_mysql init --yes` : comportement scriptable — template par défaut écrit tel quel + SQL affiché, pas de prompt, pas de connexion.

## Garde-fous attendus

- Nouveau module core/provisioning.py (statements + exécution) testé unitairement (échappement des quotes, commit, fermeture connexion/tunnel)
- Tests d'intégration CliRunner : flux interactif complet (input simulé), variante SSH, création du user (connecteur mocké), test de connexion (client mocké), --yes, refus d'écrasement
- max_func_lines ≤ 60 (helpers découpés), pdm run check vert, cliquet couverture respecté
- README mis à jour (setup guidé)

---

## Résolution

### Modifications

- check_mysql/core/provisioning.py (nouveau) : monitoring_user_statements (CREATE USER IF NOT EXISTS + GRANT USAGE, REPLICATION CLIENT — mot de passe en paramètre %s, identifiants échappés ''), monitoring_user_sql (bloc copiable), create_monitoring_user (exécution + commit, connexion/tunnel toujours libérés via finally)
- check_mysql/core/config.py : SSH_COMMENTED_SECTION extraite (source unique pour le template et le rendu), write_config(path, content, force) factorisé (mode 600), render_config(mysql, ssh) — section [ssh] active si tunnel choisi, commentée sinon
- check_mysql/cli/commands/init.py : réécrit en setup guidé — _prompt_settings (défauts : localhost/3306/monitoring, mot de passe secrets.token_urlsafe proposé, bastion optionnel), _create_user (credentials admin, mot de passe masqué, création via le tunnel si configuré, erreurs signalées sans crash), _test_connection (SELECT 1 chronométré + uptime), récapitulatif ; exit 1 si une étape a échoué ; `--yes` = ancien comportement scriptable (template + SQL, zéro prompt)
- tests/unit/test_provisioning.py (nouveau) : 6 tests (ordre et forme des statements, échappement des quotes user/host/password, exécution+commit+libération, libération sur échec)
- tests/unit/test_config.py : 3 tests render_config (round-trip direct et SSH via load_config/get_ssh_config, champs optionnels)
- tests/integration/test_cli_integration.py : TestInitYes (4 tests) + TestInitGuided (5 tests : défauts, variante SSH, création du user via connecteur mocké — credentials admin et binding du mot de passe vérifiés —, test de connexion, échec de création → exit 1)
- README.md : quick start, tableau des commandes et section Configuration réécrits pour le setup guidé

### Comportements obtenus

- `check_mysql init` guide de zéro à un monitoring opérationnel : questions avec défauts, .ini écrit (mode 600, [ssh] actif ou commenté), SQL affiché copiable, création du user monitoring sur le serveur (à travers le tunnel SSH le cas échéant), test de connexion (latence + uptime), récapitulatif
- Les échecs (création user, test) sont signalés clairement, le flux continue, exit code 1 en fin de parcours
- `check_mysql init --yes` reste scriptable (template par défaut + SQL, aucun prompt, aucune connexion)
- Smoke test réel : flux complet avec variante SSH piped — fichier correct, mode 600, exit 0

### Garde-fous

- pdm run check : VERT (isort, format-check, ruff, flake8, pyright strict 0, interrogate 100 %, refurb 0, vulture 0, 101 tests passés, metrics-gate PASS)
- Couverture : 99.4 % (≥ plancher cliquet 99.32), min par fichier 96.0 %, max_func_lines 39
- Snapshot enregistré dans doc/quality-history.csv
- Non commité : en attente de ta review (#949 aussi toujours en review)
---

[← retour à cli](index.md) · [voir log](../log/2026-07-04.md)
