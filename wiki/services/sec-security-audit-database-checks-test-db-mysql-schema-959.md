---
id: 959
title: "SEC / Security audit - database checks (test db, mysql schema)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T12:20:04
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: services
section_title: "Services (checks)"
---

# #959 — SEC / Security audit - database checks (test db, mysql schema)

# SEC / security : checks « database security »

Étendre la commande `security` (#957) au-delà de mysql.user : bases et schémas.

## Détections

- Base `test` présente et grants `test\_%` dans mysql.db (mysql_secure_installation, CIS)
- Grants non-admin sur le schéma `mysql` (SELECT/INSERT/UPDATE/DELETE/CREATE/DROP — CIS 5.1)
- Variables serveur à risque (INFO) : `local_infile = ON`, `secure_file_priv` vide,
  absence de `skip_networking`/`bind-address` restrictif quand aucun compte distant n'existe

## Contraintes

- Nécessite de nouvelles requêtes client (`SHOW DATABASES`, `SELECT ... FROM mysql.db`,
  variables déjà disponibles via `get_global_variables()`) → étendre MySQLClientProtocol + mock
- GRANT minimal à documenter (SELECT sur mysql.db) — rester en lecture seule
- README § Security Audit Semantics + check_mysql.ini.example à jour

---

## Clôture (0.2.5)

Fermé sans implémentation pour stabiliser la version. Les checks serveur (base `test`,
grants sur le schéma `mysql`, `validate_password`, `local_infile`, `secure_file_priv`)
nécessitent de nouvelles requêtes client + une sémantique « server-wide » distincte de
l'audit par compte. À rouvrir en carte dédiée si le besoin se confirme.
---

[← retour à services](index.md) · [voir log](../log/2026-07-04.md)
