# SAFIDIKO — Tantara avec image de couverture

Compatibilité : intégrer ce patch sur la version **SAFIDIKO V2 (file de traduction FR→MG)** fournie précédemment.
Le backend est livré comme patch de fichiers modifiés ; le dashboard complet est livré séparément.

## Mise à jour backend

1. Sauvegarder la base, le dossier `backend/media/` et les fichiers locaux.
2. Copier le contenu de l'archive patch depuis la racine `backend/` (comparer avant écrasement).
3. Vérifier la migration et appliquer :

```bash
cd /home/raph/competitions/cyber_sentinelle/backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate content_api
python -m pytest -q tests/test_tantara_cover.py
```

Les fichiers envoyés sont reformatés en PNG (PNG/JPEG/WEBP autorisés, upload max. 5 Mo). `image_cover` est facultatif afin de garder les Tantara existants.

## Dashboard

```bash
cd /home/raph/competitions/cyber_sentinelle/dashboard
npm install
npm run dev
```

`VITE_API_BASE_URL=/api` et `VITE_DEV_PROXY_TARGET=http://127.0.0.1:8000` restent inchangés dans `.env`. Le proxy Vite existant relaie `/api` **et** `/media` vers Django. En production, servir `/media/` par HTTPS sur le même domaine.

Les appels `storyApi.create` et `storyApi.update` utilisent `FormData`; ne pas définir manuellement `Content-Type` (Axios fournit la boundary). L'authentification `sessionid` HttpOnly et la protection CSRF restent actives.

### Endpoints

- `POST /api/editor/stories/create/` — `multipart/form-data` ; formulaire français + image optionnelle
- `PUT /api/editor/stories/{uuid}/update/` — `multipart/form-data` ; mise à jour complète
- `PATCH /api/editor/stories/{uuid}/partial-update/` — `multipart/form-data` ; image, champs FR et `effacer_couverture=true` pour retrait
- `GET /api/editor/stories/{uuid}/` — JSON avec `image_cover` et `image_cover_url`
- `GET /api/v1/covers/{release}/{slug}/` — couverture de la release immuable (après nouvelle publication)

Les trois méthodes d'écriture Swagger disposent exclusivement de paramètres `formData` manuels, et **pas de** `request_body`. Les vues restent des `APIView` distinctes avec une seule méthode métier par classe.

**Contrainte version** : les requêtes JSON de création et de modification de Tantara utilisées par d'anciens clients doivent être adaptées en multipart. Les autres endpoints JSON restent inchangés.

### Vérification manuelle

1. Créer un Tantara sans image, vérifier `image_cover_url: null`.
2. Modifier le Tantara avec un PNG/JPEG/WebP, vérifier l'aperçu dans la liste et la réponse de l'API.
3. Remplacer puis retirer la couverture, vérifier que le champ devient `null`.
4. Envoyer un faux `.png` : attendre une réponse 400.
5. Ouvrir `/api/docs/` et contrôler le champ fichier sur POST, PUT et PATCH, sans `requestBody`.
6. Publier une version validée, vérifier `cover_url` dans le catalogue public et le téléchargement sur `/api/v1/covers/...`.

**Note** : les tests ne peuvent pas être exécutés dans cet environnement sans les dépendances Django/DRF/drf-yasg. Ils sont fournis pour une exécution locale sur Kali.
