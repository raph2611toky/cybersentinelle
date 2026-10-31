# SAFIDIKO — Seed référentiel au déploiement

Ce patch ne comprend **que** un `Jenkinsfile` et une commande Django plus son test.

- `backend/apps/core/management/commands/seed_defaults.py`: crée **uniquement** les lignes absentes, sans modifier les valeurs existantes : `Langue(fr, mg)`, six `Sujet` bilingues et une `Source` de type `REFERENTIEL_INTERNE` (sans faux URL officiel).
- `backend/tests/test_seed_defaults.py`: tests d’idempotence et de non-écrasement des modifications d'administration.
- `Jenkinsfile`: dans la branche `backend` et `rebuild`, exécute `python manage.py seed_defaults --no-color` **après** `python manage.py migrate --noinput` et **avant** le redémarrage Django. Arrêt du déploiement si le seed échoue. Aucune action sur la branche `dashboard` uniquement.

Pour test manuel :

```bash
python manage.py migrate --noinput
python manage.py seed_defaults
python manage.py seed_defaults  # aucune création supplémentaire
pytest -q tests/test_seed_defaults.py
```

Pour serveur déjà déployé (une fois, sans reconstruire) :

```bash
docker exec safidiko-backend python manage.py seed_defaults
```

N'introduit **aucune** donnée fictive de victime, aucun compte, numéro d'urgence, lien officiel, profil voix TTS, vidéo ou Tantara. Ces contenus doivent être renseignés/contrôlés par les administrateurs ; l'absence de données réelles ne doit jamais être masquée par de faux contacts.

**Attention au pipeline** : le `Jenkinsfile` fourni reprend le pipeline SAFIDIKO Docker/Jenkins accessible dans l'archive `SAFIDIKO_Docker_Jenkins_Projet_Complet.zip`. Si le `Jenkinsfile` de ton dépôt a évolué depuis, ne remplace pas d'autres modifications : copie uniquement le bloc `docker run ... python manage.py seed_defaults --no-color` après sa commande `migrate`.
