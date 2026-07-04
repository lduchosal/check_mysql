---
id: 952
title: "BUG / init : CREATE USER échoue — % du host scope interprété par PyMySQL (unsupported format character)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T10:59:24
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: core
section_title: "Core (config, connexion, client, nagios)"
---

# #952 — BUG / init : CREATE USER échoue — % du host scope interprété par PyMySQL (unsupported format character)

Rapporté par l'utilisateur lors d'un run réel de `check_mysql init` :

    Create the monitoring user on the server now? [y/N]: y
    ERROR: could not create the monitoring user: unsupported format character ''' (0x27) at index 37

## Cause

PyMySQL interpole les paramètres de `cursor.execute(query, args)` avec l'opérateur `%` de Python. La requête paramétrée

    CREATE USER IF NOT EXISTS 'nagios'@'%' IDENTIFIED BY %s

contient un `%` littéral (le host scope `'%'`) : `%'` est lu comme un spécificateur de format invalide → ValueError à l'index 37, avant même d'atteindre le serveur.

Le GRANT n'est pas touché (exécuté sans args → pas d'interpolation), ni le SQL affiché.

## Correctif attendu

- Doubler le `%` littéral (`%%`) dans la seule requête paramétrée (CREATE USER) de core/provisioning.py
- Test de régression qui simule l'interpolation PyMySQL (`query % (args,)`) et vérifie que le compte rendu final contient bien 'user'@'%'
- pdm run check vert


---

## Résolution

### Modifications

- check_mysql/core/provisioning.py : dans monitoring_user_statements, le compte de la requête paramétrée (CREATE USER … IDENTIFIED BY %s) double désormais les % littéraux (`'nagios'@'%%'`) — PyMySQL rend les requêtes paramétrées avec l'opérateur % de Python. Le GRANT (exécuté sans args, donc sans interpolation) garde un % simple, tout comme le SQL affiché.
- tests/unit/test_provisioning.py : test de régression simulant l'interpolation PyMySQL (`query % args` → `'nagios'@'%' IDENTIFIED BY 'pw'`) + test que le GRANT garde un % simple.

### Comportements obtenus

- La création du user monitoring depuis `check_mysql init` fonctionne : la requête atteint le serveur au lieu d'échouer côté client sur « unsupported format character ''' (0x27) at index 37 »
- Vérifié par simulation exacte du mécanisme PyMySQL : raw `'nagios'@'%%' IDENTIFIED BY %s` → rendu `'nagios'@'%' IDENTIFIED BY '…'`

### Garde-fous

- pdm run check : VERT (103 tests, pyright strict 0, interrogate 100 %, metrics-gate PASS, couverture 99.4 %)
- Snapshot enregistré dans doc/quality-history.csv
---

[← retour à core](index.md) · [voir log](../log/2026-07-04.md)
