---
id: 956
title: "RELEASE / Publish check_mysql to PyPI"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T12:17:01
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: ci
section_title: "CI & Publication"
---

# #956 — RELEASE / Publish check_mysql to PyPI

Publier check_mysql sur PyPI.

## Objectif

Rendre le plugin installable via `pip install` depuis PyPI.

## Étapes envisagées

- Vérifier les métadonnées `pyproject.toml` : nom, version, description, licence, classifiers, URLs, `requires-python`
- Vérifier la disponibilité du nom `check_mysql` sur PyPI (sinon choisir un nom alternatif, ex. `check-mysql-nagios`)
- Build avec `pdm build` (sdist + wheel) puis contrôle `twine check dist/*`
- Publication d'abord sur TestPyPI, installation de test dans un venv propre, puis publication sur PyPI
- Token PyPI hors repo (jamais committé)
- Documenter la procédure de release (bump version, tag, build, publish) dans le README ou doc/

## Garde-fous

- `pdm run check` vert avant toute publication

---

## Résolution

**Publié : https://pypi.org/project/check-mysql-nagios/0.2.0/** — `pip install check-mysql-nagios`. Tag `check-mysql-0.2.0`, commits `636ed29` (release) et `0ab20fb`/`738396f` (contenu + fixes).

### Modifications

- pyproject.toml : distribution renommée `check-mysql-nagios` (PyPI refuse `check-mysql`, « too similar » au projet existant `checkmysql` ; import et CLI restent `check_mysql`) ; auteur corrigé `lduchosal <lduchosal@users.noreply.github.com>` ; `__init__.py` et `test_cli_integration.py` ajoutés à l'exclusion docformatter (conflits ligne-vide avec ruff format / flake8 E305 déclenchés par publish.sh, absent de `pdm run check`)
- README.md : badges et `pip install` → `check-mysql-nagios`
- check_mysql/__init__.py : version 0.2.0 (`pdm bump minor` via publish.sh)

### Comportements obtenus

- `pip install check-mysql-nagios==0.2.0` depuis PyPI vérifié dans un venv vierge : `check_mysql --version` → 0.2.0, les 20+ commandes présentes (dont `security` de #957)
- Workflow GitHub `publish.yml` opérationnel : déclenchement manuel (choix du bump), secret `PYPI_TOKEN` provisionné par l'utilisateur, pas de déclenchement sur tag donc pas de double publication avec le publish local
- TestPyPI abandonné (redondant : `twine check` + install wheel en venv ; le bump de publish.sh rendrait la version testée ≠ publiée)

### Incidents résolus en route

1. `publish.sh` run 1 : échec flake8 E305 — docformatter vs ruff format → exclusions pyproject (précédent `exceptions.py`)
2. Upload 403 : `~/.pypirc` a `username=luxyluxe` alors qu'un API token exige `__token__` → injection `TWINE_USERNAME=__token__` (le workflow CI était déjà correct) — ⚠️ corriger `~/.pypirc` pour les prochains publishes locaux
3. Upload 400 : nom `check-mysql` refusé (similarité avec `checkmysql`) → repli `check-mysql-nagios` prévu par la carte ; upload final via `twine` puis cérémonie git de publish.sh reproduite à la main (commit release, tag, push --tags, clean)

### Garde-fous

- Pipeline complet vert avant publication : 27 étapes de publish.sh — gates (isort, format, docformatter, pyright strict 0 erreur, flake8, interrogate, refurb, lint, vulture), pytest+coverage, metrics-gate (cliquet), smoke CLI, E2E serveur MySQL local, gate SonarCloud PASSED
- `twine check` PASSED sur sdist + wheel avant chaque upload
---

[← retour à ci](index.md) · [voir log](../log/2026-07-04.md)
