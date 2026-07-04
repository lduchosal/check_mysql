---
id: 960
title: "SEC / Security audit - password checks (weak, legacy, policy)"
status: todo
who: "Claude"
due_date: 
classified_at: 2026-07-04T12:20:05
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: services
section_title: "Services (checks)"
---

# #960 — SEC / Security audit - password checks (weak, legacy, policy)

# SEC / security : checks « password security »

Étendre la commande `security` (#957) sur la robustesse des mots de passe.

## Détections

- Plugin d'authentification legacy : `mysql_native_password` (SHA1 non salé),
  hash pré-4.1 court (CIS 4.7) — recommander `caching_sha2_password`/`ed25519`
- Mots de passe faibles : wordlist offline (à la MySQLTuner `basic_passwords.txt`)
  comparée aux hashes `mysql_native_password` uniquement — les hashes salés
  (`caching_sha2_password`) ne sont pas testables offline, le documenter honnêtement
- Politique absente : composant/plugin `validate_password` non installé ou désactivé
- Expiration : `default_password_lifetime = 0` et comptes avec `password_lifetime` illimité

## Contraintes

- Wordlist embarquée courte (top ~500) ou chemin configurable `[security] wordlist = …` ;
  test purement offline sur les hashes déjà lus — JAMAIS de tentatives de connexion
- Catégories distinctes dans la sortie (`weak password`, `legacy auth`, `no policy`)
- README § Security Audit Semantics : retirer ces points des « Known limits »
---

[← retour à services](index.md) · [voir log](../log/2026-07-04.md)
