---
id: 964
title: "PUBLISH / Quiet toutes les étapes, output complet si erreur"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T12:32:12
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: ci
section_title: "CI & Publication"
---

# #964 — PUBLISH / Quiet toutes les étapes, output complet si erreur

reduce verbosity of tests and test e2e in publish.sh. Le output pollue gravement le contexte du modèle qui publie. Vérifie toutes les étapes du publish et rend-les quiet, sauf si une erreur survient : alors le output doit être complet pour permettre un debug immédiat.

---

## Résolution

### Modifications
- publish.sh : `run_command` capture stdout+stderr de chaque étape dans un fichier temporaire (`mktemp`) ; sur succès l'output est jeté, sur échec il est rejoué intégralement (commande + output complet) avant l'abort
- publish.sh : en-têtes d'étape réduits de 5 lignes (cadre `═══`) à une ligne `[N/27] Titre`
- publish.sh : le gate SonarCloud (`scripts/sonar_gate.py`, appelé en direct avec son polling visible) passe désormais par `run_command` — même sémantique quiet/replay

### Comportements obtenus
- Publish vert : 2 lignes par étape (en-tête + ✓), plus aucun output de pytest `-v`, coverage, pdm, git — toutes les étapes couvertes, y compris tests, e2e et SonarCloud
- Étape en échec : la commande exacte puis son stdout+stderr complets sont affichés, puis abort (exit 1) — debug immédiat sans relancer
- Les scripts pdm (`test`, `test-e2e` avec `-v`) sont inchangés : la verbosité reste disponible en usage interactif et dans le replay d'erreur

### Garde-fous
- `sh -n publish.sh` : OK
- Harnais (fonctions extraites, commande bruyante succès/échec) : succès silencieux, échec rejoue stdout+stderr et exit 1 — vérifié
- `pdm run check` : rouge sur `format-check` uniquement, causé par 3 fichiers SEC en WIP d'une session parallèle (security_service.py, test_config.py, test_security_service.py) — non liés à cette carte ; publish.sh n'est couvert par aucun gate Python. Fichiers de la session parallèle laissés intacts
- Validation réelle du flux complet à la prochaine release (`publish.sh` s'auto-teste à l'usage)
---

[← retour à ci](index.md) · [voir log](../log/2026-07-04.md)
