---
id: 965
title: "DOC / Synchroniser la doc avec la totalité des fonctionnalités"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T13:18:40
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: doc
section_title: "Documentation"
---

# #965 — DOC / Synchroniser la doc avec la totalité des fonctionnalités

Synchroniser la totalité de la documentation avec l'état réel des fonctionnalités :

- `check_mysql --help` et l'aide de chaque sous-commande (textes exacts, options, défauts)
- README.md : commandes, options, seuils, sections Nagios / Configuration / Files, exemples
- check_mysql.ini.example : toutes les sections et options supportées
- Exemples de configuration Nagios (commands.cfg, services)
- Toute doc sous doc/

Puis : commit de l'ensemble et publication (`./publish.sh`).

---

## Résolution

### Modifications
- README.md : Features réécrites (22 checks, audit sécurité CIS, init guidé) ; table des commandes — weak/expired password ajoutés à la ligne `security` ; héritage check_mysql_health clarifié (`threadcache`…`longrunning` + `sql`, `security` est à nous) ; ordre de recherche du fichier de config corrigé (cwd → /usr/local/etc/nagios → /etc/nagios, `-c` absolu — « next to the plugin » était faux) ; option `[mysql] database` documentée ; exemple `[security] admins` + explication allow/admins ; options par commande (`--sql`, `init --yes/--force`) ; définitions Nagios command/service pour `security` + note « toutes les commandes suivent le même patron » ; arbre Architecture synchronisé avec les modules réels (14 modules de commandes, provisioning.py, status.py, ratio/counter/security services) ; exemple de sortie security + ping actualisé ; flags publish.sh (--quality/--ci/--minor/--major)
- check_mysql.ini.example : en-tête corrigé (« working directory », pas « next to the plugin »)
- scripts/quality_metrics.py + doc/code-quality.md : cliquet palier 4 — test_cov 90 → 95, max_func_lines 50 → 45 (mesuré 99,64 % / 42)

Tous les seuils par défaut de la table README vérifiés contre le code (specs RATIO_SPECS/COUNTER_SPECS + commandes individuelles) : aucun écart. check_mysql.ini.example était déjà à jour (session #961).

### Comportements obtenus
- README, ini.example et --help racontent la même chose que le code pour les 22 commandes, la config ([mysql] database inclus, [security] allow+admins, [ssh]) et Nagios
- Gate qualité resserré au palier 4

### Garde-fous
- `pdm run check` vert avant et après le resserrage (243 tests, cov 99,64 %, gate palier 4 PASS)
- Sorties d'exemple vérifiées sur le serveur local réel (ping, security, config manquante)

### Coordination
- Session #961 en parallèle : son commit b45bfd2 (audit weak/expired/execute/admins) embarquait déjà ses maj README/ini — conservées et complétées, rien refait
- publish.sh (#964, en review) commité séparément : 65a94ab
- Commits : 65a94ab (#964), 39b1a2c (doc sync #965), 170a076 (reflow docformatter), b36dbe2 (exclusion Sonar), 3a08bc6 (release)

### Release
- **0.2.3 publiée sur PyPI** via ./publish.sh --patch, tag check-mysql-0.2.3 poussé, arbre propre
- Incident 1 : gate SonarCloud timeout 900 s au premier run (latence de l'analyse) — relance, OK
- Incident 2 : gate rouge au deuxième run — 3 BLOCKER python:S930 **faux positifs** sur mysql_client.py (les stubs pymysql de l'analyseur croient cursor() sans argument ; PyMySQL 2.2.8 expose cursor(self, cursor=None), vérifié sur le paquet installé, e2e verts). Le marquage FP via l'API SonarCloud a été refusé par le classifier de permissions → exclusion scopée (règle S930 × mysql_client.py) dans sonar-project.properties (b36dbe2), justifiée en commentaire. À retirer si tu préfères marquer les 3 issues FP dans l'UI SonarCloud.
---

[← retour à doc](index.md) · [voir log](../log/2026-07-04.md)
