import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Background, BackgroundVariant, Controls, Handle, Position, ReactFlow, addEdge, applyEdgeChanges, applyNodeChanges } from '@xyflow/react';
import { BookOpen, CheckCircle2, Flag, GitBranch, Plus, Save, Trash2, Unplug } from 'lucide-react';
import { Field, Panel, Status } from '../components/UI';
import { useAdmin } from '../lib/store';

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
    if (!n.data.title?.mg?.trim()) issues.push(`Titre MG manquant : ${n.id}`);
    if (n.data.kind === 'scene' && !edges.some(e=>e.source===n.id)) issues.push(`Scène non reliée : ${n.id}`);
    if (n.data.kind === 'decision') for (const opt of n.data.options || []) if (!edges.some(e=>e.source===n.id && e.sourceHandle===opt.id)) issues.push(`Choix non relié : ${opt.label?.fr || opt.id}`);
  }
  return [...new Set(issues)];
}

export default function StoryTree() {
  const { stories, updateStory } = useAdmin();
  const [params, setParams] = useSearchParams();
  const story = stories.find(s=>s.id === params.get('story')) || stories[0];
  const [nodes, setNodes] = useState(story?.graph?.nodes || []);
  const [edges, setEdges] = useState(story?.graph?.edges || []);
  const [selectedId, setSelectedId] = useState(null);
  const [language, setLanguage] = useState('fr');
  const [dirty, setDirty] = useState(false);
  useEffect(() => { setNodes(story?.graph?.nodes || []); setEdges(story?.graph?.edges || []); setSelectedId(null); setDirty(false); }, [story?.id]);
  const selected = nodes.find(n=>n.id===selectedId);
  const issues = useMemo(()=>validateGraph({nodes,edges}),[nodes,edges]);
  const onNodesChange = useCallback(changes=>{setNodes(old=>applyNodeChanges(changes,old));if(changes.some(c=>c.type!=='select'))setDirty(true);},[]);
  const onEdgesChange = useCallback(changes=>{setEdges(old=>applyEdgeChanges(changes,old));setDirty(true);},[]);
  const onConnect = useCallback(connection=>{setEdges(old=>addEdge({...connection,type:'smoothstep',animated:true},old));setDirty(true);},[]);
  const modifySelected = (patch) => { setNodes(prev => prev.map(n => n.id===selectedId ? {...n,data:{...n.data,...patch}} : n)); setDirty(true); };
  const addNode = kind => {
    const id = `${kind}-${Date.now()}`;
    const node = { id, type:'story', position:{ x: 180+(nodes.length%3)*185, y: 120+nodes.length*58 }, data: {kind,title:{fr:`Nouvelle ${kind==='scene'?'scène':kind==='decision'?'décision':'fin'}`,mg:''}, text:{fr:'',mg:''},...(kind==='decision'?{options:[{id:`option-${Date.now()}`,label:{fr:'Choix 1',mg:''}}]}:{})} };
    setNodes(prev=>[...prev,node]);setSelectedId(id);setDirty(true);
  };
  const addOption = () => {
    if (!selected || selected.data.kind !== 'decision') return;
    const options = [...(selected.data.options||[]),{id:`opt-${Date.now()}`,label:{fr:`Choix ${(selected.data.options||[]).length+1}`,mg:''}}];
    modifySelected({options});
  };
  const deleteNode = () => {if(!selected)return;setNodes(prev=>prev.filter(n=>n.id!==selectedId));setEdges(prev=>prev.filter(e=>e.source!==selectedId && e.target!==selectedId));setSelectedId(null);setDirty(true);};
  const save = () => {if(!story)return; updateStory(story.id,{graph:{nodes,edges}});setDirty(false);};

  if (!story) return <Panel title="Aucun Tantara"><p>Créez d’abord une histoire.</p></Panel>;
  return <div className="page-stack">
    <div className="tree-bar"><div className="inline-fields"><Field label="Histoire"><select value={story.id} onChange={e=>{if(dirty && !confirm('Abandonner les changements non enregistrés ?'))return;setParams({story:e.target.value})}}>{stories.map(s=><option value={s.id} key={s.id}>{s.title}</option>)}</select></Field><span className="subtle-vertical"/><span className="tree-counter">{nodes.length} nœuds · {edges.length} liaisons</span></div><button className="btn btn-primary" onClick={save} disabled={!dirty}><Save size={17}/> {dirty?'Enregistrer':'Enregistré'}</button></div>
    <div className="tree-layout"><Panel title="Éditeur narratif" icon={GitBranch} className="flow-panel" action={<div className="flow-add"><button title="Ajouter une scène" onClick={()=>addNode('scene')}><Plus size={15}/> Scène</button><button title="Ajouter une décision" onClick={()=>addNode('decision')}><Plus size={15}/> Décision</button><button title="Ajouter une fin" onClick={()=>addNode('ending')}><Plus size={15}/> Fin</button></div>}>
      <div className="flow-canvas"><ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} onNodeClick={(_,n)=>setSelectedId(n.id)} onPaneClick={()=>setSelectedId(null)} fitView nodesConnectable elementsSelectable snapToGrid snapGrid={[15,15]} defaultEdgeOptions={{type:'smoothstep',style:{stroke:'#40aefc',strokeWidth:1.7}}} colorMode="dark">
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#23344e"/><Controls showInteractive={false}/>
      </ReactFlow></div>
    </Panel><Panel title="Propriétés du nœud" icon={BookOpen} className="inspector-panel">
      {selected ? <div className="inspector-fields"><div className="inspector-badge">{selected.data.kind.toUpperCase()}</div><div className="lang-switch"><button className={language==='fr'?'selected':''} onClick={()=>setLanguage('fr')}>Français</button><button className={language==='mg'?'selected':''} onClick={()=>setLanguage('mg')}>Malagasy</button></div>
        <Field label="Titre"><input value={selected.data.title?.[language]||''} onChange={e=>modifySelected({title:{...selected.data.title,[language]:e.target.value}})}/></Field>
        <Field label="Texte"><textarea rows={4} value={selected.data.text?.[language]||''} onChange={e=>modifySelected({text:{...selected.data.text,[language]:e.target.value}})}/></Field>
        {selected.data.kind==='decision'&&<div className="option-editor"><div className="panel-title">Choix</div>{(selected.data.options||[]).map((o,i)=><div key={o.id} className="option-edit-row"><input aria-label={`Choix ${i+1}`} value={o.label?.[language]||''} onChange={e=>modifySelected({options:selected.data.options.map(x=>x.id===o.id?{...x,label:{...x.label,[language]:e.target.value}}:x)})}/><button title="Retirer le choix" className="icon-button" onClick={()=>{modifySelected({options:selected.data.options.filter(x=>x.id!==o.id)});setEdges(es=>es.filter(e=>!(e.source===selected.id && e.sourceHandle===o.id)));}}><Trash2 size={14}/></button></div>)}<button className="btn btn-outline full-width" onClick={addOption}><Plus size={15}/> Ajouter un choix</button></div>}
        <button className="btn btn-danger full-width" onClick={deleteNode}><Trash2 size={16}/> Supprimer ce nœud</button>
      </div> : <div className="inspector-placeholder"><GitBranch size={28}/><strong>Sélectionner un nœud</strong><p>Modifiez le texte, les traductions et les options. Reliez les points des cartes pour créer une branche.</p></div>}
    </Panel></div>
    <Panel title="Validation de l’histoire" icon={issues.length ? Unplug : CheckCircle2}>
      {issues.length ? <div className="validation-list">{issues.slice(0,6).map((s,i)=><span key={i} className="validation-item">● {s}</span>)}{issues.length>6&&<span>+ {issues.length-6} autres vérifications</span>}</div> : <div className="validation-success"><CheckCircle2 size={18}/> Les contrôles de base sont satisfaits. Vérification éditoriale humaine encore nécessaire.</div>}
    </Panel>
  </div>;
}
