import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  Background, BackgroundVariant, Controls, Handle, Position, ReactFlow,
  addEdge, applyEdgeChanges, applyNodeChanges,
} from '@xyflow/react';
import {
  BookOpen, CheckCircle2, Clapperboard, Flag, GitBranch, Link2Off,
  Plus, RefreshCw, Save, Trash2, Unplug, Video, Play,
} from 'lucide-react';
import { Field, Panel } from '../components/UI';
import { useAdmin } from '../lib/store';
import { storyApi, studioApi, translationApi } from '../services/editor';
import { newGraph } from '../data/seed';
import { apiError } from '../services/api';

const nodeTypes = { story: StoryNode };

function StoryNode({ data, selected }) {
  const icon = data.kind === 'decision' ? <GitBranch size={17}/> : data.kind === 'ending' ? <Flag size={17}/> : <BookOpen size={17}/>;
  return <div className={`flow-node flow-${data.kind} ${selected ? 'flow-selected' : ''}`}>
    <Handle type="target" position={Position.Top} id="in" />
    <div className="flow-node-header">{icon}<span>{data.kind === 'decision' ? 'DÉCISION' : data.kind === 'ending' ? 'FIN' : 'SCÈNE'}</span>{(data.hasVideo || data.media?.asset) && <span className="flow-video-tag"><Video size={11}/> MÉDIA</span>}</div>
    <strong>{data.title?.fr || 'Sans titre'}</strong>
    <small>{data.text?.fr || 'Cliquer pour modifier'}</small>
    {data.kind === 'decision'
      ? <div className="flow-options">{(data.options || []).map((option, index, options) => <div key={option.id} className="flow-option">
        {option.label?.fr || 'Choix'}
        <Handle type="source" id={option.id} position={Position.Bottom}
          style={{ left: `${12 + Math.round((index + 1) * 76 / (options.length + 1))}%`, bottom: -6 }}/>
      </div>)}</div>
      : data.kind === 'scene' && <Handle type="source" position={Position.Bottom} id="out" />}
  </div>;
}

function validateGraph({ nodes = [], edges = [] }) {
  if (!nodes.length) return ['Aucun nœud'];
  const lookup = new Map(nodes.map(n => [n.id, n]));
  const issues = [];
  if (!lookup.has('start')) issues.push('Le nœud initial « start » est obligatoire');
  if (![...lookup.values()].some(n => n.data.kind === 'ending')) issues.push('Ajouter au moins une fin');
  for (const e of edges) if (!lookup.has(e.source) || !lookup.has(e.target)) issues.push('Liaison sans destination valide');
  for (const n of nodes) {
    const outgoing = edges.filter(e => e.source === n.id);
    if (!n.data.title?.fr?.trim()) issues.push(`Titre français manquant : ${n.id}`);
    if (n.data.kind === 'scene' && (outgoing.length !== 1 || !['out', null, undefined].includes(outgoing[0]?.sourceHandle))) issues.push(`Scène ${n.id} : relier exactement une sortie`);
    if (n.data.kind === 'ending' && outgoing.length) issues.push(`Fin ${n.id} : aucune sortie autorisée`);
    if (n.data.kind === 'decision') {
      const opts = n.data.options || [];
      if (opts.length < 2 || opts.length > 3) issues.push(`Décision ${n.id} : 2 ou 3 choix requis`);
      for (const opt of opts) if (outgoing.filter(e => e.sourceHandle === opt.id).length !== 1) issues.push(`Choix non relié : ${opt.label?.fr || opt.id}`);
      if (outgoing.some(e => !opts.some(o => o.id === e.sourceHandle))) issues.push(`Décision ${n.id} : liaison sans option`);
    }
  }
  // L'API refusera également les cycles et les nœuds inaccessibles.
  return [...new Set(issues)];
}

function wouldCreateCycle(edges, source, target) {
  const todo = [target];
  const seen = new Set();
  while (todo.length) {
    const cur = todo.pop();
    if (cur === source) return true;
    if (seen.has(cur)) continue;
    seen.add(cur);
    for (const edge of edges) if (edge.source === cur) todo.push(edge.target);
  }
  return false;
}

