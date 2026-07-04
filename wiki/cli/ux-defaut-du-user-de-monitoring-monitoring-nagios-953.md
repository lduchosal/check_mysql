---
id: 953
title: "UX / Défaut du user de monitoring : monitoring → nagios"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T10:59:33
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: cli
section_title: "CLI (commandes Nagios)"
---

# #953 — UX / Défaut du user de monitoring : monitoring → nagios

Demande utilisateur : changer le user de monitoring par défaut de `monitoring` à `nagios` partout dans l'expérience init et la doc.

## Portée

- Template par défaut (DEFAULT_CONFIG_TEMPLATE) et section SSH commentée : user = nagios
- Prompts du setup guidé : « Monitoring user [nagios] », « SSH user [nagios] »
- SQL affiché en mode --yes : CREATE USER 'nagios'@'%'
- README (exemples de config, SQL du user, section tunnel) et check_mysql.ini.example
- Tests ajustés (défauts attendus)


---

## Résolution

### Modifications

- check_mysql/core/config.py : DEFAULT_CONFIG_TEMPLATE `user = nagios`, section SSH commentée `#user = nagios`
- check_mysql/cli/commands/init.py : prompts « Monitoring user [nagios] » et « SSH user [nagios] », SQL du mode --yes sur 'nagios'
- README.md : exemples de config (directe et tunnel), SQL du user de monitoring → 'nagios'
- check_mysql.ini.example : user = nagios (mysql + ssh commenté)
- tests : défauts attendus ajustés (unit config + intégration init)

### Comportements obtenus

- Toute l'expérience init (guidée et --yes), la doc et les exemples utilisent `nagios` comme user de monitoring par défaut ; Enter-through crée un user 'nagios'@'%'

### Garde-fous

- pdm run check : VERT (103 tests, metrics-gate PASS) — même run que #952
- Smoke : `check_mysql init --yes` affiche CREATE USER 'nagios'@'%' et écrit user = nagios
---

[← retour à cli](index.md) · [voir log](../log/2026-07-04.md)
