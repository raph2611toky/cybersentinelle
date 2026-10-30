import { useMemo, useRef, useState, useEffect } from 'react';
import { FileAudio2, FileImage, FileVideo2, Grid2x2, List, Search, Trash2, UploadCloud } from 'lucide-react';
import { Dialog, EmptyState, Field, Panel } from '../components/UI';
import { useAdmin } from '../lib/store';
import { studioApi } from '../services/editor';
import { apiError } from '../services/api';

const icons={IMAGE:FileImage, VIDEO:FileVideo2, AUDIO:FileAudio2, SUBTITLE:FileAudio2};
const kindFromFile=f=> f?.type?.startsWith('video/')?'VIDEO':f?.type?.startsWith('image/')?'IMAGE':f?.type?.startsWith('audio/')?'AUDIO':'SUBTITLE';
const mb=n=>`${(Number(n||0)/1048576).toFixed(2)} Mo`;

export default function Media(){
  const {media,perform,busy}=useAdmin();
  const [tab,setTab]=useState('ALL'),[query,setQuery]=useState(''),[layout,setLayout]=useState('grid');
  const [form,setForm]=useState(null),[preview,setPreview]=useState(null),[error,setError]=useState('');
  const [loadingPreview,setLoadingPreview]=useState(false);
  const urlRef=useRef('');
  useEffect(()=>()=>{if(urlRef.current)URL.revokeObjectURL(urlRef.current)},[]);
  const counts=k=>media.filter(m=>m.type===k).length;
  const filtered=useMemo(()=>media.filter(m=>(tab==='ALL'||m.type===tab)&&m.titre.toLowerCase().includes(query.toLowerCase())),[media,tab,query]);
  const choose=f=>{if(!f)return;setError('');setForm({file:f,title:f.name.replace(/\.[^.]+$/,''),type:kindFromFile(f),licence:'',rights:false,langue:''})};
  const upload=async e=>{e.preventDefault();setError('');if(!form?.rights){setError('Confirmez les droits avant import.');return}
    const d=new FormData();d.append('fichier',form.file);d.append('titre',form.title);d.append('type',form.type);d.append('licence',form.licence);d.append('droits_confirmes','true');if(form.langue)d.append('langue',form.langue);
    try{await perform(()=>studioApi.upload(d));setForm(null)}catch(err){setError(err.message)}
  };
  const showPreview=async item=>{
    setError('');setLoadingPreview(true);
    try{
      if(urlRef.current)URL.revokeObjectURL(urlRef.current);
      const {data}=await studioApi.file(item.id);
      urlRef.current=URL.createObjectURL(data);
      setPreview({...item,url:urlRef.current});
    }catch(e){setError(apiError(e))}finally{setLoadingPreview(false)}
  };
  const closePreview=()=>{setPreview(null);if(urlRef.current){URL.revokeObjectURL(urlRef.current);urlRef.current=''}};
  const del=async item=>{if(!confirm(`Supprimer le média « ${item.titre} » ?`))return;try{await perform(()=>studioApi.deleteMedia(item.id));if(preview?.id===item.id)closePreview()}catch(e){setError(e.message)}};
  return <div className="page-stack">
    <div className="section-toolbar"><span className="section-hint">Médiathèque privée Django · droits vérifiés</span><label className="btn btn-primary" style={{cursor:'pointer'}}><UploadCloud size={17}/> Importer un fichier<input type="file" accept="video/*,audio/*,image/*,.srt,.vtt" hidden onChange={e=>{choose(e.target.files?.[0]);e.target.value=''}}/></label></div>
    <div className="stats-grid compact-stats"><div className="media-stat purple-tint"><FileVideo2/><strong>{counts('VIDEO')}</strong><span>Vidéos</span></div><div className="media-stat blue-tint"><FileAudio2/><strong>{counts('AUDIO')}</strong><span>Audios</span></div><div className="media-stat purple-tint"><FileImage/><strong>{counts('IMAGE')}</strong><span>Images</span></div><div className="media-stat blue-tint"><Grid2x2/><strong>{media.length}</strong><span>Fichiers</span></div></div>
    <Panel title="Bibliothèque multimédia" icon={FileImage}>
      <div className="table-toolbar"><div className="filter-tabs">{[['ALL','Tous'],['VIDEO','Vidéos'],['IMAGE','Images'],['AUDIO','Audios'],['SUBTITLE','Sous-titres']].map(([val,label])=><button key={val} onClick={()=>setTab(val)} className={`filter-tab ${tab===val?'selected':''}`}>{label}</button>)}</div><label className="search-control"><Search size={16}/><input placeholder="Rechercher un fichier" value={query} onChange={e=>setQuery(e.target.value)}/></label><div className="view-switch"><button className={layout==='grid'?'active':''} onClick={()=>setLayout('grid')} title="Grille"><Grid2x2 size={17}/></button><button className={layout==='list'?'active':''} onClick={()=>setLayout('list')} title="Liste"><List size={17}/></button></div></div>
      {error&&<div role="alert" className="api-error">{error}</div>}
      {filtered.length?<div className={`media-grid ${layout==='list'?'media-list':''}`}>{filtered.map(item=>{const Icon=icons[item.type]||FileImage;return <article className="media-tile" key={item.id}><button className={`media-thumbnail thumbnail-${item.type.toLowerCase()}`} onClick={()=>showPreview(item)} title="Ouvrir le fichier privé"><Icon size={40}/></button><div className="media-tile-info"><span><strong title={item.titre}>{item.titre}</strong><small>{item.type} · {mb(item.taille_octets)} · {item.langue||'—'}</small></span><button title="Supprimer" className="icon-button" disabled={busy} onClick={()=>del(item)}><Trash2 size={16}/></button></div></article>})}</div>:<EmptyState title="Médiathèque vide" description="Importez un fichier autorisé."/>}
      <div className="table-footer">Les médias privés sont servis via une route staff et une session valide.</div>
    </Panel>
    {loadingPreview&&<div className="loading-screen">Chargement du fichier privé…</div>}
    {preview&&<Dialog title={preview.titre} onClose={closePreview}><div className="file-preview">{preview.type==='IMAGE'?<img src={preview.url} alt={preview.titre}/>:preview.type==='VIDEO'?<video controls src={preview.url}/>:preview.type==='AUDIO'?<audio controls src={preview.url}/>:<a href={preview.url} download>Voir le sous-titre</a>}</div></Dialog>}
    {form&&<Dialog title="Importer un média" onClose={()=>setForm(null)}><form onSubmit={upload} className="form-stack">
      <p className="muted">{form.file.name} · {mb(form.file.size)}</p>
      <Field label="Titre"><input required value={form.title} onChange={e=>setForm(p=>({...p,title:e.target.value}))}/></Field>
      <Field label="Type"><select value={form.type} onChange={e=>setForm(p=>({...p,type:e.target.value}))}><option value="IMAGE">Image</option><option value="VIDEO">Vidéo</option><option value="AUDIO">Audio</option><option value="SUBTITLE">Sous-titres</option></select></Field>
      <Field label="Licence / provenance"><input required maxLength={160} value={form.licence} onChange={e=>setForm(p=>({...p,licence:e.target.value}))} placeholder="Ex. Création originale de l’équipe"/></Field>
      <Field label="Langue facultative"><select value={form.langue} onChange={e=>setForm(p=>({...p,langue:e.target.value}))}><option value="">Sans langue</option><option value="fr">Français</option><option value="mg">Malagasy</option></select></Field>
      <label className="checkbox-line"><input type="checkbox" checked={form.rights} onChange={e=>setForm(p=>({...p,rights:e.target.checked}))}/> Je confirme que nous avons les droits d'utilisation et que le contenu est fictif.</label>
      {error&&<p role="alert" className="api-error">{error}</p>}
      <div className="form-actions"><button type="button" className="btn btn-outline" onClick={()=>setForm(null)}>Annuler</button><button className="btn btn-primary" disabled={busy||!form.rights}>{busy?'Import…':'Importer sur Django'}</button></div>
    </form></Dialog>}
  </div>;
}
