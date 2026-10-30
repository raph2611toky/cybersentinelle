# SAFIDIKO — Dashboard d’administration React

Cette version conserve la refonte UI fournie (`safidiko-ui-refonte.zip`) et raccorde les pages à la véritable API Django DRF.

## Environnement

Depuis `dashboard/` :

```bash
cp .env.example .env
npm install
npm run dev
```

`.env` :

```dotenv
VITE_API_BASE_URL=/api
VITE_DEV_PROXY_TARGET=http://127.0.0.1:8000
```

Le proxy Vite conserve l’en-tête `Host` pour que Django considère l’`Origin` comme étant de même origine lors du contrôle CSRF. Ouvrir le dashboard sur `http://localhost:5173`. Django sur `http://127.0.0.1:8000`.

En production, servir le dashboard et `/api/` sous **le même domaine HTTPS** via un reverse proxy. Ne jamais placer de secrets Django, Gemini, ElevenLabs ou JWT dans `VITE_*` (ces variables sont publiques dans le bundle).

## Connexion staff

1. `GET /api/editor/auth/csrf/` émet le cookie CSRF.
2. `POST /api/editor/auth/login/` valide identifiant/mot de passe côté Django ; la réponse définit la session `sessionid` **HttpOnly**.
3. `GET /api/editor/auth/me/` revalide les permissions après chaque rechargement.
4. `POST /api/editor/auth/logout/` invalide réellement la session.

Axios fournit `X-CSRFToken` pour les mutations ; l’authentification ne dépend **ni de localStorage ni de JWT côté navigateur**. Le cookie `sessionid` est le jeton opaque de session Django. Toutes les écritures nécessitent les permissions Django du modèle.

## Pages raccordées

- Tableau de bord : les récits/nœuds/options/ressources proviennent de Django (aucune statistique utilisateur).
- Tantara : GET/POST/PATCH/DELETE des histoires éditoriales bilingues, sans inventer de traduction MG.
- Arbre React Flow : GET, PUT de brouillon avec révision optimistic-lock, puis POST explicite de **validation/application relationnelle atomique** aux `Noeud`/`OptionDecision`. Ce bouton est désactivé tant que des modifications ne sont pas sauvegardées. L’application réinitialise le statut éditorial en brouillon ; la publication exige une nouvelle approbation.
- Ressources d’aide : GET/POST/PATCH/DELETE et sources éditoriales officielles ; confirmation avant activer un contact.
- Médiathèque : liste, upload multipart avec validation des droits, lecture des assets privés par blob authentifié, suppression.
- Voix : liste, création de `VoiceProfile`, création de `SceneMedia`, déclenchement Gemini/ElevenLabs via backend, travaux Celery et assemblages FFmpeg.
- Publication : GET des releases, validation de prépublication, approbation FR/MG humaine, déclenchement réel d’une release, rollback.
- Paramètres : session staff, API configurée, compteurs réels et actualisation.

## Important sur les graphes

`BrouillonGraphe` est un **brouillon graphique privé** (JSON React Flow) lié à un Tantara, sans aucune donnée de joueur. Enregistrer ne modifie pas le contenu publiable. « Appliquer au backend » vérifie les chemins, langues, fins, options et crée/met à jour les objets métier dans une transaction ; toute erreur annule les changements. Les nœuds supprimés liés à des médias sont refusés pour éviter une perte accidentelle.

Le graphe doit contenir `start` et exactement `decisions_attendues` décisions sur **chaque** parcours ; aucune boucle autorisée. Les deux langues FR et MG et les retours pédagogiques des choix sont exigés lors de l’application. Les récits existants sont convertis en graphe lorsque aucun brouillon n’a encore été créé.

## Dépendances externes

Le studio vocal dépend d’un worker Celery/Redis, de FFmpeg et des clés des fournisseurs configurées **uniquement dans le `.env` du backend**, jamais dans le dashboard.

## Tests

```bash
npm run build
cd ../backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python -m pytest -q tests/test_dashboard_integration.py
```

Les sources ont été vérifiées par analyse syntaxique JavaScript/JSX et Python. Le build npm et pytest doivent être exécutés sur Kali : les dépendances réseau n’étaient pas disponibles dans l’environnement de création.
