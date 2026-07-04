# check_mysql

Plugin Nagios pour MySQL/MariaDB (connexion directe PyMySQL ou tunnel SSH via sshtunnel).
Architecture cli/core/services pillée de check_msdefender — voir README.md.

## Qualité (standard lduchosal)

- `pdm run check` doit être vert avant toute review : isort, format-check, lint (ruff),
  flake8 (+docstrings), pyright **strict** (package uniquement, stubs dans `typings/`),
  interrogate ≥ 95 %, refurb, vulture, pytest+coverage, `metrics-gate`.
- Gate bloquant + cliquet best-ever : `scripts/quality_metrics.py` vs `doc/quality-history.csv`
  (procédure des paliers dans `doc/code-quality.md`). Ne JAMAIS détendre un seuil.
- Les tests tournent sans serveur MySQL (mock client Protocol, fakes, CliRunner).
- Gate vert → `pdm run metrics-record` puis resserrer un seuil.

Les tâches de ce projet sont gérées sur Kenboard (https://www.kenboard.2113.ch) via le CLI `ken`.

## Ken — mise en place

- Le CLI est installé dans le venv du projet : `.venv/bin/ken`
- La config est dans `.ken` (gitignored, mode 600, contient le token API — ne jamais le committer ni afficher son contenu)

## Ken — méthodologie de travail

Workflow : `todo → doing → review → groom → done`

L'agent gère `todo → doing → review` puis le groom wiki. **Seul l'utilisateur passe une tâche de `review` à `done`** — ne jamais marquer une tâche `done` soi-même.

### La boucle

1. **Lire la queue** et choisir une tâche ; annoncer le choix et la raison avant de commencer :

       ken list --who Claude --status todo

2. **Passer en doing** avant de toucher au code (évite qu'un autre agent prenne la même carte) :

       ken move <id> --to doing

3. **Implémenter** : lire le code concerné, faire le changement, passer les quality gates (lint, tests). Ne pas ajouter de features ni refactorer au-delà de ce qui est demandé.

4. **Mettre à jour la description AVANT de passer en review** : conserver la description originale verbatim, puis ajouter un bloc résolution :

       ---

       ## Résolution

       ### Modifications
       - chemin/fichier.py : résumé en une ligne

       ### Comportements obtenus
       - ce qui fonctionne maintenant

       ### Garde-fous
       - gates exécutés et leur résultat

5. **Passer en review** :

       ken move <id> --to review

6. **Classifier pour le wiki** (sinon la tâche est invisible pour `ken wiki sync`) :

       ken wiki groom                 # liste les sections disponibles
       ken wiki groom <id> <section>  # section la plus profonde qui matche

### Descriptions multi-lignes

⚠️ Ne jamais utiliser `--desc "ligne1\nligne2"` — le `\n` reste littéral et casse le markdown. Idiome recommandé : écrire le corps dans un fichier temporaire puis :

    ken update <id> --desc-file /tmp/ken-<id>.md

Alternative : `ken update <id> --desc - <<'EOF' ... EOF` (stdin). Ne jamais passer `--desc` et `--desc-file` ensemble.

### Convention de titres

Format obligatoire `MODULE / Titre` (pas de `<` ni `>`) :

    BUG / Remove user fails with 403
    SEC / Sanitize reflected data in onboarding
    AGENT / CLI / Sync tasks to folder

Modules courants : `AUTH`, `BUG`, `CLEAN`, `SEC`, `UI`, `DOC`, `QUALITY`, `AGENT`, `ONBOARDING`, `FIX`. Titres courts — les détails vont dans la description.

### Sortie et filtres

- Utiliser les filtres natifs (`--who`, `--status`), jamais de pipe vers jq/awk
- Sortie texte par défaut (lisible directement) ; `--json` uniquement quand la sortie doit être parsée (ex. `ken add --json` pour récupérer l'id créé)

### Commandes de référence

    ken list --who Claude --status todo
    ken show <id>
    ken add "MODULE / Titre" --desc "..." --who Claude --status todo
    ken move <id> --to doing|review
    ken update <id> --desc-file corps.md
    ken polish <id>        # tâches paintbrush (SVG) : prépare la reformulation
    ken show <id> --save-attachement out.svg
    ken help               # guide agent complet
