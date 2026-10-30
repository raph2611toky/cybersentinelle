# SAFIDIKO — backend éditorial et API publique

Cette refonte ajoute l'édition web à l'ancien backend de diffusion. Elle reprend les répertoires `config/`, `apps/`, `helpers/`, `media/` du django-maker fourni, sans reprendre ses secrets par défaut, son CORS universel ni ses JWT de longue durée.

## Démarrage sur une nouvelle base

Python 3.12 recommandé ; Django 5.2. Depuis le répertoire `backend` :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py bootstrap_admin --username admin --email admin@example.com
python manage.py runserver 127.0.0.1:8000
```

La commande demande et valide le mot de passe. Aucun compte ni secret partagé n'est inclus. `python manage.py createsuperuser` reste utilisable. En automatisation, `bootstrap_admin --no-input` lit `DJANGO_SUPERUSER_PASSWORD` depuis l'environnement ; cette variable ne doit pas être conservée dans le dépôt. Un compte existant n'est jamais écrasé.

- Administration : http://127.0.0.1:8000/admin/
- Swagger, après connexion staff : http://127.0.0.1:8000/api/docs/
- ReDoc : http://127.0.0.1:8000/api/redoc/
- Schéma JSON : http://127.0.0.1:8000/api/swagger.json

La base initiale ne contient pas les vraies histoires ni leurs illustrations : elles n'étaient pas présentes dans l'archive source. Les endpoints publics renvoient `503 CONTENT_NOT_PUBLISHED` tant qu'une première release n'a pas été publiée.

## Structure

| Chemin | Responsabilité |
|---|---|
| `config/settings.py` | Base de données, sessions, CSRF, CORS, médias, Swagger |
| `config/editor_urls.py` | Routes APIView explicites, aucun routeur ni ViewSet |
| `apps/core/` | Langues, permissions, réponses JSON, services CRUD communs et Swagger |
| `apps/content_api/` | Sujets, illustrations, histoires, nœuds, options |
| `apps/resources/` | Sources et ressources d'aide |
| `apps/pedagogie/` | Questions pédagogiques |
| `apps/publication/` | Validation, snapshots, publication et rollback |
| `helpers/helper.py` | Temps écoulé, URL de média, normalisation d'image |
| `media/` | Illustrations publiques, jamais des preuves ou témoignages |
| `content/releases/` | JSON publiés figés |
| `tests/` | Contrat public, graphes, droits, APIView, Swagger, CSRF, uploads et publication |

Chaque application métier possède son `admin.py` (nom reconnu par Django), ses modèles, migrations et, selon ses endpoints, serializers, vues et routes. Les modèles `User` et `Group` standards de Django sont disponibles dans l'admin : les visiteurs n'ont pas de compte `User`.

## Droits d'accès

| Surface | Accès |
|---|---|
| `/api/v1/` | Lecture publique de snapshots validés ; aucune écriture |
| `/api/editor/` | Compte actif, `is_staff=True`, permission Django par modèle et opération |
| `/admin/` | Connexion Django ; permissions par modèle |
| Documentation | Connexion staff requise, même en développement |

Un compte authentifié sans `is_staff` ne peut pas éditer. Un membre staff sans permission ne peut pas consulter les données éditoriales. Dans l'admin, créer des groupes puis attribuer `view`, `add`, `change`, `delete` selon les besoins. Les superutilisateurs ont tous les droits.

Les UUID d'objets éditoriaux sont renvoyés pour référencer les relations. Ce sont des identifiants, pas des secrets ni des autorisations. Les réponses ajoutent des objets `*_detail` / `*_details` contenant l'UUID et un libellé. Les données publiques gardent leurs slugs et clés métier. Les visiteurs ne disposent d’aucune session applicative SAFIDIKO.

## CRUD éditoriaux

Ressources disponibles sous `/api/editor/` : `languages`, `topics`, `visuals`, `stories`, `nodes`, `options`, `sources`, `resources`, `questions`.

Pour chacune :

| Verbe | URL | Opération |
|---|---|---|
| GET | `/<ressource>/` | Liste paginée, 25 éléments par page |
| POST | `/<ressource>/create/` | Création (201 JSON) |
| GET | `/<ressource>/<uuid>/` | Détail (200 JSON) |
| PUT | `/<ressource>/<uuid>/update/` | Mise à jour complète (200 JSON) |
| PATCH | `/<ressource>/<uuid>/partial-update/` | Modification partielle (200 JSON) |
| DELETE | `/<ressource>/<uuid>/delete/` | Suppression (200 `{ "deleted": true }`) |

`?page=2`, `?search=mot`, `?ordering=-updated_at` sont disponibles. La recherche porte sur les champs textuels explicitement autorisés pour chaque ressource. Les créations et modifications utilisent JSON ; pour les visuels, les opérations d’écriture utilisent `multipart/form-data` avec le champ `fichier` et des `manual_parameters` Swagger. Le fichier et les chemins d’asset disposent aussi d’un champ `*_url` en lecture.

Les validations vérifient aussi les règles de modèle sur PATCH, l'unicité et les contraintes. Les erreurs de saisie sont renvoyées sous `error.fields`. Les suppressions bloquées par des relations retournent `409 CONFLICT` ; elles ne forcent pas la suppression des objets liés. Les parents d'un nœud et d'une option ne peuvent pas être changés après création.

## Créer puis publier une histoire

1. Dans l'admin, créer les langues `fr` et `mg`, les sujets et les illustrations. Une illustration doit avoir sa licence et ses textes alternatifs, sauf si elle est décorative.
2. Créer une histoire en brouillon : slug unique libre, numéro, textes FR/MG, durée, palette, nombre de décisions et visuel héros. L'édition n'est plus limitée aux trois slugs V14.
3. Créer d'abord les fins (`ENDING`), puis les décisions (`DECISION`, poids positif) et les scènes (`SCENE`, cible obligatoire). Le nœud initial doit avoir la clé `start`.
4. Ajouter deux ou trois options à chaque décision ; cibles dans la même histoire, qualité entre 0 et 1 et ordre unique.
5. Renseigner les relectures FR/MG, la date et le rôle de validation après relecture effective, puis passer l'histoire à `APPROUVE`. Faire de même pour les ressources et questions à publier.
6. Appeler `GET /api/editor/releases/validate/`, puis `POST /api/editor/releases/publish/` avec `{"numero":"v1","journal":"Première publication"}`.
7. Consulter `/api/v1/stories/`, puis `/api/v1/stories/<slug>/`.

Les graphes complets sont vérifiés à la publication : boucle, cible étrangère, nœud inaccessible, fin absente, mauvais nombre de décisions ou options invalides empêchent la release. Une histoire incomplète peut rester en brouillon.

Les releases se consultent via `GET /api/editor/releases/` et `GET /api/editor/releases/<uuid>/`. `POST /api/editor/releases/<uuid>/rollback/` restaure une release vérifiée. La publication exige `add_versioncontenu`, le rollback `change_versioncontenu`, la consultation/validation `view_versioncontenu`.

Les modèles de release sont en lecture seule dans l'admin. Leur création, modification ou suppression arbitraire par CRUD casserait les empreintes et l'état actif. Utiliser les actions de publication ou les commandes :

```bash
python manage.py validate_public_content
python manage.py publish_content --help
python manage.py rollback_content --help
```

L'importeur `import_public_content` conserve son format historique V14 (trois histoires) pour reprendre les anciens JSON. Les nouvelles histoires se créent librement dans l'admin ou l'API éditoriale.

## Administration, CSRF et frontend

Les APIView de l’éditeur nécessitent **deux conditions indépendantes** : compte staff authentifié en session Django et permission `view/add/change/delete` du modèle. Pour tester Swagger, se connecter sur `/admin/login/`, puis fournir le cookie `csrftoken` comme en-tête `X-CSRFToken` lors des écritures. Ce mécanisme ne concerne pas la navigation publique.

Conformément au cahier des charges concours, la route `/api/session/` a été supprimée : le navigateur joue les Tantara sans compte, session applicative, progression serveur ni cookie de joueur. Le frontend utilise seulement `GET /api/v1/` ; les requêtes CORS cross-origin n’autorisent aucun envoi de cookie (`CORS_ALLOW_CREDENTIALS=False`). Les sessions Django restent nécessaires à l’administration privée.

Une classe `APIView` ne contient **qu’une seule méthode** (get, post, put, patch ou delete), chacune avec son `try/except Exception` et son décorateur Swagger importé d’un fichier `swagger.py`. Les opérations partagées sont placées dans `apps/core/editor_service.py`, pas dans un ViewSet. Django REST Framework gère automatiquement `HEAD` et `OPTIONS`.

Les erreurs 400, 403, 404, 405, 409 et 500 utilisent le format `{ "error": { "code": "...", "message": "..." } }`, avec `fields` optionnel pour la validation. Les succès CRUD sont JSON (la suppression renvoie 200, pas 204). Exceptions HTTP sans corps : `304 Not Modified` et les réponses `HEAD`.

## Médias

`MEDIA_ROOT` est `backend/media`. Les uploads API et admin acceptent PNG/JPEG/WEBP, limités à 5 Mo et 20 millions de pixels. Ils sont réencodés en PNG avec un nom aléatoire et sans métadonnées d'origine. Le format, les dimensions et le SHA-256 sont recalculés. Les fichiers ne sont pas automatiquement effacés lors d'une suppression de modèle, pour ne pas casser d'anciennes publications.

Les anciens `chemin_asset` restent utilisables pour les médias déjà contrôlés, désormais relatifs à `media/`. Copier les anciennes illustrations depuis `static_assets/` vers `media/` en conservant leurs sous-répertoires. Les SVG ne sont pas acceptés en upload ; un SVG existant doit être contrôlé avant intégration manuelle.

En production, servir `/media/` par le serveur HTTP ou un stockage adapté ; Django ne le sert directement qu'en développement. Ces médias sont publics, pas une zone de stockage de pièces sensibles.

## Mise à niveau d'une base existante

Sauvegarder la base, ses migrations locales et ses médias avant la mise à niveau. Ne pas supprimer une base contenant du travail pour faire passer les migrations.

L'archive précédente ne livrait aucune migration. Cette version fournit les migrations initiales du schéma historique, puis `content_api/0002` pour le champ upload et le chemin optionnel.

- Base vierge : `python manage.py migrate` suffit.
- Migrations `0001` déjà générées localement : comparer leur contenu et leur historique avec les migrations livrées. Si le schéma historique correspond, conserver l'historique et appliquer la nouvelle migration `0002`.
- Tables créées hors migrations : vérifier d'abord que toutes les colonnes et contraintes correspondent aux migrations initiales. `--fake-initial` ne vérifie pas à lui seul cette correspondance ; ne l'utiliser qu'après ce contrôle et sauvegarde.
- Schéma différent : écrire une migration de transition adaptée ; ne pas utiliser `--fake` pour masquer une divergence.

Cette mise à niveau n'a pas été exécutée sur ta base Kali ni sur un serveur distant.

## Vérifications et déploiement

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
python -m pytest -q
```

Les tests sont prévus pour SQLite. Le parcours de publication et restauration, les formulaires d’administration, le schéma Swagger, les droits, les APIView, CSRF et les uploads sont couverts. Ils doivent être exécutés sur Kali ; ils n’ont pas été lancés dans l’environnement de préparation du patch. MySQL et le reverse proxy doivent être vérifiés dans l'environnement cible.

En production : `DEBUG=false`, secret aléatoire, hôtes et origines exacts, paramètres MySQL, HTTPS, `collectstatic --noinput`, puis `check --deploy`. Les cookies deviennent Secure. Ne déclarer `TRUST_PROXY_SSL_HEADER=true` que si le proxy contrôle cet en-tête. Ajouter au proxy une limite des corps de requête et une limitation des tentatives de connexion admin. Les protections contre les tentatives de connexion doivent également être configurées au niveau du proxy ou d’une solution dédiée.

Exécuter régulièrement `python manage.py clearsessions` pour supprimer les sessions expirées. Sauvegarder la base, les releases et les médias ensemble. Aucune purge de médias référencés par une ancienne release ne doit être faite à l'aveugle.
