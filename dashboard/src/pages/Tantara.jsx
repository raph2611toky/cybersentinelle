import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { BookOpen, Eye, GitBranch, Pencil, Plus, RefreshCw, Search, Trash2 } from 'lucide-react';
import { Dialog, EmptyState, Field, Panel, StatCard, Status } from '../components/UI';
import { useAdmin } from '../lib/store';
import { translationApi } from '../services/editor';

const fields=[
  ['titre','Titre'],['sous_titre','Sous-titre'],['theme','Thème'],
  ['description','Description'],['avertissement','Avertissement sensible']
];
const empty={slug:'',numero:'',titre_fr:'',sous_titre_fr:'',theme_fr:'',description_fr:'',avertissement_fr:'',duree:'5 min',decisions_attendues:1,palette:'default',ordre:0};
const toMinutes = d => {const n=parseInt((String(d||'5').match(/\d+/)?.[0]||'5'),10); return Number.isFinite(n)?Math.max(1,Math.min(180,n)):5};
function slug(s){return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'').slice(0,40)}
function nextNumber(stories){const nums=new Set(stories.map(s=>s.numero));for(let i=1;i<=99;i++){const n=String(i).padStart(2,'0');if(!nums.has(n))return n;}return ''}

export default function Tantara(){
  const {stories,addStory,updateStory,removeStory,perform,busy}=useAdmin();
  const navigate=useNavigate();const [params]=useSearchParams();
  const [search,setSearch]=useState(params.get('q')||'');
  const [status,setStatus]=useState('all');
  const [modal,setModal]=useState(null);
  const [form,setForm]=useState(empty);
  const [minutes,setMinutes]=useState(5);
  const [actionError,setActionError]=useState('');
  useEffect(()=>setSearch(params.get('q')||''),[params]);
  const filtered=useMemo(()=>stories.filter(s=>(status==='all'||s.status===status) && `${s.title} ${s.titleMg} ${s.theme}`.toLowerCase().includes(search.toLowerCase())),[stories,search,status]);
  const create=()=>{setActionError('');setMinutes(5);setForm({...empty,numero:nextNumber(stories)});setModal({mode:'create'})};
  const edit=s=>{setActionError('');setMinutes(toMinutes(s.duree));setForm(Object.fromEntries(Object.keys(empty).map(k=>[k,s[k] ?? empty[k]])));setModal({mode:'edit',id:s.id})};
  const save=async e=>{
    e.preventDefault();setActionError('');
    const payload={...form,duree:`${minutes} min`,decisions_attendues:Number(form.decisions_attendues),ordre:Number(form.ordre)};
    if(!Number.isInteger(Number(minutes)) || Number(minutes)<1 || Number(minutes)>180){setActionError('Saisis une durée entre 1 et 180 minutes.');return}
    if(modal.mode==='create' && (!payload.slug || !payload.numero)) {setActionError('Un slug et un numéro uniques sont nécessaires.');return}
    try{if(modal.mode==='edit') await updateStory(modal.id,payload);else await addStory(payload);setModal(null)}
    catch(err){setActionError(err.message)}
  };
  const del=async s=>{if(!window.confirm(`Supprimer définitivement « ${s.title} » et ses nœuds associés ?`))return;try{await removeStory(s.id)}catch(err){alert(err.message)}};
  return <div className="page-stack">
    <div className="section-toolbar"><span className="section-hint">Saisie française · Traduction malgache automatique en file</span><button className="btn btn-primary" onClick={create}><Plus size={17}/> Nouveau Tantara</button></div>
    <div className="stats-grid compact-stats">
      <StatCard icon={BookOpen} label="Total" value={stories.length} note="Histoires" tone="purple"/>
      <StatCard icon={Eye} label="Publiés" value={stories.filter(s=>s.status==='published').length} note="Référencés" tone="blue"/>
      <StatCard icon={Pencil} label="Brouillons" value={stories.filter(s=>s.status==='draft').length} note="À compléter" tone="purple"/>
      <StatCard icon={GitBranch} label="À relire" value={stories.filter(s=>s.status==='review').length} note="Contrôles" tone="blue"/>
    </div>
    <Panel title="Histoires" icon={BookOpen} action={<span className="muted">{filtered.length} résultat(s)</span>}>
      <div className="table-toolbar"><label className="search-control"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Chercher un Tantara…"/></label>
        <div className="filter-tabs">{[['all','Tous'],['published','Publiés'],['draft','Brouillons'],['review','À relire']].map(([v,t])=><button key={v} className={`filter-tab ${status===v?'selected':''}`} onClick={()=>setStatus(v)}>{t}</button>)}</div></div>
      {filtered.length?<div className="data-table-wrap"><table className="data-table"><thead><tr><th>Tantara</th><th>Thème</th><th>Révision</th><th>Traduction</th><th>Statut</th><th>Actions</th></tr></thead><tbody>
        {filtered.map(s=><tr key={s.id}><td><strong>{s.title}</strong><small>{s.titre_mg || s.slug}</small></td><td>{s.theme}</td><td>{s.revision || '1.0'}</td><td><span className={`translation-status translation-${s.translation_state?.state||'NONE'}`}>{({PENDING:'En file',FAILED:'Erreur',REVIEW_REQUIRED:'À relire',NONE:'—'})[s.translation_state?.state||'NONE']}</span></td><td><Status value={s.status}/></td><td><div className="table-actions">{s.translation_state?.state==='FAILED'&&<button title="Relancer la traduction MG" onClick={async()=>{try{await perform(()=>translationApi.retry('content_api.Tantara',s.id))}catch(e){alert(e.message)}}}><RefreshCw size={16}/></button>}<button title="Éditer les détails" onClick={()=>edit(s)}><Pencil size={16}/></button><button title="Éditer l’arbre" onClick={()=>navigate(`/arbre?story=${encodeURIComponent(s.id)}`)}><GitBranch size={16}/></button><button title="Supprimer" onClick={()=>del(s)}><Trash2 size={16}/></button></div></td></tr>)}
      </tbody></table></div>:<EmptyState title="Aucune histoire" description="Ajoutez un Tantara ou modifiez les filtres."/>}
      <div className="table-footer">Contenus enregistrés sur Django · aucune progression de joueur collectée</div>
    </Panel>
    {modal&&<Dialog title={modal.mode==='create'?'Créer un Tantara':'Modifier le Tantara'} onClose={()=>setModal(null)}><form className="form-stack" onSubmit={save}>
      <p className="form-hint">Rédige en français. Le backend génère les traductions malgaches en arrière-plan ; elles doivent être relues avant publication.</p>
      <div className="form-two"><Field label="Identifiant (slug)" required><input value={form.slug} required maxLength={40} onChange={e=>setForm(p=>({...p,slug:slug(e.target.value)}))}/></Field><Field label="Numéro (01–99)" required><input required maxLength={2} pattern="[0-9]{2}" value={form.numero} onChange={e=>setForm(p=>({...p,numero:e.target.value}))}/></Field></div>
      {fields.map(([key,label])=><Field key={key} label={label} required>{['description','avertissement'].includes(key)?<textarea required rows={2} value={form[`${key}_fr`]} onChange={e=>setForm(p=>({...p,[`${key}_fr`]:e.target.value}))}/>:<input required value={form[`${key}_fr`]} onChange={e=>setForm(p=>({...p,[`${key}_fr`]:e.target.value,...(key==='titre'&&modal.mode==='create'&&!p.slug?{slug:slug(e.target.value)}:{})}))}/>}</Field>)}
      <div className="form-two"><Field label="Durée indicative" required><div className="number-with-unit"><input required type="number" inputMode="numeric" min="1" max="180" step="1" value={minutes} onChange={e=>setMinutes(e.target.value===''?'':Number(e.target.value))}/><span>minutes</span></div></Field><Field label="Décisions par parcours" required><input required type="number" min="1" max="30" step="1" value={form.decisions_attendues} onChange={e=>setForm(p=>({...p,decisions_attendues:e.target.value}))}/></Field></div>
      {actionError&&<p role="alert" className="api-error">{actionError}</p>}
      <div className="form-actions"><button type="button" className="btn btn-outline" onClick={()=>setModal(null)}>Annuler</button><button disabled={busy} className="btn btn-primary">{busy?'Enregistrement…':'Enregistrer'}</button></div>
    </form></Dialog>}
  </div>;
}
