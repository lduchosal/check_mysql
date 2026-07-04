---
id: 958
title: "SEC / Security audit - account checks (root rename, TLS, stale)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-04T12:20:03
classified_by: "key:f156efe4-abe2-4a76-affc-d07705fb5c4f"
section: services
section_title: "Services (checks)"
---

# #958 — SEC / Security audit - account checks (root rename, TLS, stale)

# SEC / security : checks « account security »

Étendre la commande `security` (#957) avec les critères CIS orientés comptes :

## Détections

- `root` non renommé (CIS 4.5) — présence d'un compte nommé littéralement `root`
- Comptes par défaut / d'exemple restants (ex. `debian-sys-maint` inutilisé, comptes de démo)
- Comptes expirés mais non supprimés (`password_expired = Y` de longue date)
- TLS par compte : `ssl_type` vide (aucun REQUIRE SSL/X509) alors que le compte est
  joignable à distance et que `require_secure_transport` est OFF

## Contraintes

- Même architecture que #957 : lignes mysql.user déjà chargées par `get_user_accounts()`,
  nouveaux critères dans `_account_checks` (catégorie + description), trace `-vvv` gratuite
- Chaque nouveau critère documenté dans README § Security Audit Semantics (+ mapping CIS)
- Attention au bruit : critères info/opt-in si besoin, whitelist `[security] allow` inchangée

---

## Avancement (increment security-audit v2)

**Livré** : critère « password expired » (`password_expired = Y`) dans `_account_checks`,
tracé `-vvv`, testé, documenté (README table + CIS 4.x).

**Reste** : root non renommé (CIS 4.5, tension avec « install saine = OK »), comptes par
défaut inutilisés, TLS par compte (`ssl_type`). Carte maintenue en todo.

---

## Clôture (0.2.5)

Fermé : critère « password expired » livré (v2). Root-rename (CIS 4.5) et TLS par
compte descopés — feraient warner toute install standard (contradiction avec le
principe « install saine = OK »). À rouvrir via une carte opt-in « strict CIS » si besoin.
---

[← retour à services](index.md) · [voir log](../log/2026-07-04.md)
