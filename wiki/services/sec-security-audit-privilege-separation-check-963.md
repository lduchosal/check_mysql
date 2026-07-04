---
id: 963
title: "SEC / Security audit - privilege separation check"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T12:20:06
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: services
section_title: "Services (checks)"
---

# #963 — SEC / Security audit - privilege separation check

# SEC / security : check « privilege separation »

Étendre la commande `security` (#957) sur la séparation des rôles (app / migration / admin).

## Détections

- Comptes applicatifs avec DDL global (CREATE/DROP/ALTER) en plus du DML :
  un compte app ne devrait pas pouvoir modifier le schéma (séparation app vs migration)
- `GRANT OPTION` hors comptes admin (CIS 5.8) : personne d'autre ne doit pouvoir
  redistribuer des privilèges
- Comptes cumulards : admin ET utilisé comme compte applicatif (heuristique :
  privilèges admin + connexions applicatives, ou DML large multi-schémas)
- WITH GRANT OPTION en cascade : privilèges re-délégués par des non-admins

## Contraintes

- S'appuyer sur `[security] admins` (carte « all privileges ») pour la notion d'admin attendu
- Critères heuristiques → sévérité modérée / catégories dédiées pour whitelister finement
- README § Security Audit Semantics + mapping CIS

---

## Avancement (increment security-audit v2)

**Livré** : GRANT OPTION reste signalé sur les comptes distants hors `[security] admins`
(fondation « redistribution de privilèges par des non-admins » de la carte).

**Reste** : comptes applicatifs avec DDL global (heuristique), comptes cumulards admin+app,
cascade WITH GRANT OPTION. Dépend de l'inventaire admin (#962). Carte en todo.

---

## Clôture (0.2.5)

Fermé : GRANT OPTION hors admins déjà couvert via `[security] admins` (v2). Heuristiques
restantes (DDL sur comptes applicatifs, comptes cumulards admin+app) descopées — trop de
faux positifs pour un plugin de monitoring.
---

[← retour à services](index.md) · [voir log](../log/2026-07-04.md)
