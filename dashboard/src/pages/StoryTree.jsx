import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Background, BackgroundVariant, Controls, Handle, Position, ReactFlow, addEdge, applyEdgeChanges, applyNodeChanges } from '@xyflow/react';
import { BookOpen, CheckCircle2, Flag, GitBranch, Plus, RefreshCw, Save, Trash2, Unplug } from 'lucide-react';
import { Field, Panel, Status } from '../components/UI';
import { useAdmin } from '../lib/store';
import { storyApi,translationApi } from '../services/editor';
import { newGraph } from '../data/seed';
import { apiError } from '../services/api';

const nodeTypes = { story: StoryNode };
function StoryNode({ data, selected }) {
  const icon = data.kind === 'decision' ? <GitBranch size={17}/> : data.kind === 'ending' ? <Flag size={17}/> : <BookOpen size={17}/>;
  return <div className={`flow-node flow-${data.kind} ${selected?'flow-selected':''}`}>
    <Handle type="target" position={Position.Top} id="in" />
    <div className="flow-node-header">{icon}<span>{data.kind === 'decision' ? 'DÉCISION' : data.kind === 'ending' ? 'FIN' : 'SCÈNE'}</span></div>
    <strong>{data.title?.fr || 'Sans titre'}</strong>
    <small>{data.text?.fr || 'Cliquer pour modifier'}</small>
    {data.kind === 'decision' ? <div className="flow-options">{(data.options || []).map(opt => <div key={opt.id} className="flow-option">{opt.label?.fr || 'Choix'}<Handle type="source" id={opt.id} position={Position.Bottom} style={{left:`${12+Math.round(((data.options || []).indexOf(opt)+1)*76/((data.options || []).length+1))}%`,bottom:-6}}/></div>)}</div> : data.kind !== 'ending' && <Handle type="source" position={Position.Bottom} id="out" />}
  </div>;
}

function validateGraph(graph) {
  const nodes = graph?.nodes || [], edges = graph?.edges || [];
  if (!nodes.length) return ['Aucun nœud'];
  const ids = new Set(nodes.map(n => n.id));
  const issues = [];
  if (!nodes.some(n => n.data.kind === 'ending')) issues.push('Ajouter au moins une fin');
  for (const edge of edges) if (!ids.has(edge.source) || !ids.has(edge.target)) issues.push('Liaison sans destination valide');
  for (const n of nodes) {
    if (!n.data.title?.fr?.trim()) issues.push(`Titre FR manquant : ${n.id}`);

    if (n.data.kind === 'scene' && !edges.some(e=>e.source===n.id)) issues.push(`Scène non reliée : ${n.id}`);
    if (n.data.kind === 'decision') for (const opt of n.data.options || []) if (!edges.some(e=>e.source===n.id && e.sourceHandle===opt.id)) issues.push(`Choix non relié : ${opt.label?.fr || opt.id}`);
  }
  return [...new Set(issues)];
}

