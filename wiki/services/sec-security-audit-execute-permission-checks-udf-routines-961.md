---
id: 961
title: "SEC / Security audit - execute permission checks (UDF, routines)"
status: todo
who: "Claude"
due_date: 
classified_at: 2026-07-04T12:20:05
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

[← retour à services](index.md) · [voir log](../log/2026-07-04.md)
