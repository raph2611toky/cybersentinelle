import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, Film, GitBranch, Play, RotateCcw, AlertCircle } from 'lucide-react';
import { useAdmin } from '../lib/store';
import { storyApi } from '../services/editor';
import api, { apiError } from '../services/api';

/** A media asset's public/staff endpoint may be emitted with an internal container hostname.
 *  Only accept known same-origin URL paths; never navigate to arbitrary storage hosts. */
function safeMediaUrl(raw) {
  if (!raw || typeof raw !== 'string') return '';
  try {
    const url = new URL(raw, window.location.origin);
    if (!['http:', 'https:'].includes(url.protocol)) return '';
    if (!/^\/api\/(editor\/studio\/media\/|v1\/)/.test(url.pathname)) return '';
    return url.pathname + url.search;
  } catch { return ''; }
}

function toStoryGraph(saved) {
  const nodes = saved?.graph?.nodes || [];
  const edges = saved?.graph?.edges || [];
  return {
    nodes: Object.fromEntries(nodes.map(n => [n.id, n.data])),
    next: (id, handle) => edges.find(e => e.source === id && (e.sourceHandle || 'out') === handle)?.target || '',
    ids: saved?.node_id_map || {},
  };
}

function toPublishedGraph(story) {
  const nodes = story?.nodes || {};
  return {
    nodes,
    next: (id, handle) => {
      const node = nodes[id];
      if (!node) return '';
      if (node.kind === 'scene') return node.next || '';
      return (node.options || []).find(o => o.id === handle)?.next || '';
    },
    ids: {},
  };
}

const tr = (object, lang) => object?.[lang] || object?.fr || '';

