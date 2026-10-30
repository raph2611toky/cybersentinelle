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
| `config/editor_urls.py` | Routeur des CRUD éditoriaux |
| `apps/core/` | Langues, permissions, validation commune, session visiteur |
| `apps/content_api/` | Sujets, illustrations, histoires, nœuds, options |
| `apps/resources/` | Sources et ressources d'aide |
| `apps/pedagogie/` | Questions pédagogiques |
| `apps/publication/` | Validation, snapshots, publication et rollback |
| `helpers/helper.py` | Temps écoulé, URL de média, normalisation d'image |
| `media/` | Illustrations publiques, jamais des preuves ou témoignages |
| `content/releases/` | JSON publiés figés |
| `tests/` | Contrat public, graphes, droits, CRUD, sessions, uploads, publication |

Chaque application métier possède son `admin.py` (nom reconnu par Django), ses modèles, migrations et, selon ses endpoints, serializers, vues et routes. Les modèles `User` et `Group` standards de Django sont disponibles dans l'admin : les visiteurs n'ont pas de compte `User`.

## Droits d'accès

| Surface | Accès |
|---|---|
| `/api/v1/` | Lecture publique de snapshots validés ; aucune écriture |
| `/api/editor/` | Compte actif, `is_staff=True`, permission Django par modèle et opération |
| `/api/session/` | Visiteur anonyme ; écritures protégées par CSRF |
| `/admin/` | Connexion Django ; permissions par modèle |
| Documentation | Connexion staff requise, même en développement |

Un compte authentifié sans `is_staff` ne peut pas éditer. Un membre staff sans permission ne peut pas consulter les données éditoriales. Dans l'admin, créer des groupes puis attribuer `view`, `add`, `change`, `delete` selon les besoins. Les superutilisateurs ont tous les droits.

Les UUID d'objets éditoriaux sont renvoyés pour référencer les relations. Ce sont des identifiants, pas des secrets ni des autorisations. Les réponses ajoutent des objets `*_detail` / `*_details` contenant l'UUID et un libellé. Les données publiques gardent leurs slugs et clés métier. Ni clé de session ni identifiant de compte n'est exposé par l'API visiteur.

## CRUD éditoriaux

Ressources disponibles sous `/api/editor/` : `languages`, `topics`, `visuals`, `stories`, `nodes`, `options`, `sources`, `resources`, `questions`.

Pour chacune :

| Verbe | URL | Opération |
|---|---|---|
| GET | `/<ressource>/` | Liste paginée, 25 éléments par page |
| POST | `/<ressource>/` | Création |
| GET | `/<ressource>/<uuid>/` | Détail |
| PUT | `/<ressource>/<uuid>/` | Mise à jour selon les champs requis du serializer |
| PATCH | `/<ressource>/<uuid>/` | Modification partielle |
| DELETE | `/<ressource>/<uuid>/` | Suppression, si les dépendances l'autorisent |

`?page=2`, `?search=mot`, `?ordering=-updated_at` sont disponibles. La recherche porte sur les champs textuels déclarés de chaque ressource, sauf les langues. Les créations et modifications utilisent JSON ; les visuels acceptent aussi `multipart/form-data` avec le champ `fichier`.

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

## Sessions et intégration frontend

L'identité technique est pseudonyme : Django conserve une session serveur derrière un cookie `sessionid` HttpOnly, sans créer de profil utilisateur. Le simple accès aux histoires ne crée pas de session. Le frontend choisit quand initialiser la session :

1. `GET /api/session/`, avec `credentials: 'include'`, initialise le cookie CSRF et renvoie l'état de session.
2. Lire le cookie `csrftoken` et le transmettre dans `X-CSRFToken` sur chaque écriture. Swagger propose aussi ce champ via **Authorize**.
3. `POST /api/session/` avec `{"language":"fr"}` crée ou renouvelle la session, en tournant sa clé.
4. `PATCH /api/session/` change `language` (`fr` ou `mg`).
5. `DELETE /api/session/` efface la session visiteur. Si l'appelant est connecté à l'admin, son authentification est conservée.

La réponse contient `active`, `language`, `expires_at` et `elapsed_seconds` lorsque la session existe. Durée de la session visiteur : 24 heures. Une autre session ne peut pas être sélectionnée par UUID dans l'URL ou dans le corps de requête. Les choix, scores, récits personnels et preuves ne sont pas enregistrés.

Pour les écritures éditoriales, se connecter d'abord via `/admin/login/` : le jeton CSRF ne remplace jamais l'authentification. Déployer de préférence frontend et API sur la même origine ou le même site. Les origines CORS autorisées sont explicites ; `SameSite=Lax` ne permet pas de réutiliser les cookies entre deux sites indépendants. Un proxy de même origine évite ce problème. Le frontend doit être adapté : cette archive ne modifie pas son code.

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

Les tests exécutés ici utilisent SQLite. Le parcours de publication et restauration, les formulaires d'administration, le schéma Swagger, les droits, les sessions isolées, CSRF et les uploads font partie des tests. MySQL et le reverse proxy doivent être vérifiés dans l'environnement cible.

En production : `DEBUG=false`, secret aléatoire, hôtes et origines exacts, paramètres MySQL, HTTPS, `collectstatic --noinput`, puis `check --deploy`. Les cookies deviennent Secure. Ne déclarer `TRUST_PROXY_SSL_HEADER=true` que si le proxy contrôle cet en-tête. Ajouter au proxy une limite des corps de requête et une limitation des tentatives de connexion admin. La limitation DRF des sessions utilise le cache local ; plusieurs workers nécessitent un cache partagé si une limite globale est souhaitée.

Exécuter régulièrement `python manage.py clearsessions` pour supprimer les sessions expirées. Sauvegarder la base, les releases et les médias ensemble. Aucune purge de médias référencés par une ancienne release ne doit être faite à l'aveugle.
