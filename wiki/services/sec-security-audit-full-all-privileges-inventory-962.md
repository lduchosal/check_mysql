---
id: 962
title: "SEC / Security audit - full all-privileges inventory"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T12:20:06
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: services
section_title: "Services (checks)"
---

# #962 — SEC / Security audit - full all-privileges inventory

# SEC / security : audit « all privileges » complet

Étendre le critère ALL PRIVILEGES de la commande `security` (#957).

## Contexte

Aujourd'hui ALL PRIVILEGES n'est signalé que sur les comptes joignables à distance ;
les comptes admin locaux sont silencieux par design. Il manque un inventaire exhaustif.

## Détections

- Inventaire de TOUS les comptes ALL PRIVILEGES / équivalent admin, locaux inclus
- Liste d'admins attendus configurable : `[security] admins = root@localhost, …` —
  tout compte ALL PRIVILEGES hors liste est flaggé, même local (approche CIS « non-admin »)
- MySQL 8 : privilèges dynamiques équivalents (mysql.global_grants : SYSTEM_USER,
  ROLE_ADMIN, BACKUP_ADMIN…) et rôles (`mandatory_roles`, grants via rôles)

## Contraintes

- Nouvelle option `[security] admins` (défaut : comportement actuel, pas de régression)
- mysql.global_grants = requête supplémentaire → étendre client + mock + GRANT documenté
- Sortie : catégorie `unexpected admin` distincte, README à jour

---

## Avancement (increment security-audit v2)

**Livré** : option `[security] admins = user@host, …` (config + parsing raw, testée) qui
exempte les comptes admin attendus du seul critère « remote privileges ». Combinée au
critère existant, tout compte distant ALL PRIVILEGES / privilège dangereux hors liste est
signalé (portion « unexpected admin » distante de la carte).

**Reste** : inventaire exhaustif incluant les comptes locaux (approche CIS non-admin,
bruyante par défaut → opt-in), privilèges dynamiques MySQL 8 (`mysql.global_grants` :
SYSTEM_USER, ROLE_ADMIN…) et rôles. Carte en todo.

---

## Clôture (0.2.5)

Fermé : option `[security] admins` + détection « unexpected admin » à distance livrées
(v2). Inventaire local exhaustif (bruit) et privilèges dynamiques MySQL 8
(`mysql.global_grants`) descopés.
---

[← retour à services](index.md) · [voir log](../log/2026-07-04.md)
