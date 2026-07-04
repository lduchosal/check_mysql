---
id: 961
title: "SEC / Security audit - execute permission checks (UDF, routines)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T12:34:18
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: services
section_title: "Services (checks)"
---

# #961 — SEC / Security audit - execute permission checks (UDF, routines)

# SEC / security : checks « execute permission security »

Étendre la commande `security` (#957) sur les vecteurs d'exécution de code.

## Détections

- FILE + `secure_file_priv` vide : lecture/écriture de fichiers arbitraires (déjà flaggé
  à distance ; croiser avec la variable pour ajuster la sévérité)
- Écriture sur le schéma `mysql` (INSERT/UPDATE sur mysql.func & co) : installation d'UDF
  → escalade de privilèges
- `CREATE ROUTINE` / `ALTER ROUTINE` / `EXECUTE` globaux sur des comptes applicatifs
- `CREATE USER`, `RELOAD`, `EVENT`, `TRIGGER` hors comptes admin (CIS 5.6/5.7)

## Contraintes

- Colonnes *_priv de mysql.user déjà chargées : la plupart des critères s'ajoutent dans
  `_account_checks` ; mysql.func/global_grants demanderaient une requête en plus (phase 2)
- Distinguer sévérité locale vs distante comme pour les privilèges actuels
- README § Security Audit Semantics + mapping CIS

---

## Résolution

### Modifications
- check_mysql/services/security_service.py : `_DANGEROUS_PRIV_COLUMNS` étendu — CREATE USER,
  RELOAD, CREATE ROUTINE, ALTER ROUTINE, EVENT, TRIGGER (en plus de SUPER/GRANT/FILE/PROCESS/SHUTDOWN)
- README.md § Security Audit Semantics : ligne « remote dangerous privileges » complétée
- tests/unit/test_security_service.py : TestExtendedPrivilegeFindings (CREATE USER, routines/events, local non flaggé)

### Comportements obtenus
- Ces privilèges d'exécution/administration sont signalés `remote privileges (…)` uniquement
  sur les comptes joignables à distance (comptes locaux restent silencieux, cohérent avec le modèle)
- S'ils sont tous présents avec les autres, l'agrégat reste `ALL PRIVILEGES`
- Hérite automatiquement de la trace `-vvv` (critère « remote privileges » par compte)

### Garde-fous
- pdm run check vert (palier 3, 243 tests, couverture 99,64 %), pdm run test-e2e 25/25
- Vérifié contre le serveur local : `MYSQL OK - 0 risky accounts out of 16 audited`

### Hors périmètre (reste à faire, cartes dédiées)
- Écriture directe sur le schéma `mysql` / mysql.func (UDF) : nécessite une requête mysql.db
  supplémentaire → couvert par #959 (database checks)
- Croisement FILE × `secure_file_priv` (variable serveur) → #959
---

[← retour à services](index.md) · [voir log](../log/2026-07-04.md)
