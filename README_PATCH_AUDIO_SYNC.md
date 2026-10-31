# SAFIDIKO — import audio + synchronisation des scènes

## Application

Correctif incrémental **à poser sur SAFIDIKO_Arbre_Medias_Voix_TTS_FFmpeg_Patch.zip**, qui lui-même est basé sur `dashboard.zip` + `backend(20261030-235522).zip`. Les fichiers de l'archive s'appliquent à la racine du dépôt (dossiers `backend/` et `dashboard/`). Ne jamais remplacer le `.env` de production, les médias ni la base MySQL. Ne contient pas de secret.

## Nouvelles fonctions

- Voix directement importée (MP3/WAV/M4A/OGG) depuis la modale Scène, licence/droits confirmés, puis liaison à `SceneMedia.audio` via la médiathèque privée. La source peut également provenir de Google TTS/ElevenLabs comme auparavant.
- Mode `AUDIO_ONLY` : aucun visuel requis ; le rendu produit un MP3 autonome et un `audio_finale_url` côté administration. À la publication, JSON `{mode: "audio", audio_url: "..."}` pour chaque langue concernée. Le lecteur public doit gérer `audio_url` pour lire ce mode ; les scènes vidéo existantes continuent à utiliser `video_url`.
- Trois stratégies **uniquement pour vidéo + audio séparé** : `SPEED` (utilise l'audio entier et calcule automatiquement la vitesse), `TRIM` (segment exact à vitesse 1×), `TRIM_SPEED` (segment choisi puis vitesse calculée automatiquement). La modale permet aussi de saisir la vitesse souhaitée pour calculer la fin du segment. Plage 0,5×–2,5×. Toute durée incompatible provoque un échec explicite, plutôt qu'une coupe ou une accélération silencieuse.
- Vérification FFprobe pour l'audio/vidéo ; tolérance technique : 0,085 s (environ deux images à 25 fps) pour prendre en compte l'encodage AAC/H.264. L'audio final et la vidéo visent la durée de la vidéo originale, sans modifier ses images sauf la conversion 25 fps.
- Le texte n'est **pas requis** pour la voix importée. Pour le TTS, le texte reste nécessaire. Une synthèse TTS sans image/vidéo devient automatiquement `AUDIO_ONLY`.

## Déploiement

1. **Sauvegarder** MySQL et les médias privés avant déploiement. Aucune suppression de données ni de conteneur de base de données.
2. Fusionner les fichiers du patch sur les sources du dépôt ; en cas de divergence Git, inspecter avant de remplacer.
3. Recréer les images `backend` et **worker Celery avec la même version du code**, sans toucher aux volumes MySQL.
4. Exécuter `python manage.py migrate --noinput` depuis le conteneur avec `DB_ENGINE=mysql`, puis `python manage.py check` et `python manage.py seed_defaults`. Le pipeline Jenkins existant effectue déjà ces opérations s'il est à jour.
5. Reconstruire et redéployer le dashboard React.
6. Tester en production : importer un audio, choisir `VIDEO_AUDIO`, régler `SPEED`/`TRIM`/`TRIM_SPEED`, enregistrer puis assembler ; puis tester une scène `AUDIO_ONLY` sans visuel. Vérifier dans le studio les jobs `RENDER/SUCCESS` et les rendus accessibles avec session admin.

## Sécurité et limites

- `audio_finale` est un fichier du stockage privé et n'est rendu public qu'au sein d'un snapshot de publication vérifié, après confirmation des droits.
- Les `SceneMedia` déjà sauvegardés utilisent `SPEED` par défaut, sans suppression de liens existants. Un réglage modifié invalide l'ancien rendu mais pas les anciennes publications immuables.
- Ne jamais considérer les quotas Google ou ElevenLabs comme gratuits et illimités ; ce correctif n'ajoute aucun appel TTS automatique non sollicité lors d'un import.
- Les tests FFmpeg locaux ont été exécutés ; **les tests d'intégration Django n'ont pas été lancés ici** faute de dépendances installées.