export default function StoryTree() {
  const { stories, media, scenes, languages, refresh } = useAdmin();
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [mediaBusy, setMediaBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [params, setParams] = useSearchParams();
  const story = stories.find(s => s.id === params.get('story')) || stories[0];
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [nodeIdMap, setNodeIdMap] = useState({});
  const [selectedId, setSelectedId] = useState(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState(null);
  const [videoLang, setVideoLang] = useState('fr');
  const [videoId, setVideoId] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadLicence, setUploadLicence] = useState('');
  const [uploadRights, setUploadRights] = useState(false);
  const [videoPreview, setVideoPreview] = useState('');
  const previewUrl = useRef('');
  const uploadInput = useRef(null);
  const [translation, setTranslation] = useState({ state: 'NONE', pending: 0, failed: 0, translated: 0 });
  const [draftId, setDraftId] = useState(null);
  const [dirty, setDirty] = useState(false);

  const closePreview = useCallback(() => {
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = '';
    setVideoPreview('');
  }, []);
  useEffect(() => () => { if (previewUrl.current) URL.revokeObjectURL(previewUrl.current); }, []);

  useEffect(() => {
    let active = true;
    if (!story) return;
    setLoading(true); setMessage(''); setSelectedId(null); setSelectedEdgeId(null); setDirty(false);
    setNodeIdMap({}); closePreview();
    storyApi.graph(story.id).then(({data}) => {
      if (!active) return;
      const isNew = !data.graph?.nodes?.length;
      const graph = isNew ? newGraph(story.title) : data.graph;
      setNodes(graph.nodes); setEdges(graph.edges);
      setRevision(data.revision || 0); setDraftId(data.draft_id);
      setNodeIdMap(data.node_id_map || {});
      setTranslation(data.translation_state || {state: 'NONE', pending: 0, failed: 0, translated: 0});
      setDirty(isNew);
    }).catch(e => {if (active) setMessage(apiError(e));})
      .finally(() => {if (active) setLoading(false);});
    return () => {active = false;};
  }, [story?.id, closePreview]);

  const selected = nodes.find(n => n.id === selectedId);
  const selectedEdge = edges.find(e => e.id === selectedEdgeId);
  const dbNodeId = selected && nodeIdMap[selected.id];
  const currentLanguage = languages.find(l => l.code === videoLang);
  const existingSceneMedia = scenes.find(s => s.noeud === dbNodeId && s.langue === currentLanguage?.id);
  const availableVideos = media.filter(m => m.type === 'VIDEO' && m.droits_confirmes);
  const availableAssets = media.filter(m => ['VIDEO','IMAGE'].includes(m.type) && m.droits_confirmes);
  const issues = useMemo(() => validateGraph({nodes, edges}), [nodes, edges]);
  const flowNodes = useMemo(() => nodes.map(n => ({
    ...n, data: {...n.data, hasVideo: Boolean(nodeIdMap[n.id] && scenes.some(s => s.noeud === nodeIdMap[n.id] && s.video))},
  })), [nodes, nodeIdMap, scenes]);
  const flowEdges = useMemo(() => edges.map(e => ({
    ...e, interactionWidth: 25,
    style: { stroke: e.id === selectedEdgeId ? '#c9a3ff' : '#40aefc', strokeWidth: e.id === selectedEdgeId ? 3.4 : 1.8 },
  })), [edges, selectedEdgeId]);

  useEffect(() => { setVideoId(existingSceneMedia?.video || ''); closePreview(); }, [selectedId, videoLang, existingSceneMedia?.id, existingSceneMedia?.video, closePreview]);
  useEffect(() => { if (selectedEdgeId && !edges.some(e => e.id === selectedEdgeId)) setSelectedEdgeId(null); }, [edges, selectedEdgeId]);

  const onNodesChange = useCallback(changes => {
    setNodes(old => applyNodeChanges(changes, old));
    if (changes.some(c => c.type !== 'select')) setDirty(true);
  }, []);
  const onEdgesChange = useCallback(changes => {
    setEdges(old => applyEdgeChanges(changes, old));
    if (changes.some(c => c.type !== 'select')) setDirty(true);
  }, []);
  const isValidConnection = useCallback(connection => {
    const source = nodes.find(n => n.id === connection.source);
    if (!source || !connection.target || connection.source === connection.target) return false;
    if (source.data.kind === 'ending') return false;
    if (source.data.kind === 'scene' && ![null, undefined, 'out'].includes(connection.sourceHandle)) return false;
    if (source.data.kind === 'decision' && !(source.data.options || []).some(o => o.id === connection.sourceHandle)) return false;
    const other = edges.filter(e => !(e.source === connection.source && (e.sourceHandle || 'out') === (connection.sourceHandle || 'out')));
    return !wouldCreateCycle(other, connection.source, connection.target);
  }, [nodes, edges]);
  const onConnect = useCallback(connection => {
    if (!isValidConnection(connection)) { setMessage('Connexion refusée : vérifie le type de nœud ou un éventuel cycle.'); return; }
    setEdges(old => {
      const remaining = old.filter(e => !(e.source === connection.source && (e.sourceHandle || 'out') === (connection.sourceHandle || 'out')));
      return addEdge({ ...connection, id: `edge-${Date.now()}`, type: 'smoothstep', animated: true }, remaining);
    });
    setSelectedEdgeId(null); setDirty(true); setMessage('');
  }, [isValidConnection]);
  const deleteLink = () => {
    if (!selectedEdgeId) return;
    setEdges(old => old.filter(e => e.id !== selectedEdgeId));
    setSelectedEdgeId(null); setDirty(true);
    setMessage('Liaison retirée du brouillon. Clique sur Enregistrer pour conserver le changement.');
  };
  const modifySelected = patch => { setNodes(prev => prev.map(n => n.id === selectedId ? {...n, data: {...n.data, ...patch}} : n)); setDirty(true); };
  const addNode = kind => {
    const id = `${kind}-${Date.now()}`;
    const node = { id, type: 'story', position: {x: 180 + (nodes.length % 3) * 185, y: 120 + nodes.length * 58},
      data: { kind, title: {fr: `Nouvelle ${kind === 'scene' ? 'scène' : kind === 'decision' ? 'décision' : 'fin'}`, mg: ''}, text: {fr: '', mg: ''},
        ...(kind === 'decision' ? {options: [
          {id: `option-${Date.now()}-a`, label: {fr: 'Choix A', mg: ''}, feedback: {fr: '', mg: ''}, quality: 0},
          {id: `option-${Date.now()}-b`, label: {fr: 'Choix B', mg: ''}, feedback: {fr: '', mg: ''}, quality: 0},
        ]} : {}) } };
    setNodes(prev => [...prev, node]); setSelectedId(id); setSelectedEdgeId(null); setDirty(true);
  };
  const addOption = () => {
    if (!selected || selected.data.kind !== 'decision') return;
    if ((selected.data.options || []).length >= 3) {setMessage('Une décision accepte 2 à 3 choix.'); return;}
    const options = [...(selected.data.options || []), {id: `opt-${Date.now()}`, label: {fr: `Choix ${(selected.data.options || []).length + 1}`, mg: ''}, feedback: {fr: '', mg: ''}, quality: 0}];
    modifySelected({options});
  };
  const deleteNode = () => {
    if (!selected) return;
    if (dbNodeId && scenes.some(s => s.noeud === dbNodeId)) {setMessage('Ce nœud possède un média associé. Retire ses médias dans le studio avant suppression.');return;}
    setNodes(prev => prev.filter(n => n.id !== selectedId));
    setEdges(prev => prev.filter(e => e.source !== selectedId && e.target !== selectedId));
    setSelectedId(null); setDirty(true);
  };
  const save = async () => {
    if (!story || saving) return;
    setSaving(true); setMessage('');
    try {
      const {data} = await storyApi.saveGraph(story.id, {nodes, edges}, revision);
      setRevision(data.revision); setDraftId(data.draft_id);
      setTranslation(data.translation_state || {state: 'NONE', pending: 0, failed: 0, translated: 0});
      setDirty(false); setMessage('Brouillon enregistré. La traduction malgache continue en arrière-plan.');
    } catch(e) {setMessage(apiError(e));} finally {setSaving(false);}
  };
  const apply = async () => {
    if (!story || dirty || saving || ['PENDING','FAILED'].includes(translation.state)) return;
    if (!window.confirm('Appliquer le brouillon aux nœuds Django ? Les médias des nœuds conservés restent associés.')) return;
    setSaving(true); setMessage('');
    try {
      const {data} = await storyApi.applyGraph(story.id);
      const graph = await storyApi.graph(story.id);
      setNodeIdMap(graph.data.node_id_map || {});
      await refresh();
      setMessage(`${data.nodes} nœuds appliqués. Tu peux maintenant associer des vidéos aux scènes et aux fins.`);
    } catch(e) {setMessage(apiError(e));} finally {setSaving(false);}
  };

  const saveVideo = async () => {
    if (!dbNodeId || dirty || !currentLanguage?.id || !videoId) return;
    setMediaBusy(true); setMessage('');
    try {
      const payload = {mode: 'VIDEO_ORIGINAL', video: videoId, image: null, audio: null};
      if (existingSceneMedia) await studioApi.updateScene(existingSceneMedia.id, payload);
      else await studioApi.createScene({ ...payload, noeud: dbNodeId, langue: currentLanguage.id });
      await refresh(); setMessage(`Vidéo associée à ce nœud pour ${videoLang.toUpperCase()}. Lancer le rendu avant publication.`);
    } catch(e) {setMessage(apiError(e));} finally {setMediaBusy(false);}
  };
  const removeVideo = async () => {
    if (!existingSceneMedia || dirty) return;
    setMediaBusy(true); setMessage('');
    try {
      await studioApi.updateScene(existingSceneMedia.id, {mode: 'TEXT_ONLY', video: null, audio: null, image: null});
      await refresh(); closePreview(); setVideoId(''); setMessage('Vidéo retirée du nœud ; fichier conservé dans la médiathèque.');
    } catch(e) {setMessage(apiError(e));} finally {setMediaBusy(false);}
  };
  const renderVideo = async () => {
    if (!existingSceneMedia?.video || dirty || mediaBusy) return;
    setMediaBusy(true); setMessage('');
    try {await studioApi.render(existingSceneMedia.id); await refresh();setMessage('Rendu FFmpeg ajouté à la file de traitements.');}
    catch(e) {setMessage(apiError(e));} finally {setMediaBusy(false);}
  };
  const uploadVideo = async () => {
    if (!uploadFile || !uploadLicence.trim() || !uploadRights || !dbNodeId || dirty) return;
    setMediaBusy(true); setMessage('');
    try {
      const form = new FormData();
      form.append('fichier', uploadFile);
      form.append('titre', uploadFile.name.replace(/\.[^.]+$/, '').slice(0, 200));
      form.append('type', 'VIDEO');
      form.append('licence', uploadLicence.trim());
      form.append('droits_confirmes', 'true');
      form.append('langue', videoLang);
      const {data} = await studioApi.upload(form);
      await refresh();
      if (uploadInput.current) uploadInput.current.value = '';
      setVideoId(data.id); setUploadFile(null);setUploadLicence('');setUploadRights(false);
      setMessage('Vidéo importée dans la médiathèque privée. Clique sur « Associer » pour lier le nœud.');
    } catch(e) {setMessage(apiError(e));} finally {setMediaBusy(false);}
  };
  const previewVideo = async () => {
    if (!videoId) return;
    setMediaBusy(true);
    try {
      closePreview();
      const {data} = await studioApi.file(videoId);
      const url = URL.createObjectURL(data);
      previewUrl.current = url; setVideoPreview(url);
    } catch(e) {setMessage(apiError(e));} finally {setMediaBusy(false);}
  };

  useEffect(() => {
    if (!story || translation.state !== 'PENDING' || dirty || saving) return;
    const timer = setInterval(async () => {
      try {
        const {data} = await storyApi.graph(story.id);
        setTranslation(data.translation_state || {state:'NONE', pending:0, failed:0, translated:0});
        setNodeIdMap(data.node_id_map || {});
        if (data.revision !== revision) {
          setNodes(data.graph.nodes);setEdges(data.graph.edges);setRevision(data.revision);setDraftId(data.draft_id);
        }
      } catch { /* conserver les données locales si le polling échoue */ }
    }, 6000);
    return () => clearInterval(timer);
  }, [story?.id, translation.state, dirty, saving, revision]);

  if (!story) return <Panel title="Aucun Tantara"><p>Créez d’abord une histoire.</p></Panel>;
  return <div className="page-stack">
    {message && <div role="status" className="api-banner">{message}</div>}
    <div className="tree-bar">
      <div className="inline-fields"><Field label="Histoire"><select value={story.id} onChange={e => {if (dirty && !confirm('Abandonner les changements non enregistrés ?')) return;setParams({story:e.target.value});}}>{stories.map(s => <option value={s.id} key={s.id}>{s.title}</option>)}</select></Field><span className="subtle-vertical"/><span className="tree-counter">{nodes.length} nœuds · {edges.length} liaisons · {translation.state === 'PENDING' ? `MG en file (${translation.pending})` : translation.state === 'FAILED' ? 'MG en erreur' : translation.state === 'REVIEW_REQUIRED' ? 'MG à relire' : 'FR → MG automatique'}</span></div>
      <div className="tree-toolbar-actions">
        {translation.state === 'FAILED' && draftId && <button className="btn btn-outline" onClick={async () => {try {await translationApi.retry('content_api.BrouillonGraphe', draftId);setTranslation(p => ({...p,state:'PENDING'}));setMessage('Traduction relancée.');} catch(e) {setMessage(apiError(e));}}}><RefreshCw size={15}/> Relancer MG</button>}
        {selectedEdge && <button className="btn btn-danger" type="button" onClick={deleteLink}><Link2Off size={15}/> Supprimer le lien</button>}
        <button className="btn btn-outline" onClick={apply} disabled={saving || loading || dirty || ['PENDING','FAILED'].includes(translation.state)}>Appliquer au backend</button>
        <button className="btn btn-primary" onClick={save} disabled={saving || loading || !dirty}><Save size={17}/> {saving ? 'Traitement…' : dirty ? 'Enregistrer' : 'Enregistré'}</button>
      </div>
    </div>
    <div className="tree-layout">
      <Panel title="Éditeur narratif" icon={GitBranch} className="flow-panel" action={<div className="flow-add"><button title="Ajouter une scène" onClick={() => addNode('scene')}><Plus size={15}/> Scène</button><button title="Ajouter une décision" onClick={() => addNode('decision')}><Plus size={15}/> Décision</button><button title="Ajouter une fin" onClick={() => addNode('ending')}><Plus size={15}/> Fin</button></div>}>
        <p className="flow-toolbar-hint">Clique sur une liaison pour la supprimer. Pour changer sa destination, reconnecte la même sortie. Scène → Décision → Scène → Décision est autorisé.</p>
        <div className="flow-canvas">{loading ? <div className="loading-screen">Chargement du graphe…</div> : <ReactFlow
          nodes={flowNodes} edges={flowEdges} nodeTypes={nodeTypes}
          onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          onConnect={onConnect} isValidConnection={isValidConnection}
          onEdgeClick={(_, edge) => {setSelectedEdgeId(edge.id);setSelectedId(null);}}
          onNodeClick={(_, node) => {setSelectedId(node.id);setSelectedEdgeId(null);}}
          onPaneClick={() => {setSelectedId(null);setSelectedEdgeId(null);}}
          deleteKeyCode={['Backspace','Delete']}
          fitView nodesConnectable elementsSelectable snapToGrid snapGrid={[15,15]}
          defaultEdgeOptions={{type:'smoothstep',style:{stroke:'#40aefc',strokeWidth:1.7}}} colorMode="dark">
          <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#23344e"/><Controls showInteractive={false}/>
        </ReactFlow>}</div>
      </Panel>
      <Panel title={selectedEdge ? 'Propriétés de la liaison' : 'Propriétés du nœud'} icon={selectedEdge ? GitBranch : BookOpen} className="inspector-panel">
        {selectedEdge ? <div className="inspector-fields">
          <div className="inspector-badge">LIAISON SÉLECTIONNÉE</div>
          <div className="link-details"><span>De</span><strong>{nodes.find(n => n.id === selectedEdge.source)?.data?.title?.fr || selectedEdge.source}</strong><span>Vers</span><strong>{nodes.find(n => n.id === selectedEdge.target)?.data?.title?.fr || selectedEdge.target}</strong></div>
          <button className="btn btn-danger full-width" onClick={deleteLink}><Link2Off size={16}/> Supprimer cette liaison</button>
          <p className="form-hint">Le changement reste local jusqu’à « Enregistrer ». Une branche manquante sera signalée dans la validation.</p>
        </div> : selected ? <div className="inspector-fields">
          <div className="inspector-badge">{selected.data.kind === 'ending' ? 'FIN' : selected.data.kind === 'scene' ? 'SCÈNE' : 'DÉCISION'}</div>
          <p className="form-hint">Français uniquement · Malagasy généré dans la file de traduction.</p>
          <Field label="Titre" required><input required value={selected.data.title?.fr || ''} onChange={e => modifySelected({title:{...selected.data.title,fr:e.target.value}})}/></Field>
          <Field label="Texte" required><textarea required rows={4} value={selected.data.text?.fr || ''} onChange={e => modifySelected({text:{...selected.data.text,fr:e.target.value}})}/></Field>
          {selected.data.kind === 'decision' && <Field label="Poids de la décision" required><input type="number" min="1" max="100" required value={selected.data.weight || 20} onChange={e => modifySelected({weight:Number(e.target.value) || 20})}/></Field>}
          {selected.data.kind === 'decision' && <div className="option-editor"><div className="panel-title">Choix (2 à 3)</div>
            {(selected.data.options || []).map((o,i) => <div key={o.id} className="option-edit-row"><input required aria-label={`Choix ${i+1}`} value={o.label?.fr || ''} onChange={e => modifySelected({options:selected.data.options.map(x => x.id === o.id ? {...x,label:{...x.label,fr:e.target.value}} : x)})}/><button className="icon-button" title="Retirer ce choix et sa liaison" disabled={selected.data.options.length <= 2} onClick={() => {modifySelected({options:selected.data.options.filter(x => x.id !== o.id)});setEdges(es => es.filter(e => !(e.source === selected.id && e.sourceHandle === o.id)));}}><Trash2 size={14}/></button></div>)}
            {(selected.data.options || []).map((o,i) => <div key={`${o.id}-feedback`} className="option-feedback-row"><label>Retour pédagogique {i+1} <span className="required-asterisk">*</span><textarea required rows={2} value={o.feedback?.fr || ''} onChange={e => modifySelected({options:selected.data.options.map(x => x.id === o.id ? {...x,feedback:{...x.feedback,fr:e.target.value}} : x)})}/></label><label>Qualité (0–1) <span className="required-asterisk">*</span><input required type="number" min="0" max="1" step="0.1" value={o.quality ?? 0} onChange={e => modifySelected({options:selected.data.options.map(x => x.id === o.id ? {...x,quality:Number(e.target.value)} : x)})}/></label></div>)}
            <button className="btn btn-outline full-width" onClick={addOption} disabled={(selected.data.options || []).length >= 3}><Plus size={15}/> Ajouter un choix</button>
          </div>}
          {['scene','ending'].includes(selected.data.kind) && <div className="node-media-editor">
            <div className="panel-title"><Clapperboard size={16}/> Image / vidéo de la scène</div>
            <p className="form-hint">Sélectionne un fichier dès le brouillon. L'association sera conservée puis créée dans Django lorsque tu appliqueras l'arbre.</p>
            <Field label="Média de la médiathèque">
              <select value={selected.data.media?.asset || ''} onChange={e => {
                const asset = availableAssets.find(a => String(a.id) === e.target.value);
                modifySelected({media: asset ? {asset:String(asset.id),kind:asset.type} : null});
              }}>
                <option value="">{existingSceneMedia?.video || existingSceneMedia?.image ? 'Média actuel déjà associé dans Django' : 'Sans média (texte seulement)'}</option>
                {availableAssets.map(asset => <option key={asset.id} value={asset.id}>{asset.type === 'IMAGE' ? '🖼' : '🎬'} {asset.titre}</option>)}
              </select>
            </Field>
            {!availableAssets.length && <p className="form-hint">Importe d'abord une image ou une vidéo avec droits confirmés dans la médiathèque.</p>}
            {!!selected.data.media?.asset && <div className="media-link-status">Média choisi : {availableAssets.find(m => String(m.id) === String(selected.data.media.asset))?.titre || 'Référence introuvable'} · en attente d’application</div>}
            <p className="form-hint">Après « Enregistrer » puis « Appliquer au backend », configure la voix FR ou MG dans « Voix & audio ».</p>
            <hr className="subtle-divider" />
            <div className="panel-title"><Clapperboard size={16}/> Vidéo du nœud</div>
            {!dbNodeId || dirty ? <p className="form-hint">Tu peux déjà choisir une image/vidéo ci-dessus et enregistrer le brouillon. L'application de l'arbre exige les décisions attendues et les traductions FR/MG validées.</p> : <>
              <Field label="Langue"><select value={videoLang} onChange={e => setVideoLang(e.target.value)}><option value="fr">Français</option><option value="mg">Malagasy</option></select></Field>
              <Field label="Vidéo de la médiathèque"><select value={videoId} onChange={e => {closePreview();setVideoId(e.target.value);}}><option value="">Choisir une vidéo</option>{availableVideos.map(m => <option key={m.id} value={m.id}>{m.titre}</option>)}</select></Field>
              <div className="node-media-upload">
                <strong>Ou importer une vidéo</strong>
                <input ref={uploadInput} aria-label="Fichier vidéo à importer" type="file" accept=".mp4,.mov,.webm,video/mp4,video/quicktime,video/webm" onChange={e => setUploadFile(e.target.files?.[0] || null)}/>
                {uploadFile && <>
                  <Field label="Licence / provenance" required><input required maxLength={160} placeholder="Ex. création originale" value={uploadLicence} onChange={e => setUploadLicence(e.target.value)}/></Field>
                  <label className="checkbox-line"><input type="checkbox" checked={uploadRights} onChange={e => setUploadRights(e.target.checked)}/> Je confirme les droits et le caractère fictif de ce média.</label>
                  <button className="btn btn-outline full-width" onClick={uploadVideo} disabled={mediaBusy || !uploadRights || !uploadLicence.trim()}>Importer dans la médiathèque</button>
                </>}
              </div>
              <div className="media-inspector-actions"><button className="btn btn-outline" onClick={previewVideo} disabled={!videoId || mediaBusy}><Play size={14}/> Aperçu</button><button className="btn btn-primary" onClick={saveVideo} disabled={!videoId || !currentLanguage || mediaBusy}><Save size={14}/> Associer</button></div>
              {videoPreview && <video className="node-video-preview" src={videoPreview} controls playsInline/>}
              {existingSceneMedia?.video && <div className="media-link-status"><span>Vidéo liée · {existingSceneMedia.statut}</span><button className="btn btn-outline" onClick={renderVideo} disabled={mediaBusy || existingSceneMedia.statut === 'PROCESSING'}>Lancer le rendu</button><button className="btn btn-outline" onClick={removeVideo} disabled={mediaBusy}><Link2Off size={14}/> Retirer</button></div>}
              {!availableVideos.length && <p className="form-hint">Aucune vidéo importée et validée.</p>}
            </>}
            <Link className="btn btn-outline full-width" to="/medias"><Video size={15}/> Ouvrir la médiathèque</Link>
            <p className="form-hint">Les fichiers restent privés. Le rendu FFmpeg validé sera utilisé pour la publication.</p>
          </div>}
          <button className="btn btn-danger full-width" onClick={deleteNode}><Trash2 size={16}/> Supprimer ce nœud</button>
        </div> : <div className="inspector-placeholder"><GitBranch size={28}/><strong>Sélectionner un nœud ou un lien</strong><p>Pour retirer une liaison, clique sur sa ligne puis sur « Supprimer ». Pour ajouter une vidéo, sélectionne une scène ou une fin.</p></div>}
      </Panel>
    </div>
    <Panel title="Validation de l’histoire" icon={issues.length ? Unplug : CheckCircle2}>
      {issues.length ? <div className="validation-list">{issues.slice(0, 6).map((s,i) => <span key={i} className="validation-item">● {s}</span>)}{issues.length > 6 && <span>+ {issues.length - 6} autres vérifications</span>}</div> : <div className="validation-success"><CheckCircle2 size={18}/> Contrôles visuels satisfaits ; appliquer au backend pour les validations métier complètes.</div>}
    </Panel>
  </div>;
}
