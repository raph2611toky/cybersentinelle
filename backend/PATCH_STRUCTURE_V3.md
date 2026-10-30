# SAFIDIKO — patch de structure V3

Ce ZIP est un **patch différentiel** à extraire directement dans `backend/` : il n'a **pas** de dossier `backend/` parent.

## Mise en place

```bash
cd /home/raph/competitions/cyber_sentinelle/backend
cp -a config config_backup_before_v3
unzip -o ~/Downloads/SAFIDIKO_patch_structure_v3.zip -d .
bash APPLY_PATCH.sh
# Ajouter SWAGGER_PASSWORD dans .env (minimum 12 caractères), puis :
python manage.py check
python -m pytest -q
python manage.py runserver
```

`APPLY_PATCH.sh` vérifie que les anciennes références `config.*` sont absentes du code Python du projet, puis supprime les cinq fichiers obsolètes de `config/` : `editor_urls.py`, `exceptions.py`, `responses.py`, `middleware.py`, `swagger.py`. L'archive ne touche pas `.env`, aux données ni aux migrations.

## Config minimal

`config/` : `__init__.py`, `settings.py`, `urls.py`, `asgi.py`, `wsgi.py`, **`views.py`**.

- **Entrée unique** : `config/urls.py`, avec les routes éditoriales incluses depuis `apps/editor/urls.py` (comme les autres `apps/*/urls.py`). Aucun routeur DRF.
- **Helpers HTTP** : `helpers/api/{swagger.py,swagger_access.py,swagger_views.py,responses.py,exceptions.py,middleware.py}`.
- **Pages HTML** : `templates/swagger_login.html` (seule page HTML utilisée par le portail de documentation).
- **Media** : `MEDIA_ROOT` et `MEDIA_URL` dans settings ; `static()` uniquement en `DEBUG=True` ; en production, confier `/media/` à Nginx ou stockage adapté. Le lien `_url` est une URL absolue et vient du storage.
- **Swagger** : `GET /api/docs/`, `GET /api/redoc/`, `GET /api/swagger.json` et `.yaml`, même contrôle par un cookie signé court. `GET /api/swagger/login/` présente un formulaire *indépendant* de Django Admin ; `POST /api/swagger/unlock/` retourne du JSON, nécessite CSRF ; `POST /api/swagger/logout/` termine l'accès.
- **Sécurité** : `SWAGGER_PASSWORD` doit être défini et contenir au moins 12 caractères, sinon documentation verrouillée (503). La protection Swagger ne donne aucun droit éditorial : l'API editor exige toujours les permissions Django staff + CSRF.

## Note de confidentialité

Le formulaire de connexion Swagger est une page HTML. Les APIs métier et les endpoints Swagger d'authentification retournent des erreurs JSON ; les réponses HTTP 304 / HEAD sont sans corps.

## Production

`SWAGGER_ENABLED=false` est le défaut de production. Si `true`, HTTPS et rate limiting reverse-proxy sont fortement recommandés. Publier le schéma Swagger expose les chemins des endpoints éditoriaux, même si ces endpoints restent protégés.

Ne jamais exposer le dossier `media/` comme un espace privé : il ne doit contenir que des images éditoriales autorisées, jamais des témoignages ni pièces de mineurs.

Exemple de configuration des médias de production : `deployment/nginx_media.conf.example`. Adaptation nécessaire à votre domaine et à votre installation.
