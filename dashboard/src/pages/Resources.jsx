import { useState } from 'react';
import { BookOpen, ExternalLink, Pencil, Plus, Search, Trash2 } from 'lucide-react';
import { Dialog, EmptyState, Field, Panel, Status } from '../components/UI';
import { useAdmin } from '../lib/store';
import { resourceApi } from '../services/editor';

const blank = { cle:'',titre_fr:'',titre_mg:'',description_fr:'',description_mg:'',action_fr:'',action_mg:'',audience_fr:'',audience_mg:'',kind:'EXTERNAL',href:'',source:'',statut_service:'REVIEW_NEEDED',pour_mineurs:true };
const srcBlank={code:'',nom_fr:'',nom_mg:'',type:'REFERENTIEL_INTERNE',url_officielle:'',dernier_controle_le:''};
const slug=s=>s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'').slice(0,80);

export default function Resources(){
  const {resources,sources,addResource,updateResource,removeResource,perform,busy}=useAdmin();
  const [query,setQuery]=useState('');const [dialog,setDialog]=useState(null);const [form,setForm]=useState(blank);
  const [sourceForm,setSourceForm]=useState(srcBlank);const [error,setError]=useState('');
  const [sourceView,setSourceView]=useState(false);
  const edit=r=>{setError('');setForm(Object.fromEntries(Object.keys(blank).map(k=>[k,r[k]??blank[k]])));setDialog({mode:'edit',id:r.id})};
  const create=()=>{setError('');setForm(blank);setDialog({mode:'create'})};
  const addSource=()=>{setError('');setSourceForm(srcBlank);setDialog({mode:'source'})};
  const save=async e=>{e.preventDefault();setError('');try{
    if(dialog.mode==='source') {
      await perform(()=>resourceApi.createSource({...sourceForm, dernier_controle_le:sourceForm.dernier_controle_le||null}));
    } else if(dialog.mode==='edit')await updateResource(dialog.id,form);
    else await addResource(form);
    setDialog(null);
  }catch(err){setError(err.message)}};
  const markVerified=async r=>{
    if(!r.href && r.kind!=='INTERNAL')return alert('Contact officiel obligatoire.');
    if(!confirm('Avez-vous personnellement vérifié ce contact et la source officielle ?'))return;
    try{await updateResource(r.id,{statut_service:'ACTIVE',verifie_le:new Date().toISOString().slice(0,10),verificateur_role:'Équipe éditoriale'})}catch(err){alert(err.message)}
  };
  const shown=resources.filter(r=>`${r.title} ${r.titre_mg} ${r.kind}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="page-stack">
    <div className="section-toolbar"><div className="filter-tabs"><button className={`filter-tab ${!sourceView?'selected':''}`} onClick={()=>setSourceView(false)}>Ressources ({resources.length})</button><button className={`filter-tab ${sourceView?'selected':''}`} onClick={()=>setSourceView(true)}>Sources ({sources.length})</button></div><button className="btn btn-primary" onClick={sourceView?addSource:create}><Plus size={17}/> {sourceView?'Ajouter une source':'Ajouter une ressource'}</button></div>
    {!sourceView ? <Panel title="Ressources d’aide" icon={BookOpen} action={<span className="muted">Aucune donnée de victime</span>}>
      <div className="table-toolbar"><label className="search-control"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Rechercher une ressource"/></label></div>
      {shown.length?<div className="resource-list">{shown.map(r=><div className="resource-list-row" key={r.id}><span className="resource-list-icon"><BookOpen size={20}/></span><span className="resource-list-main"><strong>{r.title}</strong><small>{r.type} · {r.source_detail?.nom_fr || sources.find(s=>s.id===r.source)?.nom_fr || 'Source à renseigner'}</small></span><Status value={r.status}/><div className="table-actions"><button title="Modifier" onClick={()=>edit(r)}><Pencil size={16}/></button>{r.url?.startsWith('https://')&&<a href={r.url} target="_blank" rel="noopener noreferrer" title="Lien officiel"><ExternalLink size={16}/></a>}<button title="Vérifier" onClick={()=>markVerified(r)} disabled={r.statut_service==='ACTIVE'}>✓</button><button title="Supprimer" onClick={async()=>{if(confirm('Supprimer définitivement ?'))try{await removeResource(r.id)}catch(e){alert(e.message)}}}><Trash2 size={16}/></button></div></div>)}</div>:<EmptyState title="Aucune ressource" description="Ajoutez une ressource ou modifiez la recherche."/>}
      <div className="table-footer">La validation de sécurité et de provenance s’effectue côté Django.</div>
    </Panel>:<Panel title="Organismes et sources" icon={BookOpen}><div className="resource-list">{sources.map(s=><div className="resource-list-row" key={s.id}><span className="resource-list-icon"><BookOpen size={20}/></span><span className="resource-list-main"><strong>{s.nom_fr}</strong><small>{s.type} · {s.url_officielle||'Référentiel interne'} · {s.dernier_controle_le||'Non vérifié'}</small></span><div className="table-actions"><button onClick={async()=>{if(confirm(`Supprimer ${s.nom_fr} ?`))try{await perform(()=>resourceApi.deleteSource(s.id))}catch(e){alert(e.message)}}}><Trash2 size={16}/></button></div></div>)}</div></Panel>}
    {dialog&&<Dialog title={dialog.mode==='source'?'Nouvelle source':dialog.mode==='edit'?'Modifier la ressource':'Nouvelle ressource'} onClose={()=>setDialog(null)}>
      <form className="form-stack" onSubmit={save}>
      {dialog.mode==='source'?<>
        <div className="form-two"><Field label="Code unique"><input required value={sourceForm.code} onChange={e=>setSourceForm(p=>({...p,code:slug(e.target.value)}))}/></Field><Field label="Type"><select value={sourceForm.type} onChange={e=>setSourceForm(p=>({...p,type:e.target.value}))}><option value="REFERENTIEL_INTERNE">Référentiel interne</option><option value="SERVICE_PUBLIC">Service public</option><option value="INSTITUTION">Institution</option><option value="ONG">ONG</option><option value="AUTRE_ORGANISATION">Autre organisme</option></select></Field></div>
        <div className="form-two"><Field label="Nom FR"><input required value={sourceForm.nom_fr} onChange={e=>setSourceForm(p=>({...p,nom_fr:e.target.value}))}/></Field><Field label="Nom MG"><input required value={sourceForm.nom_mg} onChange={e=>setSourceForm(p=>({...p,nom_mg:e.target.value}))}/></Field></div>
        {sourceForm.type!=='REFERENTIEL_INTERNE'&&<Field label="URL officielle HTTPS"><input type="url" required value={sourceForm.url_officielle} onChange={e=>setSourceForm(p=>({...p,url_officielle:e.target.value}))}/></Field>}
        <Field label="Dernier contrôle de la source"><input type="date" value={sourceForm.dernier_controle_le} onChange={e=>setSourceForm(p=>({...p,dernier_controle_le:e.target.value}))}/></Field>
      </>:<>
        <div className="form-two"><Field label="Clé unique"><input required value={form.cle} onChange={e=>setForm(p=>({...p,cle:slug(e.target.value)}))}/></Field><Field label="Type"><select value={form.kind} onChange={e=>setForm(p=>({...p,kind:e.target.value,href:e.target.value==='INTERNAL'?'':p.href}))}><option value="EXTERNAL">Site officiel HTTPS</option><option value="CALL">Numéro d'aide (tel:)</option><option value="INTERNAL">Conseil interne</option></select></Field></div>
        {[['titre','Titre'],['description','Description'],['action','Action conseillée'],['audience','Public concerné']].map(([k,label])=><div className="form-two" key={k}><Field label={`${label} FR`}><textarea rows={2} required value={form[`${k}_fr`]} onChange={e=>setForm(p=>({...p,[`${k}_fr`]:e.target.value}))}/></Field><Field label={`${label} MG`}><textarea rows={2} required value={form[`${k}_mg`]} onChange={e=>setForm(p=>({...p,[`${k}_mg`]:e.target.value}))}/></Field></div>)}
        <Field label="Source officielle"><select required value={form.source} onChange={e=>setForm(p=>({...p,source:e.target.value}))}><option value="">Choisir</option>{sources.map(s=><option value={s.id} key={s.id}>{s.nom_fr} ({s.type})</option>)}</select></Field>
        {form.kind!=='INTERNAL'&&<Field label={form.kind==='CALL'?'Téléphone (tel:+...)':'URL HTTPS'}><input required value={form.href} onChange={e=>setForm(p=>({...p,href:e.target.value}))} placeholder={form.kind==='CALL'?'tel:+261...':'https://...'}/></Field>}
      </>}
      {error&&<p className="api-error" role="alert">{error}</p>}
      <div className="form-actions"><button type="button" className="btn btn-outline" onClick={()=>setDialog(null)}>Annuler</button><button className="btn btn-primary" disabled={busy}>{busy?'Enregistrement…':'Enregistrer'}</button></div>
      </form>
    </Dialog>}
  </div>;
}