export default function StoryPreview() {
  const [params] = useSearchParams();
  const { stories, scenes, media, languages } = useAdmin();
  const story = stories.find(s => s.id === params.get('story'));
  const mode = params.get('mode') === 'published' ? 'published' : 'draft';
  const [lang, setLang] = useState('fr');
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [current, setCurrent] = useState('start');
  const [feedback, setFeedback] = useState(null);
  const [visited, setVisited] = useState([]);
  const [mediaError, setMediaError] = useState(false);
  const graph = useMemo(() => payload ? (mode === 'published' ? toPublishedGraph(payload) : toStoryGraph(payload)) : null, [payload, mode]);

  useEffect(() => {
    if (!story) { setPayload(null); return; }
    let live = true;
    setLoading(true); setError(''); setPayload(null); setCurrent('start'); setFeedback(null); setVisited([]);
    const request = mode === 'published'
      ? api.get(`/v1/stories/${encodeURIComponent(story.slug)}/`)
      : storyApi.graph(story.id);
    request.then(({data}) => {
      if (!live) return;
      setPayload(data);
      const keys = mode === 'published' ? Object.keys(data?.nodes || {}) : (data?.graph?.nodes || []).map(n => n.id);
      setCurrent(keys.includes('start') ? 'start' : (keys[0] || ''));
    }).catch(e => { if (live) setError(mode === 'published' && e.response?.status === 404
      ? 'Cette histoire ne figure pas dans la release active. Approuve-la et publie une nouvelle release.'
      : apiError(e)); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [story?.id, story?.slug, mode]);

  useEffect(() => { setMediaError(false); }, [current, lang, mode]);

  const node = graph?.nodes[current];
  const language = languages.find(l => l.code === lang);
  const dbId = graph?.ids[current];
  const draftScene = mode === 'draft' && dbId && language
    ? scenes.find(s => s.noeud === dbId && s.langue === language.id)
    : null;
  const draftAsset = mode === 'draft' && node?.media?.asset
    ? media.find(m => String(m.id) === String(node.media.asset))
    : null;
  const publishedMedia = mode === 'published' ? node?.media?.[lang] : null;
  const isReady = Boolean(draftScene?.statut === 'READY');
  const mediaById = id => media.find(m => String(m.id) === String(id));
  let video = '', audio = '', image = '', mediaNote = '';
  if (mode === 'published') {
    video = safeMediaUrl(publishedMedia?.video_url);
    audio = safeMediaUrl(publishedMedia?.audio_url);
    image = safeMediaUrl(node?.visual_url);
    if (!video && !audio && !image && node?.kind !== 'decision') mediaNote = `Aucun média publié en ${lang.toUpperCase()} pour ce nœud.`;
  } else if (draftScene) {
    video = safeMediaUrl(isReady ? draftScene.video_finale_url : mediaById(draftScene.video)?.fichier_url);
    audio = safeMediaUrl(isReady ? draftScene.audio_finale_url : mediaById(draftScene.audio)?.fichier_url);
    image = safeMediaUrl(mediaById(draftScene.image)?.fichier_url);
    if (draftScene.mode === 'VIDEO_AUDIO' && !isReady) audio = ''; // Never present two unassembled tracks as a final render.
    mediaNote = isReady ? 'Rendu final prêt (média privé en prévisualisation).' : 'Brouillon : média source, rendu final encore à préparer.';
  } else if (draftAsset && lang === 'fr') {
    if (draftAsset.type === 'VIDEO') video = safeMediaUrl(draftAsset.fichier_url);
    if (draftAsset.type === 'IMAGE') image = safeMediaUrl(draftAsset.fichier_url);
    mediaNote = 'Média du brouillon : applique l’arbre puis lance un rendu pour la publication.';
  } else if (node && node.kind !== 'decision') {
    mediaNote = `Pas de média associé à ce nœud en ${lang.toUpperCase()}.`;
  }
  const goTo = id => {if (!id || !graph?.nodes[id]) {setError('Destination de scène introuvable dans cet arbre.');return;}
    setVisited(p => [...p, current]); setCurrent(id); setFeedback(null); setMediaError(false);};
  const continueScene = () => goTo(graph?.next(current, 'out'));
  const restart = () => {setCurrent(graph?.nodes.start ? 'start' : Object.keys(graph?.nodes || {})[0] || '');setFeedback(null);setVisited([]);setMediaError(false);};
  const options = node?.kind === 'decision' ? node.options || [] : [];
  const ended = node?.kind === 'ending';
  const currentTitle = tr(node?.title, lang) || 'Scène sans titre';
  const currentText = tr(node?.text, lang);
  const published = mode === 'published';

  return <div className="page-stack">
    <div className="section-toolbar">
      <span className="section-hint">{story?.title || 'Tantara'} · {published ? 'Lecture depuis la release active' : 'Prévisualisation privée du brouillon'}</span>
      <div className="tree-toolbar-actions">
        <Link className="btn btn-outline" to="/publication"><ArrowLeft size={16}/> Publication</Link>
        <label className="preview-lang">Langue <select value={lang} onChange={e => {setLang(e.target.value);setFeedback(null)}}><option value="fr">Français</option><option value="mg">Malagasy</option></select></label>
        <button className="btn btn-outline" onClick={restart} disabled={!graph}><RotateCcw size={16}/> Recommencer</button>
      </div>
    </div>
    {!published && <div className="soft-note">Mode administrateur : les médias non finalisés peuvent être affichés pour vérification, mais ne sont pas encore publiés. Aucun choix de joueur n'est envoyé au serveur.</div>}
    {published && <div className="soft-note">Lecture du contenu réellement diffusé par <code>/api/v1/stories/{story?.slug}/</code> et ses médias figés. Ce lecteur reste dans l'administration.</div>}
    {loading && <div className="api-banner">Chargement du parcours…</div>}
    {error && <div role="alert" className="api-error">{error}</div>}
    {!story && <div className="api-banner">Tantara inconnu. Reviens au catalogue pour le sélectionner.</div>}
    {!loading && graph && node && <div className="story-preview-layout">
      <section className="story-preview-stage" aria-label="Lecture du Tantara">
        <div className="story-preview-stage-head"><span>{node.kind === 'decision' ? 'DÉCISION' : node.kind === 'ending' ? 'FIN' : 'SCÈNE'}</span><span>{lang.toUpperCase()}</span></div>
        {node.kind !== 'decision' && <div className="story-preview-screen" key={`${current}-${lang}`}>
          {!mediaError && video ? <video src={video} controls autoPlay playsInline preload="metadata" onEnded={node.kind === 'scene' ? continueScene : undefined} onError={() => setMediaError(true)} />
            : !mediaError && image ? <img src={image} alt={currentTitle} onError={() => setMediaError(true)}/>
            : <div className="story-preview-placeholder"><Film size={40}/><span>{mediaError ? 'Média impossible à charger' : 'Scène sans image ou vidéo disponible'}</span></div>}
          {!mediaError && !video && audio && <audio src={audio} controls autoPlay onEnded={node.kind === 'scene' ? continueScene : undefined} />}
        </div>}
        {node.kind === 'decision' && <div className="story-preview-decision-banner"><GitBranch size={32}/><strong>À toi de choisir</strong><span>Ta décision déterminera la suite de l'histoire.</span></div>}
        <div className="story-preview-copy"><h2>{currentTitle}</h2><p>{currentText}</p></div>
        {mediaNote && node.kind !== 'decision' && <p className="story-preview-note">{mediaNote}</p>}
        {node.kind === 'scene' && <button className="btn btn-primary" onClick={continueScene}>Continuer vers la suite</button>}
        {node.kind === 'decision' && <div className="story-preview-choices">
          {options.map(option => <button key={option.id} className={`story-preview-choice ${feedback?.id === option.id ? 'selected' : ''}`} onClick={() => setFeedback(option)}>{tr(option.label, lang) || 'Choix sans texte'}</button>)}
          {feedback && <div className="story-preview-feedback"><CheckCircle2 size={18}/><span>{tr(feedback.feedback, lang) || 'Conséquence de ce choix'}</span><button className="btn btn-primary" onClick={() => goTo(graph?.next(current, feedback.id))}>Voir la conséquence</button></div>}
        </div>}
        {ended && <div className="story-preview-end"><CheckCircle2 size={19}/><span>Fin de ce parcours. Recommence pour explorer les autres décisions.</span><button className="btn btn-primary" onClick={restart}><RotateCcw size={16}/> Rejouer</button></div>}
      </section>
      <aside className="story-preview-aside"><h3>Parcours interactif</h3><p>{Object.keys(graph.nodes).length} nœuds disponibles · {visited.length + 1} étape(s) visitée(s)</p>
        <div className="story-preview-history">{[...visited, current].map((id, i) => <div key={`${id}-${i}`} className={id === current ? 'active' : ''}><span>{i + 1}</span>{tr(graph.nodes[id]?.title, lang) || id}</div>)}</div>
        <div className="soft-note"><AlertCircle size={15}/> {published ? 'Ce parcours est extrait de la publication active.' : 'La prévisualisation ne publie aucun fichier. Utilise « Publication » pour la mise en ligne.'}</div>
      </aside>
    </div>}
    {!loading && graph && !node && <div className="api-banner">Le nœud de départ n'existe pas encore. Applique un arbre valide ou corrige le brouillon.</div>}
  </div>;
}
