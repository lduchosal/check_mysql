# Code quality — standard lduchosal

check_mysql suit le standard qualité établi dans les projets kenboard et
check_msdefender. Le pipeline est piloté par `publish.sh` (et `pdm run check`
en local) ; chaque étape doit être verte avant publication.

## Outils

| Étape            | Outil                         | `pdm run …`     |
|------------------|-------------------------------|-----------------|
| Imports absolus  | absolufy-imports              | `absolufy`      |
| Tri des imports  | ruff (`--select I`)           | `isort`         |
| Formatage        | ruff format                   | `format`        |
| Docstrings (fmt) | docformatter                  | `docformatter`  |
| Typage           | pyright (strict)              | `typecheck`     |
| Docstrings (lint)| flake8 + flake8-docstrings(-complete) | `flake8` |
| Couverture docs  | interrogate (≥ 95 %)          | `interrogate`   |
| Qualité code     | refurb                        | `refurb`        |
| Lint             | ruff                          | `lint`          |
| Code mort        | vulture                       | `vulture`       |
| Tests + coverage | pytest + coverage             | `test` / `test-ci` |
| **Gate bloquant**| scripts/quality_metrics.py    | `metrics-gate`  |
| Gate SonarCloud  | scripts/sonar_gate.py         | `sonar-gate`    |

> Le formatage reste sur **ruff** (unifié isort+format) — même choix que
> check_msdefender, au lieu du couple black+isort de kenboard.

## Gate bloquant (métriques + cliquet)

`scripts/quality_metrics.py --gate` applique, sur `check_mysql/` :

- des **plafonds/planchers absolus** (`GATE_MAX` / `GATE_MIN`) ;
- un **cliquet best-ever** (`RATCHET_DOWN` / `RATCHET_UP`) lu dans
  `doc/quality-history.csv` : aucune métrique suivie ne peut régresser
  au-delà de sa meilleure valeur historique.

Les règles dont la donnée est absente (pas de `.coverage`) sont **sautées**,
pas échouées — d'où l'ordre « tests → gate » dans `publish.sh`.

### Procédure des paliers

Le gate matérialise un **palier courant**. Dès qu'il est vert :

1. enregistrer un snapshot — `pdm run metrics-record` ;
2. **resserrer** un ou plusieurs seuils (`GATE_MAX`/`GATE_MIN`) au palier
   suivant et committer.

Un gate vert n'est jamais un état stable : on resserre jusqu'aux cibles
finales. On ne **détend** JAMAIS un seuil sans décision humaine explicite.

### Palier 1 (greenfield, 2026-07-04, v0.1.0)

Contrairement à check_msdefender (palier initial calé sur l'existant), le
projet naît directement avec un palier serré :
`max_file_lines=500`, `max_func_lines=60`, `c901_over_10=0`,
`vulture/refurb/pyright=0`, `docstring_cov≥95 %`, `test_cov≥80 %`,
`min_file_cov≥50 %` (les stubs d'entrée `__main__.py` sont exclus de la
mesure de couverture via `[tool.coverage.run] omit`).

Cibles de resserrage envisagées : `max_func_lines` → 50, `test_cov` → 90 %+,
`min_file_cov` → 75 %+.

### Palier 2 (2026-07-04, backport check_mysql_health)

Gate vert au palier 1 après le backport des checks check_mysql_health
(task #951) : resserrage de `max_func_lines` 60 → 50, `test_cov` 80 → 90 %,
`min_file_cov` 50 → 75 % (mesuré : 40 lignes / 99,59 % / 96 %).
Prochaines cibles : `min_file_cov` → 90 %+, `loc` par fichier à surveiller.

### Palier 3 (2026-07-04, commande security)

Gate vert au palier 2 après l'audit des comptes (task #957) : resserrage de
`min_file_cov` 75 → 90 % (mesuré : 96 %, test_cov 99,63 %).
Prochaines cibles : `test_cov` → 95 % en plancher absolu (le cliquet le tient
déjà plus haut), `max_func_lines` → 40.

### Palier 4 (2026-07-04, sync doc + audit weak/expired passwords)

Gate vert au palier 3 après l'extension de l'audit (weak/expired passwords,
`[security] admins`) et la synchronisation de la doc (task #965) : resserrage
de `test_cov` 90 → 95 % et `max_func_lines` 50 → 45 (mesuré : 99,64 % / 42
lignes). Prochaines cibles : `max_func_lines` → 40, `min_file_cov` → 95 %.

## Tests end-to-end (serveur local)

`tests/e2e/` pilote le **binaire installé** (`.venv/bin/check_mysql`) en
sous-process contre le serveur MySQL local configuré dans `check_mysql.ini`
(gitignoré — `check_mysql init` pour le créer) : vraie connexion PyMySQL,
vrai SQL, vrais codes de sortie Nagios. La suite porte le marker `e2e` et
est **exclue du run pytest par défaut** (`-m "not e2e"` dans pytest.ini) ;
`pdm run test-e2e` l'exécute, et elle **bloque la publication** : étape
dédiée de `publish.sh` (sautée en mode `--ci`, les runners GitHub n'ayant
ni serveur ni ini) et prérequis du script composite `pdm run publish`.

## SonarCloud

`sonar-project.properties` (clé `lduchosal_check_mysql`, org `lduchosal`)
+ le job `sonarcloud` de `.github/workflows/python-package.yml` poussent
l'analyse à chaque push sur `main`. `publish.sh` pousse le commit puis
attend le quality gate via `scripts/sonar_gate.py`.

**Setup requis (une fois)** : créer le projet sur sonarcloud.io, ajouter le
secret `SONAR_TOKEN` au dépôt GitHub, et exporter `SONAR_TOKEN` en local pour
activer le gate dans `publish.sh` (sinon l'étape se saute proprement).