export default function StoryTree() {
  const { stories, refresh } = useAdmin();
  const [revision,setRevision]=useState(0);
  const [loading,setLoading]=useState(false);
  const [saving,setSaving]=useState(false);
  const [message,setMessage]=useState('');
  const [params, setParams] = useSearchParams();
  const story = stories.find(s=>s.id === params.get('story')) || stories[0];
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const language = 'fr';
  const [translation,setTranslation]=useState({state:'NONE',pending:0,failed:0,translated:0});
  const [draftId,setDraftId]=useState(null);
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    let active=true;
    if(!story) return;
    setLoading(true);setMessage('');setSelectedId(null);setDirty(false);
    storyApi.graph(story.id).then(({data})=>{
      if(!active)return;
      const isNew=!data.graph?.nodes?.length;
      const graph=isNew ? newGraph(story.title) : data.graph;
      setNodes(graph.nodes);setEdges(graph.edges);setRevision(data.revision || 0);setDraftId(data.draft_id);setTranslation(data.translation_state||{state:'NONE',pending:0,failed:0,translated:0});
      setDirty(isNew);
    }).catch(e=>{if(active)setMessage(apiError(e))}).finally(()=>{if(active)setLoading(false)});
    return ()=>{active=false};
  }, [story?.id]);
  const selected = nodes.find(n=>n.id===selectedId);
  const issues = useMemo(()=>validateGraph({nodes,edges}),[nodes,edges]);
  const onNodesChange = useCallback(changes=>{setNodes(old=>applyNodeChanges(changes,old));if(changes.some(c=>c.type!=='select'))setDirty(true);},[]);
  const onEdgesChange = useCallback(changes=>{setEdges(old=>applyEdgeChanges(changes,old));setDirty(true);},[]);
  const onConnect = useCallback(connection=>{setEdges(old=>addEdge({...connection,type:'smoothstep',animated:true},old));setDirty(true);},[]);
  const modifySelected = (patch) => { setNodes(prev => prev.map(n => n.id===selectedId ? {...n,data:{...n.data,...patch}} : n)); setDirty(true); };
  const addNode = kind => {
    const id = `${kind}-${Date.now()}`;
    const node = { id, type:'story', position:{ x: 180+(nodes.length%3)*185, y: 120+nodes.length*58 }, data: {kind,title:{fr:`Nouvelle ${kind==='scene'?'scène':kind==='decision'?'décision':'fin'}`,mg:''}, text:{fr:'',mg:''},...(kind==='decision'?{options:[{id:`option-${Date.now()}`,label:{fr:'Choix 1',mg:''},feedback:{fr:'',mg:''},quality:0}]}:{})} };
    setNodes(prev=>[...prev,node]);setSelectedId(id);setDirty(true);
  };
  const addOption = () => {
    if (!selected || selected.data.kind !== 'decision') return;
    const options = [...(selected.data.options||[]),{id:`opt-${Date.now()}`,label:{fr:`Choix ${(selected.data.options||[]).length+1}`,mg:''},feedback:{fr:'',mg:''},quality:0}];
    modifySelected({options});
  };
  const deleteNode = () => {if(!selected)return;setNodes(prev=>prev.filter(n=>n.id!==selectedId));setEdges(prev=>prev.filter(e=>e.source!==selectedId && e.target!==selectedId));setSelectedId(null);setDirty(true);};
  const save = async () => {
    if(!story||saving)return;
    setSaving(true);setMessage('');
    try {
      const {data}=await storyApi.saveGraph(story.id,{nodes,edges},revision);
      setRevision(data.revision);setDraftId(data.draft_id);setTranslation(data.translation_state||{state:'NONE',pending:0,failed:0,translated:0});setDirty(false);
      setMessage('Brouillon enregistré. La traduction malgache continue en arrière-plan.');
    } catch(e){setMessage(apiError(e));}
    finally{setSaving(false)}
  };
  const apply = async () => {
    if(!story||dirty||translation.state==='PENDING'||translation.state==='FAILED')return;
    if(!window.confirm('Appliquer le brouillon graphique aux nœuds relationnels Django ? Les versions déjà publiées restent figées.'))return;
    setSaving(true);setMessage('');
    try {const {data}=await storyApi.applyGraph(story.id);await refresh();setMessage(`${data.nodes} nœuds appliqués. Relecture et approbation encore nécessaires.`)}
    catch(e){setMessage(apiError(e))}finally{setSaving(false)}
  };

  useEffect(()=>{
    if(!story || translation.state!=='PENDING' || dirty || saving)return;
    const timer=setInterval(async()=>{
      try{const {data}=await storyApi.graph(story.id);
        setTranslation(data.translation_state||{state:'NONE',pending:0,failed:0,translated:0});
        if(data.revision!==revision){setNodes(data.graph.nodes);setEdges(data.graph.edges);setRevision(data.revision);setDraftId(data.draft_id)}
      }catch{}
    },6000);return ()=>clearInterval(timer);
  },[story?.id,translation.state,dirty,saving,revision]);

  if (!story) return <Panel title="Aucun Tantara"><p>Créez d’abord une histoire.</p></Panel>;
  return <div className="page-stack">
    {message && <div role="status" className="api-banner">{message}</div>}
    <div className="tree-bar"><div className="inline-fields"><Field label="Histoire"><select value={story.id} onChange={e=>{if(dirty && !confirm('Abandonner les changements non enregistrés ?'))return;setParams({story:e.target.value})}}>{stories.map(s=><option value={s.id} key={s.id}>{s.title}</option>)}</select></Field><span className="subtle-vertical"/><span className="tree-counter">{nodes.length} nœuds · {edges.length} liaisons · {translation.state==='PENDING'?`Traduction MG en file (${translation.pending})`:translation.state==='FAILED'?'Traduction MG en erreur':translation.state==='REVIEW_REQUIRED'?'MG à relire':'FR → MG automatique'}</span></div><div className="tree-toolbar-actions">{translation.state==='FAILED'&&draftId&&<button className="btn btn-outline" onClick={async()=>{try{await translationApi.retry('content_api.BrouillonGraphe',draftId);setTranslation(p=>({...p,state:'PENDING'}));setMessage('Traduction relancée.')}catch(e){setMessage(apiError(e))}}}><RefreshCw size={15}/> Relancer MG</button>}<button className="btn btn-outline" onClick={apply} disabled={saving||loading||dirty||translation.state==='PENDING'||translation.state==='FAILED'}>Appliquer au backend</button><button className="btn btn-primary" onClick={save} disabled={saving||loading||!dirty}><Save size={17}/> {saving?'Traitement…':dirty?'Enregistrer':'Enregistré'}</button></div></div>
    <div className="tree-layout"><Panel title="Éditeur narratif" icon={GitBranch} className="flow-panel" action={<div className="flow-add"><button title="Ajouter une scène" onClick={()=>addNode('scene')}><Plus size={15}/> Scène</button><button title="Ajouter une décision" onClick={()=>addNode('decision')}><Plus size={15}/> Décision</button><button title="Ajouter une fin" onClick={()=>addNode('ending')}><Plus size={15}/> Fin</button></div>}>
      <div className="flow-canvas">{loading?<div className="loading-screen">Chargement du graphe…</div>:<ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} onNodeClick={(_,n)=>setSelectedId(n.id)} onPaneClick={()=>setSelectedId(null)} fitView nodesConnectable elementsSelectable snapToGrid snapGrid={[15,15]} defaultEdgeOptions={{type:'smoothstep',style:{stroke:'#40aefc',strokeWidth:1.7}}} colorMode="dark">
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#23344e"/><Controls showInteractive={false}/>
      </ReactFlow>}</div>
    </Panel><Panel title="Propriétés du nœud" icon={BookOpen} className="inspector-panel">
      {selected ? <div className="inspector-fields"><div className="inspector-badge">{selected.data.kind.toUpperCase()}</div><p className="form-hint">Français uniquement · Malagasy généré dans la file de traduction.</p>
        <Field label="Titre" required><input required value={selected.data.title?.[language]||''} onChange={e=>modifySelected({title:{...selected.data.title,[language]:e.target.value}})}/></Field>
        <Field label="Texte" required><textarea required rows={4} value={selected.data.text?.[language]||''} onChange={e=>modifySelected({text:{...selected.data.text,[language]:e.target.value}})}/></Field>
        {selected.data.kind==='decision'&&<Field label="Poids de la décision" required><input required type="number" min="1" max="100" value={selected.data.weight||20} onChange={e=>modifySelected({weight:Number(e.target.value)||20})}/></Field>}
        {selected.data.kind==='decision'&&<div className="option-editor"><div className="panel-title">Choix</div>{(selected.data.options||[]).map((o,i)=><div key={o.id} className="option-edit-row"><input required aria-label={`Choix ${i+1}`} value={o.label?.[language]||''} onChange={e=>modifySelected({options:selected.data.options.map(x=>x.id===o.id?{...x,label:{...x.label,[language]:e.target.value}}:x)})}/><button title="Retirer le choix" className="icon-button" onClick={()=>{modifySelected({options:selected.data.options.filter(x=>x.id!==o.id)});setEdges(es=>es.filter(e=>!(e.source===selected.id && e.sourceHandle===o.id)));}}><Trash2 size={14}/></button></div>)}{(selected.data.options||[]).map((o,i)=><div key={`${o.id}-feedback`} className="option-feedback-row"><label>Retour pédagogique {i+1} <span className="required-asterisk">*</span><textarea required rows={2} value={o.feedback?.[language]||''} onChange={e=>modifySelected({options:selected.data.options.map(x=>x.id===o.id?{...x,feedback:{...x.feedback,[language]:e.target.value}}:x)})}/></label><label>Qualité (0–1) <span className="required-asterisk">*</span><input required type="number" min="0" max="1" step="0.1" value={o.quality??0} onChange={e=>modifySelected({options:selected.data.options.map(x=>x.id===o.id?{...x,quality:Number(e.target.value)}:x)})}/></label></div>)}<button className="btn btn-outline full-width" onClick={addOption}><Plus size={15}/> Ajouter un choix</button></div>}
        <button className="btn btn-danger full-width" onClick={deleteNode}><Trash2 size={16}/> Supprimer ce nœud</button>
      </div> : <div className="inspector-placeholder"><GitBranch size={28}/><strong>Sélectionner un nœud</strong><p>Rédigez le contenu français et les options. Reliez les points des cartes pour créer une branche.</p></div>}
    </Panel></div>
    <Panel title="Validation de l’histoire" icon={issues.length ? Unplug : CheckCircle2}>
      {issues.length ? <div className="validation-list">{issues.slice(0,6).map((s,i)=><span key={i} className="validation-item">● {s}</span>)}{issues.length>6&&<span>+ {issues.length-6} autres vérifications</span>}</div> : <div className="validation-success"><CheckCircle2 size={18}/> Contrôles visuels satisfaits ; appliquer au backend pour les validations métier complètes.</div>}
    </Panel>
  </div>;
}
