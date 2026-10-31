/**
 * Source commune des prévisualisations admin : choisir une piste FR/MG réelle,
 * puis associer vidéo muette + piste audio indépendante lorsque disponible.
 * Le MP4 peut avoir sa voix intégrée ; il n'est jamais audible en même temps
 * qu'une piste séparée. Aucune synthèse TTS ne démarre depuis un GET d'aperçu.
 */
export function adminMediaUrl(value) {
  if (typeof value !== 'string' || !value) return '';
  try {
    const url = new URL(value, window.location.origin);
    if (!['http:', 'https:'].includes(url.protocol)) return '';
    if (!/^\/api\/(?:editor\/studio\/media\/|v1\/)/.test(url.pathname)) return '';
    return url.pathname + url.search;
  } catch { return ''; }
}

function fallbackSource(scene, field, media) {
  if (!scene) return '';
  return adminMediaUrl(scene[field] || media.find(asset => String(asset.id) === String(scene[field === 'video_source_url' ? 'video' : field === 'image_source_url' ? 'image' : 'audio']))?.fichier_url);
}

export function draftSceneSources({ scenes, languages, media, nodeId, lang = 'fr', variantId = null }) {
  const getScene = code => {
    const language = languages.find(l => l.code === code);
    return scenes.find(s => String(s.noeud) === String(nodeId) && String(s.langue) === String(language?.id));
  };
  const chosen = getScene(lang);
  const french = getScene('fr');
  // Garder le même visuel lors du changement de langue, seule la piste change.
  const visual = french?.video || french?.image ? french : chosen;
  const override = chosen?.audio_variants?.find(v => String(v.id) === String(variantId) && v.audio_url);
  const chosenTrack = override?.audio_url || (variantId ? null : (chosen?.statut === 'READY' ? chosen.audio_finale_url : null)) ||
    (!variantId && (chosen?.audio_source_url || (chosen?.audio ? chosen?.audio_tracks?.[lang]?.url : null) ||
    fallbackSource(chosen,'audio_source_url',media)));
  const frenchTrack = (french?.statut === 'READY' ? french.audio_finale_url : null) ||
    french?.audio_source_url || (french?.audio ? french?.audio_tracks?.fr?.url : null) ||
    fallbackSource(french,'audio_source_url',media);
  const chosenSound = adminMediaUrl(chosenTrack);
  const frenchSound = adminMediaUrl(frenchTrack);
  const audio = chosenSound || frenchSound;
  const audioLanguage = chosenSound ? lang : frenchSound ? 'fr' : null;
  const finalVideo = adminMediaUrl(visual?.statut === 'READY' ? visual?.video_finale_url : '');
  const video = (audio ? fallbackSource(visual, 'video_source_url', media) || finalVideo : finalVideo || fallbackSource(visual, 'video_source_url', media));
  const image = fallbackSource(visual, 'image_source_url', media);
  // Source audio indépendante prioritaire, donc la vidéo doit être muette.
  const embeddedAudio = Boolean(!audio && finalVideo && visual?.audio_embedded);
  return { video, audio, image, embeddedAudio, audioLanguage };
}

export function publishedSceneSources(node, lang = 'fr') {
  const preferred = node?.media?.[lang] || {};
  const french = node?.media?.fr || {};
  const selectedTrack = adminMediaUrl(node?.audio_tracks?.[lang]?.url || preferred.audio_url);
  const frenchTrack = adminMediaUrl(node?.audio_tracks?.fr?.url || french.audio_url);
  const audio = selectedTrack || frenchTrack;
  const audioLanguage = selectedTrack ? lang : frenchTrack ? 'fr' : null;
  const video = adminMediaUrl(french.video_url || preferred.video_url);
  return {
    video, audio,
    image: adminMediaUrl(node?.visual_url),
    embeddedAudio: Boolean(video && !audio && (french.video_url ? french.audio_embedded : preferred.audio_embedded)),
    audioLanguage,
  };
}
