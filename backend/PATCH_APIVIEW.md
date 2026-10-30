# Patch différentiel SAFIDIKO — APIView uniquement

Ce ZIP est un **patch**, pas un backend complet. Il s'applique sur le projet issu de `backend(20261030-112942).zip` et ne contient que des fichiers modifiés/ajoutés (plus ce guide).

## Installer le patch dans ton dossier existant

```bash
cd /home/raph/competitions/cyber_sentinelle
# Préalable : faire une copie de sauvegarde ou un commit Git.
unzip -o /chemin/vers/SAFIDIKO_patch_APIView_uniquement.zip -d .
cd backend
source .venv/bin/activate
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest -q
```

Aucun modèle, migration ou fichier `.env` n'a été modifié. La base SQLite/MySQL et les données existantes restent intactes.

## Architecture des vues

- `apps/*/views.py` : endpoints publics GET, plus `apps/core/views.py` pour les APIView d'édition Langue.
- `apps/*/editor_views.py` : APIView éditoriales individuelles (six opérations par modèle).
- `apps/*/swagger.py` : décorateurs Swagger explicites et séparés.
- `apps/core/editor_service.py` : services CRUD et permissions par modèle, sans vue générique ni ViewSet.
- `apps/core/editor_swagger.py` : schémas communs de réussite, pagination, erreurs et paramètres multipart manuels.
- `apps/publication/editor_views.py` : validation, liste, détail, publication et rollback par opérations séparées.

## Changement d'URLs éditoriales

Chaque ressource (`languages`, `topics`, `visuals`, `stories`, `nodes`, `options`, `sources`, `resources`, `questions`) possède :

| Méthode | Chemin relatif à `/api/editor/` | Réponse |
|---|---|---|
| GET | `<resource>/` | 200 JSON paginé |
| GET | `<resource>/<uuid>/` | 200 JSON |
| POST | `<resource>/create/` | 201 JSON |
| PUT | `<resource>/<uuid>/update/` | 200 JSON |
| PATCH | `<resource>/<uuid>/partial-update/` | 200 JSON |
| DELETE | `<resource>/<uuid>/delete/` | 200 JSON `{"deleted":true}` |

Les anciennes URL d'écriture du ViewSet ne sont plus utilisées. Adapte les clients qui les appelaient.

Les versions continuent avec `/api/editor/releases/`, `/<uuid>/`, `/validate/`, `/publish/`, `/<uuid>/rollback/`.

## Formats et droits

Les succès CRUD sont JSON ; les erreurs utilisent `{"error":{"code":"...","message":"...","fields":{...}}}` (champs facultatifs). Les réponses HEAD et 304 ne contiennent normalement pas de corps.

L'édition nécessite `is_staff=True`, une authentification session Django et la permission Django du modèle. L'API `/api/session/` utilisée par des visiteurs anonymes a été supprimée afin de respecter le cahier des charges zéro donnée joueur ; les sessions admin restent inchangées. L'API publique `/api/v1/` est toujours en lecture seule.

Les uploads `Visuel` utilisent `multipart/form-data` sur les opérations d'écriture, avec `manual_parameters` dans Swagger. Les réponses incluent maintenant `fichier_url`, `chemin_asset_url`, `visuel_heros_url` ou `visuel_url` selon le modèle.

## Tests

La syntaxe Python et la structure AST ont été vérifiées, ainsi que l'absence de ViewSet. Les tests Django et la génération réelle du schéma Swagger doivent être lancés sur Kali : les dépendances Django n'étaient pas disponibles dans l'environnement de préparation.
