---
id: 957
title: "SEC / Report over-privileged MySQL accounts"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T11:40:43
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: services
section_title: "Services (checks)"
---

# #957 — SEC / Report over-privileged MySQL accounts

# SEC / check_mysql : détecter et rapporter les comptes trop puissants

## Contexte

check_mysql sait vérifier ping, ratios, counters, longrunning, openfiles, sql.
Il manque un contrôle de sécurité sur les comptes MySQL/MariaDB : des comptes
sur-privilégiés ou mal configurés passent inaperçus jusqu'à l'incident.

## Objectif

Nouvelle commande `security` (pattern cli/core/services identique aux autres checks)
qui inspecte `mysql.user` / `information_schema` et rapporte les comptes à risque
au format Nagios (OK / WARNING / CRITICAL + perfdata).

## Détections attendues

- Privilèges globaux dangereux : `ALL PRIVILEGES ON *.*`, `SUPER`, `GRANT OPTION`,
  `FILE`, `PROCESS`, `SHUTDOWN` (hors comptes système attendus)
- `root` (ou équivalent) accessible depuis un host distant (autre que `localhost`/`127.0.0.1`/`::1`)
- Comptes avec host wildcard `%`
- Comptes anonymes (user vide)
- Comptes sans mot de passe / `authentication_string` vide

## Comportement Nagios

- OK : aucun compte à risque
- WARNING / CRITICAL : seuils sur le nombre de comptes à risque (`--warning`, `--critical`,
  cohérents avec les autres commandes), liste des comptes fautifs dans la sortie
- Perfdata : compteur par catégorie de détection

## Contraintes

- Whitelist configurable dans `check_mysql.ini` (comptes système/attendus à exclure)
- Le compte utilisé par le plugin n'a besoin que de `SELECT` sur `mysql.user` —
  documenter le GRANT minimal dans le README
- Tests unitaires sans serveur MySQL (mock client Protocol, fixtures), test e2e optionnel
- `pdm run check` vert (pyright strict, interrogate, metrics-gate…)

---

## Résolution

### Modifications
- check_mysql/services/security_service.py : nouveau SecurityService — audite les lignes mysql.user, value = nb de comptes à risque, détails par compte
- check_mysql/cli/commands/security.py : commande `security` (défauts W:0, C:5), factory liant la whitelist de l'ini
- check_mysql/cli/commands/__init__.py : enregistrement de la commande
- check_mysql/core/mysql_client.py : get_user_accounts() — SELECT * FROM mysql.user (DictCursor)
- check_mysql/core/models.py : get_user_accounts ajouté au MySQLClientProtocol
- check_mysql/core/config.py : get_security_allowlist() — section [security], option allow lue en raw (pas d'échappement du %)
- check_mysql.ini.example : section [security] commentée documentée
- README.md : ligne `security` dans le tableau des commandes + GRANT minimal (SELECT ON mysql.user) + exemple [security]
- tests/fixtures/{mock_mysql_client.py,status_data.json} : user_accounts (fixture serveur durci : root local, comptes sys verrouillés, nagios)
- tests/unit/test_security_service.py : 23 tests (détections, exemptions, reporting)
- tests/unit/test_config.py : 4 tests get_security_allowlist
- tests/unit/test_mysql_client.py : 2 tests get_user_accounts
- tests/integration/test_cli_integration.py : TestSecurityCommand (OK/WARNING/CRITICAL/whitelist ini) + `security` dans --help
- tests/e2e/test_local_server.py : TestSecurityE2E tolérant (0 si grant présent, UNKNOWN sinon)
- scripts/quality_metrics.py + doc/code-quality.md : palier 3 (min_file_cov 75 → 90 %)
- check_mysql/core/provisioning.py : `GRANT SELECT ON mysql.user` ajouté au provisioning
  de `init` (statements exécutés et bloc SQL imprimé) — suivi de review
- tests/unit/test_provisioning.py : assertions étendues au 3e GRANT
- check_mysql/services/security_service.py + cli/commands/security.py : le user de
  monitoring (`[mysql] user`) est exempté du seul critère wildcard-host — suivi de review
  (le compte nagios@% créé par init déclenchait un WARNING sur toute install standard)

- README.md § Security Audit Semantics : table des 5 critères (mapping CIS Benchmark /
  mysql_secure_installation), liste des exemptions volontaires et des limites connues
  (mots de passe faibles non vides, plugins d'auth legacy, validate_password, base test,
  grants sur le schéma mysql, expiration, TLS) — suivi de review

- security_service.py : audit verbeux — suivi de review. `-v` : nombre de comptes audités ;
  `-vv` : comptes ignorés (verrouillés), exemptions appliquées (allowlist, monitoring user)
  et verdict par compte (clean / FLAGGED + findings) ; `-vvv` : chaque critère évalué par
  compte avec son résultat (ok / FLAGGED). 4 tests unitaires (capsys) sur la sortie stderr.

### Comportements obtenus
- `check_mysql security` : compte les comptes à risque — anonymes, sans mot de passe
  (plugins d'auth externes unix_socket/PAM/LDAP/GSSAPI exclus, colonnes Password ET
  authentication_string acceptées → MySQL et MariaDB), host wildcard `%` (ou vide),
  root joignable à distance, privilèges dangereux (SUPER, GRANT OPTION, FILE, PROCESS,
  SHUTDOWN, ou ALL PRIVILEGES si toutes les colonnes *_priv sont à Y) sur un host non local
- Les privilèges des comptes locaux (localhost/127.0.0.1/::1) ne sont pas signalés :
  root@localhost et debian-sys-maint restent silencieux sans whitelist — une install
  saine sort OK d'emblée
- Comptes verrouillés (account_locked) et plugin mysql_no_login ignorés (pas de surface d'attaque)
- Whitelist `[security] allow = user@host, …` (correspondance exacte User/Host, % sans échappement)
- Sortie Nagios : headline `N risky accounts out of M audited (catégorie: n, …)`,
  une ligne 'user'@'host' par compte fautif, perfdata `security=N` ; défauts W:0 C:5
- Écart assumé vs description : perfdata = compteur global (architecture mono-métrique
  du NagiosPlugin) ; les compteurs par catégorie sont dans la headline/long output
- Grant manquant → UNKNOWN propre : `SELECT command denied…` (vérifié contre le serveur local)
- `check_mysql init` crée (ou imprime) désormais le user avec le GRANT SELECT ON mysql.user
  requis par `security` ; README (§ MySQL Monitoring User) aligné sur le bloc généré
- Le user de monitoring n'est plus signalé pour son host `%` (il doit être joignable à
  distance par design) mais reste soumis aux autres critères (sans mot de passe,
  privilèges dangereux) ; le compte anonyme n'hérite jamais de l'exemption —
  vérifié contre le serveur local : `MYSQL OK - 0 risky accounts out of 16 audited`

### Garde-fous
- pdm run check vert : isort, format, lint, flake8, pyright strict, interrogate 100 %,
  refurb, vulture, 216 tests unit/intégration passés, couverture 99,63 %
- metrics-gate PASS puis cliquet : metrics-record enregistré, palier 3 activé
  (min_file_cov 75 → 90 %, GATE_PALIER 2 → 3, doc/code-quality.md § Palier 3)
- pdm run test-e2e : 25 tests passés contre le serveur local (dont les 2 nouveaux
  TestSecurityE2E — branche UNKNOWN, le nagios local n'ayant pas SELECT sur mysql.user)
---

[← retour à services](index.md) · [voir log](../log/2026-07-04.md)
