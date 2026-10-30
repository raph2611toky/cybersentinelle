import { useEffect, useMemo, useRef, useState } from 'react';
import { FileAudio2, FileImage, FileVideo2, Grid2x2, List, Plus, Search, Trash2, UploadCloud } from 'lucide-react';
import { EmptyState, Panel } from '../components/UI';

const demo = [
  { id:'demo-video', name:'Introduction — Aza zaraina', kind:'video', size:'Vidéo de démonstration', demo:true },
  { id:'demo-image', name:'Illustration de scène', kind:'image', size:'Image de démonstration', demo:true },
  { id:'demo-audio', name:'Narration FR', kind:'audio', size:'Audio de démonstration', demo:true },
];
const kindOf = file => file.type.startsWith('image/')?'image':file.type.startsWith('video/')?'video':file.type.startsWith('audio/')?'audio':null;
const icons = { image:FileImage, video:FileVideo2, audio:FileAudio2 };

export default function Media() {
  const inputRef=useRef(null);
  const objectUrls = useRef(new Set());
  const [items,setItems]=useState(demo);
  const [tab,setTab]=useState('all');
  const [search,setSearch]=useState('');
  const [layout,setLayout]=useState('grid');
  const [preview,setPreview]=useState(null);
  const fileCount = kind => items.filter(x=>x.kind===kind).length;
  const visible=useMemo(()=>items.filter(i=>(tab==='all'||tab===i.kind)&&i.name.toLowerCase().includes(search.toLowerCase())),[items,search,tab]);
  const importFiles=e=>{
    const files=Array.from(e.target.files||[]);
    const next=files.map(file=>({id:crypto.randomUUID(),name:file.name,kind:kindOf(file),size:`${(file.size/1024/1024).toFixed(2)} Mo`,url:URL.createObjectURL(file),demo:false})).filter(x=>x.kind);
    next.forEach(item => objectUrls.current.add(item.url));
    setItems(old=>[...next,...old]);e.target.value='';
  };
  useEffect(()=>()=>{objectUrls.current.forEach(url=>URL.revokeObjectURL(url));objectUrls.current.clear()},[]);
  const remove=id=>{
    const item=items.find(i=>i.id===id);
    if(item?.url){URL.revokeObjectURL(item.url);objectUrls.current.delete(item.url);}
    setItems(old=>old.filter(x=>x.id!==id));setPreview(p=>p?.id===id?null:p);
  };
  return <div className="page-stack">
    <div className="section-toolbar"><span className="section-hint">Fichiers de démonstration et imports temporaires</span><button className="btn btn-primary" onClick={()=>inputRef.current?.click()}><UploadCloud size={17}/> Importer des médias</button><input ref={inputRef} type="file" accept="video/*,audio/*,image/*" multiple hidden onChange={importFiles}/></div>
    <div className="stats-grid compact-stats"><div className="media-stat purple-tint"><FileVideo2/><strong>{fileCount('video')}</strong><span>Vidéos</span></div><div className="media-stat blue-tint"><FileAudio2/><strong>{fileCount('audio')}</strong><span>Audios</span></div><div className="media-stat purple-tint"><FileImage/><strong>{fileCount('image')}</strong><span>Images</span></div><div className="media-stat blue-tint"><Grid2x2/><strong>{items.length}</strong><span>Total</span></div></div>
    <Panel title="Bibliothèque multimédia" icon={FileImage}>
      <div className="table-toolbar"><div className="filter-tabs">{[['all','Tous'],['video','Vidéos'],['image','Images'],['audio','Audios']].map(([v,label])=><button key={v} onClick={()=>setTab(v)} className={`filter-tab ${tab===v?'selected':''}`}>{label}</button>)}</div><label className="search-control"><Search size={16}/><input placeholder="Rechercher un fichier" value={search} onChange={e=>setSearch(e.target.value)}/></label><div className="view-switch"><button className={layout==='grid'?'active':''} title="Grille" onClick={()=>setLayout('grid')}><Grid2x2 size={17}/></button><button className={layout==='list'?'active':''} title="Liste" onClick={()=>setLayout('list')}><List size={17}/></button></div></div>
      {visible.length ? <div className={`media-grid ${layout==='list'?'media-list':''}`}>{visible.map(item=>{const Icon=icons[item.kind];return <article className="media-tile" key={item.id}><button className={`media-thumbnail thumbnail-${item.kind}`} onClick={()=>setPreview(item)} title="Prévisualiser"><Icon size={40}/>{item.kind==='image'&&item.url&&<img alt="" src={item.url}/>}</button><div className="media-tile-info"><span><strong title={item.name}>{item.name}</strong><small>{item.kind.toUpperCase()} · {item.size}</small></span><button title="Supprimer du catalogue local" className="icon-button" onClick={()=>remove(item.id)}><Trash2 size={16}/></button></div></article>})}</div>:<EmptyState title="Aucun média" description="Importez un fichier ou modifiez les filtres."/>}
      <div className="table-footer">Les fichiers importés restent uniquement dans la mémoire de cet onglet. Pour les conserver, connecter l’API Django.</div>
    </Panel>
    {preview&&<div className="dialog-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setPreview(null)}}><div className="dialog preview-dialog"><div className="dialog-title"><h2>{preview.name}</h2><button className="icon-button" onClick={()=>setPreview(null)}>×</button></div><div className="file-preview">{preview.url&&preview.kind==='image'?<img alt={preview.name} src={preview.url}/>:preview.url&&preview.kind==='video'?<video controls src={preview.url}/>:preview.url&&preview.kind==='audio'?<audio controls src={preview.url}/>:<p>Fichier de démonstration : aucun média réel associé.</p>}</div></div></div>}
  </div>;
}
