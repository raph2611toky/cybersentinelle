# SAFIDIKO — intégration Dashboard React ↔ Backend Django

## Ce qui est inclus

- `dashboard/` : **projet React/Vite complet**, vos fichiers de refonte préservés et les nouveaux services Axios.
- `backend_patch/` : **uniquement les fichiers modifiés ou ajoutés au backend**, basés sur `SAFIDIKO_Backend_Django_v3` puis les patches APIView, structure V3, CSRF same-origin et studio média/TTS. Il ne remplace pas les autres fichiers du backend existant.

## Installation sur Kali

Faites une sauvegarde ou un commit Git avant d’appliquer les fichiers sur votre backend. Les fichiers `apps/editor/urls.py` et `apps/content_api/models.py` sont des versions **complètes** à examiner si votre backend a évolué depuis les patches mentionnés.

```bash
cd /home/raph/competitions/cyber_sentinelle
cp -a backend backend.backup-before-dashboard
cp -a dashboard dashboard.backup-before-api

# Copier le code du dashboard extrait
cp -a /CHEMIN/EXTRACTION/dashboard/. ./dashboard/

# Installer uniquement les modifications nécessaires au backend
cp -a /CHEMIN/EXTRACTION/backend_patch/. ./backend/

cd backend
source .venv/bin/activate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python -m pytest -q tests/test_dashboard_integration.py
python manage.py createsuperuser  # si aucun compte admin staff n'existe
python manage.py runserver 127.0.0.1:8000
```

Dans un **autre** terminal :

```bash
cd /home/raph/competitions/cyber_sentinelle/dashboard
cp .env.example .env
npm install
npm run dev
```

Ouvrez **http://localhost:5173** (ne pas utiliser en même temps localhost et 127.0.0.1 côté navigateur, sauf si vous savez gérer vos cookies). La connexion se fait avec un compte Django `is_staff=True` disposant des permissions de lecture/écriture requises ; `createsuperuser` a toutes les permissions.

## Authentification, CSRF, cookies

Le backend existant utilise `SessionAuthentication`. Nous **n'ajoutons pas de JWT** : nous utilisons la session native Django comme jeton de session opaque dans `sessionid` **HttpOnly** et un cookie `csrftoken` avec l'en-tête `X-CSRFToken`. Aucune donnée d’authentification n’est stockée dans localStorage.

Le proxy Vite `/api` relaie les requêtes Django en **conservant Host** (`changeOrigin:false`) pour respecter l’origine CSRF. Le navigateur croit contacter le même domaine, tandis que Vite relaie en interne vers Django.

En production, le dashboard et `/api/` doivent être servis **sous le même domaine HTTPS** ; le serveur doit définir `DEBUG=false`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, des origines de confiance strictes et un rate limit sur `/api/editor/auth/login/`. Ne pas exposer le serveur Vite de développement sur Internet.

## Routes ajoutées (backend)

| Méthode | Route | Fonction |
|---|---|---|
| GET | `/api/editor/auth/csrf/` | Prépare le cookie CSRF |
| POST | `/api/editor/auth/login/` | Connexion staff (session HttpOnly) |
| GET | `/api/editor/auth/me/` | Session + permissions |
| POST | `/api/editor/auth/logout/` | Déconnexion serveur |
| GET | `/api/editor/stories/<uuid>/graph/` | Brouillon React Flow ou projection depuis la base |
| PUT | `/api/editor/stories/<uuid>/graph/save/` | Sauvegarde versionnée du brouillon |
| POST | `/api/editor/stories/<uuid>/graph/apply/` | Validation + synchronisation relationnelle atomique |

Les autres routes sont celles du **backend existant**, notamment `/api/editor/stories/`, `/api/editor/resources/`, `/api/editor/studio/*`, `/api/editor/releases/*`. Chaque route nouvelle est une `APIView` à **une seule méthode HTTP** et possède sa documentation Swagger dans un fichier distinct.

## Précautions métier

- Le backend est éditorial ; aucun compte, message, score ou progression de mineur n’est remonté.
- L’application d’un graphe supprime/recrée ses options de décision et met à jour les nœuds stables. Vérifiez les sauvegardes et les médias associés ; la suppression d’un nœud avec médias est refusée.
- `api/editor/releases/publish/` publie **réellement** une release : validation et confirmation manuelles requises. Une version publiée reste immuable.
- Des permissions `add/change/delete` sur `Noeud` et `OptionDecision` sont exigées pour appliquer un graphe.
- Les APIs de voix facturent éventuellement selon le fournisseur ; les clés restent dans le `.env` Django.

## Limites de vérification

Syntaxe Python et JavaScript/JSX vérifiées localement. **Pas de build npm exécuté ni de pytest exécuté** : ni le téléchargement npm ni Django n’étaient disponibles dans l’environnement. Vérifiez impérativement les commandes ci-dessus sur votre machine avant production.
