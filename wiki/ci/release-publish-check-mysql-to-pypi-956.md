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

- **Nom `check-mysql` libre sur PyPI** (404 sur l'API JSON) — pas besoin de nom alternatif.
- **Métadonnées `pyproject.toml` complètes** : description, licence MIT (+ fichier LICENSE), classifiers, keywords, URLs, `requires-python >=3.10`. Auteur corrigé : `ldvchosal/ldvchosal@github.com` → `lduchosal/lduchosal@users.noreply.github.com` (décision utilisateur, pas d'email réel public).
- **Build OK** : `pdm build` produit sdist + wheel, `twine check` PASSED sur les deux.
- **Wheel testée dans un venv vierge** : installation propre, `check_mysql --help` fonctionne (20+ commandes). Artefacts de test supprimés de `dist/` ensuite.
- **Credentials présents** : `~/.pypirc` (mode 600) avec sections `[pypi]` et `[testpypi]`.
- **Pipeline canon** : `./publish.sh` (gates qualité → smoke → e2e serveur local → SonarCloud si token → `pdm bump patch` → `pdm build` → `pdm publish` → commit + tag `check-mysql-<version>` + push). TestPyPI abandonné : redondant avec `twine check` + test wheel en venv, et le bump de version rendrait la version testée ≠ publiée.

### Bloqué sur (décision utilisateur : publier après review)

1. #951 (backport health) encore en `doing` — un autre agent modifie activement l'arbre.
2. Review utilisateur des cartes en `review`, puis commit de l'arbre (publish.sh exige un arbre propre au départ et pousse sur GitHub à la fin).

### Reste à faire une fois l'arbre commité

- `./publish.sh --quality` puis `./publish.sh` complet (choisir `--patch` → 0.1.1 ou `--minor` → 0.2.0 pour la première release publique).
- Vérifier la page PyPI après publication + `pip install check-mysql` de contrôle.
---

[← retour à ci](index.md) · [voir log](../log/2026-07-04.md)
