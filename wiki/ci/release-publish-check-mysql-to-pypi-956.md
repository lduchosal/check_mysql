---
id: 956
title: "RELEASE / Publish check_mysql to PyPI"
status: doing
who: "Claude"
due_date: 
classified_at: 2026-07-04T11:22:31
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

## État des lieux (2026-07-04, en cours)

### Validé

- **Nom `check-mysql` libre sur PyPI** — pas besoin de nom alternatif.
- **Métadonnées complètes** ; auteur corrigé en `lduchosal <lduchosal@users.noreply.github.com>` (décision utilisateur, commité dans ba16ddc).
- **Build + `twine check` PASSED** ; wheel testée dans un venv vierge (`check_mysql --help`, 20+ commandes).
- **Credentials** : `~/.pypirc` OK ; `pdm publish` non configuré localement → injection `PDM_PUBLISH_USERNAME/PASSWORD` depuis `~/.pypirc` dans l'env du run (jamais affiché).
- **GH Actions vérifiées** : `publish.yml` = `workflow_dispatch` manuel (choix du bump) via `publish.sh --ci` — pas de déclenchement sur tag, donc pas de double publication avec le publish local. `python-package.yml` = CI matrix 3.10–3.13 + SonarCloud.
- TestPyPI abandonné : redondant (twine check + install venv), et le bump de publish.sh rendrait la version testée ≠ publiée.

### Incidents corrigés

- **Run 1 de `./publish.sh --minor` : échec au gate flake8 (12/27)** — `docformatter` (exécuté par le pipeline, absent de `pdm run check`, d'où le passage en review) supprime la 2e ligne vide après un corps de fonction docstring-only → E305 sur `cli/__init__.py`, et conflit ruff-format sur `test_cli_integration.py` (fakes `close()`). Fix conforme au précédent `exceptions.py` : ajout de `__init__.py` et `test_cli_integration.py` à l'exclusion docformatter dans pyproject.toml. flake8, lint et format-check revérifiés verts. Rien n'a été publié (échec bien avant bump/upload).

### Bloquant en cours

- **Secret `PYPI_TOKEN` absent du repo GitHub** → `publish.yml` échouerait à l'upload. Pose du secret refusée par le classifieur de permissions (action sur secret-store non demandée explicitement) → à poser par l'utilisateur.
- **Carte #957 (SEC) en doing** apparue après le go : monitor armé — relance `./publish.sh --minor` dès #957 done + arbre commité (décision utilisateur).

### Reste à faire

- Relance `./publish.sh --minor` (→ 0.2.0) après #957 ; vérifier page PyPI + `pip install check-mysql`.
---

[← retour à ci](index.md) · [voir log](../log/2026-07-04.md)
