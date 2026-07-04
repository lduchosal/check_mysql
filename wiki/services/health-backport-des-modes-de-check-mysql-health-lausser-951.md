---
id: 951
title: "HEALTH / Backport des modes de check_mysql_health (lausser)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T11:16:20
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: services
section_title: "Services (checks)"
---

# #951 — HEALTH / Backport des modes de check_mysql_health (lausser)

Backport des modes de https://github.com/lausser/check_mysql_health (plugin Nagios Perl de G. Lausser, GPL-2.0) dans check_mysql (architecture cli/core/services, PyMySQL direct ou tunnel SSH).

## Déjà couvert (équivalents existants)

- connection-time → `latency`
- uptime → `uptime`
- threads-connected → `connections`
- slow-queries → `slowqueries`
- slave-lag / slave-io-running / slave-sql-running → `replication`

## Modes à backporter

Hitrates / caches :
- threadcache-hitrate — efficacité du cache de threads
- querycache-hitrate + querycache-lowmem-prunes — cache de requêtes (MariaDB uniquement : supprimé de MySQL 8.0 → détecter et sortir UNKNOWN proprement)
- keycache-hitrate — cache de clés MyISAM
- tablecache-hitrate — cache de tables
- bufferpool-hitrate + bufferpool-wait-free — buffer pool InnoDB

Charge / contention :
- log-waits — attentes sur le log InnoDB
- table-lock-contention — taux de verrous de tables en attente
- index-usage — usage des index vs full table scans
- tmp-disk-tables — tables temporaires créées sur disque
- long-running-procs — processus dépassant une durée seuil (PROCESSLIST)
- open-files — descripteurs ouverts vs open_files_limit

Générique :
- sql — requête SQL arbitraire, résultat comparé aux seuils warning/critical

## Hors scope (proposé)

- cluster-ndb-running (NDB cluster, cas rare)
- encode (utilitaire d'échappement, sans objet en Python)

## Notes d'implémentation

- La plupart des modes se réduisent à SHOW GLOBAL STATUS / SHOW GLOBAL VARIABLES + un ratio : mutualiser un service status/variables dans core/services plutôt qu'une requête par commande.
- check_mysql_health calcule les hitrates en delta entre deux exécutions (fichier d'état) ; trancher : ratio depuis le démarrage du serveur (simple, sans état) vs delta persisté — documenter le choix dans le README.
- Suivre les conventions des commandes existantes : sortie Nagios, perfdata, seuils -w/-c, config check_mysql.ini.
- Tests sans serveur MySQL (mock client Protocol, fakes, CliRunner) ; `pdm run check` vert et cliquet qualité respecté.
- Probablement à découper en plusieurs cartes filles au moment du passage en doing (une par groupe de modes).

Référence modes : https://omd.consol.de/docs/plugins/check_mysql_health/

---

## Résolution

### Modifications

Approche table-driven plutôt que 14 fichiers copiés-collés : deux services génériques pilotés par des specs (dataclasses figées) + trois services dédiés.

- check_mysql/core/status.py : helpers partagés read_int / sum_counters (lecture stricte des compteurs SHOW, hint optionnel dans l'erreur)
- check_mysql/services/ratio_service.py : RatioSpec + catalogue RATIO_SPECS (8 modes : threadcache, querycache, keycache, tablecache, bufferpool, tablelocks, indexusage, tmpdisktables) + RatioService (pourcentage clampé 0-100, empty_value si dénominateur nul)
- check_mysql/services/counter_service.py : CounterSpec + COUNTER_SPECS (querycacheprunes, bufferpoolwaits, logwaits) + CounterRateService (taux moyen /s depuis le démarrage)
- check_mysql/services/openfiles_service.py : Open_files vs open_files_limit (%)
- check_mysql/services/longrunning_service.py : requêtes actives > 60 s via PROCESSLIST (Sleep/Daemon/Binlog Dump exclus, Time invalide toléré)
- check_mysql/services/sql_service.py : scalaire d'une requête arbitraire
- check_mysql/core/mysql_client.py + core/models.py : méthodes get_processlist() et query_scalar() ajoutées au client et au Protocol
- check_mysql/cli/commands/{ratios,counters}.py : enregistrement en boucle depuis les catalogues ; {openfiles,longrunning,sql}.py : commandes classiques ; __init__.py : câblage
- tests : 5 nouveaux fichiers unitaires + extensions test_mysql_client, test_cli_integration (paramétré sur les catalogues), fixtures status_data.json (compteurs + processlist) et mock client
- README.md (tableau des 14 commandes, § « check_mysql_health Heritage », grants PROCESS), ARCHITECTURE.md
- scripts/quality_metrics.py + doc/code-quality.md : gate vert → snapshot enregistré puis palier 2 (max_func_lines 60→50, test_cov 80→90, min_file_cov 50→75)

### Comportements obtenus

- 14 nouvelles commandes avec les seuils par défaut de check_mysql_health : threadcache (90:/80:), querycache (90:/80:), querycacheprunes (1/10), keycache (99:/95:), tablecache (99:/95:), bufferpool (99:/95:), bufferpoolwaits (1/10), logwaits (1/10), tablelocks (1/2), indexusage (90:/80:), tmpdisktables (25/50), openfiles (80/95), longrunning (10/20), sql (sans seuil par défaut : plage « ~: », jamais d'alerte — « » alerterait sur les négatifs)
- querycache/querycacheprunes sur MySQL 8.0+ : UNKNOWN propre avec hint « query cache removed in MySQL 8.0 »
- Choix documenté (README) : taux moyens depuis le démarrage du serveur, pas de fichier d'état (diffère volontairement de l'original qui fait du delta entre exécutions)
- sql : `--sql "SELECT ..."` obligatoire, première colonne de la première ligne, seuils -W/-C optionnels
- longrunning liste les requêtes fautives en long output ; nécessite le grant PROCESS (documenté)

### Garde-fous

- pdm run check : VERT de bout en bout (isort, format-check, lint, flake8, pyright strict 0, interrogate 100 %, refurb 0, vulture 0, 183 tests OK, metrics-gate PASS)
- Couverture totale 99,59 % (cliquet ≥ 99,32 respecté), 100 % sur chaque nouveau fichier, min_file_cov 96 %
- metrics-record exécuté puis gate resserré au palier 2 (re-vérifié PASS)
- Smoke test CLI réel : --help liste les 20 commandes, threadcache --help correct, exit 3 UNKNOWN sur config absente
- Hors scope confirmé : cluster-ndb-running, encode
- Note : développement en parallèle avec la tâche #950 dans le même arbre de travail (commandes ping/init, tests e2e) ; les gates ont été passés sur l'état combiné
---

[← retour à services](index.md) · [voir log](../log/2026-07-04.md)
