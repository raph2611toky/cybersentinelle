import { useState } from 'react';
import { BookOpen, ExternalLink, Pencil, Plus, Search, Trash2 } from 'lucide-react';
import { Dialog, EmptyState, Field, Panel, Status } from '../components/UI';
import { useAdmin } from '../lib/store';

export default function Resources() {
  const {resources, addResource, updateResource, removeResource}=useAdmin();
  const [query,setQuery]=useState('');
  const [dialog,setDialog]=useState(null);
  const [form,setForm]=useState({title:'',type:'Guide',url:''});
  const edit=r=>{setForm({title:r.title,type:r.type,url:r.url||''});setDialog({id:r.id})};
  const create=()=>{setForm({title:'',type:'Guide',url:''});setDialog({})};
  const save=e=>{e.preventDefault();if(!form.title.trim())return;const values={...form,title:form.title.trim(),url:form.url.trim()};if(dialog.id)updateResource(dialog.id,values);else addResource(values);setDialog(null)};
  const markVerified=r=>{
    if (!r.url || !/^https:\/\//i.test(r.url)) return alert('Ajoutez d’abord une adresse HTTPS vérifiée.');
    if (confirm('Avez-vous vérifié personnellement le lien, son organisme et son contenu ?')) updateResource(r.id,{status:'ready'});
  };
  const shown=resources.filter(r=>`${r.title} ${r.type}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="page-stack"><div className="section-toolbar"><span className="section-hint">Annuaire éditorial · aucune donnée de victimes</span><button className="btn btn-primary" onClick={create}><Plus size={17}/> Ajouter une ressource</button></div>
    <Panel title="Ressources et conseils" icon={BookOpen} action={<span className="muted">{resources.length} fiche(s)</span>}>
      <div className="table-toolbar"><label className="search-control"><Search size={16}/><input placeholder="Rechercher une ressource" value={query} onChange={e=>setQuery(e.target.value)}/></label></div>
      {shown.length ? <div className="resource-list">{shown.map(r=><div key={r.id} className="resource-list-row"><span className="resource-list-icon"><BookOpen size={20}/></span><span className="resource-list-main"><strong>{r.title}</strong><small>{r.type} {r.url?`· ${r.url}`:'· Aucun lien associé'}</small></span><Status value={r.status}/><div className="table-actions"><button title="Modifier" onClick={()=>edit(r)}><Pencil size={16}/></button>{r.url&&<a title="Ouvrir" href={r.url} target="_blank" rel="noopener noreferrer"><ExternalLink size={16}/></a>}<button title="Valider" onClick={()=>markVerified(r)} disabled={r.status==='ready'}>✓</button><button title="Supprimer" onClick={()=>{if(confirm('Supprimer cette ressource ?'))removeResource(r.id)}}><Trash2 size={16}/></button></div></div>)}</div>:<EmptyState title="Aucune ressource" description="Ajoutez un guide ou un contact d’orientation."/>}
      <div className="table-footer">Les liens d’aide doivent être contrôlés manuellement avant diffusion.</div>
    </Panel>
    {dialog&&<Dialog title={dialog.id?'Modifier une ressource':'Nouvelle ressource'} onClose={()=>setDialog(null)}><form className="form-stack" onSubmit={save}><Field label="Titre"><input value={form.title} onChange={e=>setForm(f=>({...f,title:e.target.value}))} required maxLength={130}/></Field><Field label="Type"><select value={form.type} onChange={e=>setForm(f=>({...f,type:e.target.value}))}><option>Guide</option><option>Conseil</option><option>Lien externe</option></select></Field><Field label="Lien HTTPS (optionnel)"><input type="url" value={form.url} onChange={e=>setForm(f=>({...f,url:e.target.value}))} placeholder="https://..."/></Field><div className="form-actions"><button type="button" className="btn btn-outline" onClick={()=>setDialog(null)}>Annuler</button><button className="btn btn-primary">Enregistrer</button></div></form></Dialog>}
  </div>;
}
