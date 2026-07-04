---
id: 957
title: "SEC / Report over-privileged MySQL accounts"
status: doing
who: "Claude"
due_date: 
classified_at: 2026-07-04T11:22:31
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: services
section_title: "Services (checks)"
---

# #957 — SEC / Report over-privileged MySQL accounts

# SEC / check_mysql : détecter et rapporter les comptes trop puissants

## Contexte

check_mysql sait vérifier ping, ratios, counters, longrunning, openfiles, sql.
Il manque un contrôle de sécurité sur les comptes MySQL/MariaDB : des comptes
sur-privilégiés ou mal configurés passent inaperçus jusqu'à l'incident.

## Objectif

Nouvelle commande `security` (pattern cli/core/services identique aux autres checks)
qui inspecte `mysql.user` / `information_schema` et rapporte les comptes à risque
au format Nagios (OK / WARNING / CRITICAL + perfdata).

## Détections attendues

- Privilèges globaux dangereux : `ALL PRIVILEGES ON *.*`, `SUPER`, `GRANT OPTION`,
  `FILE`, `PROCESS`, `SHUTDOWN` (hors comptes système attendus)
- `root` (ou équivalent) accessible depuis un host distant (autre que `localhost`/`127.0.0.1`/`::1`)
- Comptes avec host wildcard `%`
- Comptes anonymes (user vide)
- Comptes sans mot de passe / `authentication_string` vide

## Comportement Nagios

- OK : aucun compte à risque
- WARNING / CRITICAL : seuils sur le nombre de comptes à risque (`--warning`, `--critical`,
  cohérents avec les autres commandes), liste des comptes fautifs dans la sortie
- Perfdata : compteur par catégorie de détection

## Contraintes

- Whitelist configurable dans `check_mysql.ini` (comptes système/attendus à exclure)
- Le compte utilisé par le plugin n'a besoin que de `SELECT` sur `mysql.user` —
  documenter le GRANT minimal dans le README
- Tests unitaires sans serveur MySQL (mock client Protocol, fixtures), test e2e optionnel
- `pdm run check` vert (pyright strict, interrogate, metrics-gate…)
---

[← retour à services](index.md) · [voir log](../log/2026-07-04.md)
