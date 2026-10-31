import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { BookOpen, Eye, GitBranch, ImagePlus, Pencil, Plus, RefreshCw, Search, Send, Trash2, X } from 'lucide-react';
import { Dialog, EmptyState, Field, Panel, StatCard, Status } from '../components/UI';
import { useAdmin } from '../lib/store';
import { translationApi, publicationApi } from '../services/editor';
import { apiError } from '../services/api';

const fields=[
  ['titre','Titre'],['sous_titre','Sous-titre'],['theme','Thème'],
  ['description','Description'],['avertissement','Avertissement sensible']
];
const empty={slug:'',numero:'',titre_fr:'',sous_titre_fr:'',theme_fr:'',description_fr:'',avertissement_fr:'',duree:'5 min',decisions_attendues:1,palette:'default',ordre:0};
const toMinutes = d => {const n=parseInt((String(d||'5').match(/\d+/)?.[0]||'5'),10); return Number.isFinite(n)?Math.max(1,Math.min(180,n)):5};
function slug(s){return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'').slice(0,40)}
function nextNumber(stories){const nums=new Set(stories.map(s=>s.numero));for(let i=1;i<=99;i++){const n=String(i).padStart(2,'0');if(!nums.has(n))return n;}return ''}

export default function Tantara(){
  const {stories,releases,nodes,scenes,languages,addStory,updateStory,removeStory,perform,busy}=useAdmin();
  const navigate=useNavigate();const [params]=useSearchParams();
  const [search,setSearch]=useState(params.get('q')||'');
  const [status,setStatus]=useState('all');
  const [modal,setModal]=useState(null);
  const [form,setForm]=useState(empty);
  const [minutes,setMinutes]=useState(5);
  const [coverFile,setCoverFile]=useState(null);
  const [removeCover,setRemoveCover]=useState(false);
  const [coverBlobUrl,setCoverBlobUrl]=useState('');
  useEffect(()=>{
    if(!coverFile){setCoverBlobUrl('');return;}
    const url=URL.createObjectURL(coverFile);
    setCoverBlobUrl(url);
    return ()=>URL.revokeObjectURL(url);
  },[coverFile]);
  const coverPreview=coverBlobUrl || (!removeCover ? modal?.coverUrl : null);
  const setNewCover=file=>{
    setActionError('');
    if(!file){setCoverFile(null);return;}
    if(!['image/png','image/jpeg','image/webp'].includes(file.type)){
      setCoverFile(null);setActionError('Format non accepté : PNG, JPEG ou WebP uniquement.');return;
    }
    if(file.size===0 || file.size>5*1024*1024){
      setCoverFile(null);setActionError('La couverture doit être comprise entre 1 octet et 5 Mo.');return;
    }
    setRemoveCover(false);
    setCoverFile(file);
  };

  const [actionError,setActionError]=useState('');
  const [publishTarget,setPublishTarget]=useState(null);
  const [releaseNumber,setReleaseNumber]=useState('');
  const [publishCheck,setPublishCheck]=useState({state:'idle',message:''});
  const [preflightRevision,setPreflightRevision]=useState(0);
  useEffect(()=>{
    if (!publishTarget) {setPublishCheck({state:'idle',message:''});return;}
    let active=true;
    setPublishCheck({state:'checking',message:''});
    publicationApi.validate().then(()=>{
      if(active)setPublishCheck({state:'valid',message:'Contrôles Django réussis. La publication peut être lancée.'});
    }).catch(error=>{
      if(active)setPublishCheck({state:'invalid',message:apiError(error)});
    });
    return ()=>{active=false;};
  },[publishTarget?.id,preflightRevision]);
  const localPublishIssues = useMemo(()=>{
    if (!publishTarget) return [];
    const matching = nodes.filter(node=>String(node.tantara)===String(publishTarget.id));
    const decisionCount = matching.filter(node=>node.type==='DECISION').length;
    const frenchId = languages.find(l=>l.code==='fr')?.id;
    const audiovisual = matching.filter(node=>['SCENE','ENDING'].includes(node.type));
    const missing = audiovisual.filter(node=>!scenes.some(scene=>String(scene.noeud)===String(node.id) && String(scene.langue)===String(frenchId) && scene.statut==='READY' && scene.audio_finale));
    const issues=[];
    if (decisionCount < Number(publishTarget.decisions_attendues)) issues.push(`${decisionCount} nœud(s) décision dans l'arbre pour ${publishTarget.decisions_attendues} décisions exigées sur chaque chemin.`);
    if (missing.length) issues.push(`${missing.length} scène(s)/fin(s) sans piste FR finalisée : ${missing.slice(0,5).map(n=>n.titre_fr||n.cle).join(', ')}${missing.length>5?'…':''}`);
    return issues;
  },[publishTarget,nodes,scenes,languages]);
  const publish=async e=>{e.preventDefault();setActionError('');try{
    // Le contrôle est global : les autres Tantara approuvés comptent aussi.
    await publicationApi.validate();
    await perform(()=>publicationApi.publish({numero:releaseNumber,journal:`Publication depuis Tantara : ${publishTarget.title}`}));
    setPublishTarget(null);
  }catch(err){setActionError(apiError(err));setPublishCheck({state:'invalid',message:apiError(err)})}};
  useEffect(()=>setSearch(params.get('q')||''),[params]);
  const publishedSlugs=useMemo(() => new Set((releases.find(r => r.statut === 'ACTIVE')?.fichiers || []).filter(f => f.type === 'STORY').map(f => f.chemin?.match(/^stories\/([a-z0-9-]+)\.json$/)?.[1]).filter(Boolean)), [releases]);
  const effectiveStatus=s=>publishedSlugs.has(s.slug)?'published':(s.status==='published'?'ready':s.status);
  const filtered=useMemo(()=>stories.filter(s=>(status==='all'||effectiveStatus(s)===status) && `${s.title} ${s.titleMg} ${s.theme}`.toLowerCase().includes(search.toLowerCase())),[stories,search,status,publishedSlugs]);
  const create=()=>{setActionError('');setCoverFile(null);setRemoveCover(false);setMinutes(5);setForm({...empty,numero:nextNumber(stories)});setModal({mode:'create'})};
  const edit=s=>{setActionError('');setCoverFile(null);setRemoveCover(false);setMinutes(toMinutes(s.duree));setForm(Object.fromEntries(Object.keys(empty).map(k=>[k,s[k] ?? empty[k]])));setModal({mode:'edit',id:s.id,coverUrl:s.coverUrl||null})};
  const save=async e=>{
    e.preventDefault();setActionError('');
    const payload={...form,duree:`${minutes} min`,decisions_attendues:Number(form.decisions_attendues),ordre:Number(form.ordre)};
    if(!Number.isInteger(Number(minutes)) || Number(minutes)<1 || Number(minutes)>180){setActionError('Saisis une durée entre 1 et 180 minutes.');return}
    if(modal.mode==='create' && (!payload.slug || !payload.numero)) {setActionError('Un slug et un numéro uniques sont nécessaires.');return}
    if(coverFile)payload.image_cover=coverFile;
    if(removeCover && modal.mode==='edit')payload.effacer_couverture=true;
    try{if(modal.mode==='edit') await updateStory(modal.id,payload);else await addStory(payload);setModal(null);setCoverFile(null);setRemoveCover(false)}
    catch(err){setActionError(err.message)}
  };
  const del=async s=>{if(!window.confirm(`Supprimer définitivement « ${s.title} » et ses nœuds associés ?`))return;try{await removeStory(s.id)}catch(err){alert(err.message)}};
  return <div className="page-stack">
    <div className="section-toolbar"><span className="section-hint">Saisie française · Traduction malgache automatique en file</span><button className="btn btn-primary" onClick={create}><Plus size={17}/> Nouveau Tantara</button></div>
    <div className="stats-grid compact-stats">
      <StatCard icon={BookOpen} label="Total" value={stories.length} note="Histoires" tone="purple"/>
      <StatCard icon={Eye} label="Publiés" value={stories.filter(s=>publishedSlugs.has(s.slug)).length} note="Référencés" tone="blue"/>
      <StatCard icon={Pencil} label="Brouillons" value={stories.filter(s=>effectiveStatus(s)==='draft').length} note="À compléter" tone="purple"/>
      <StatCard icon={GitBranch} label="À relire" value={stories.filter(s=>effectiveStatus(s)==='review').length} note="Contrôles" tone="blue"/>
    </div>
    <Panel title="Histoires" icon={BookOpen} action={<span className="muted">{filtered.length} résultat(s)</span>}>
      <div className="table-toolbar"><label className="search-control"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Chercher un Tantara…"/></label>
        <div className="filter-tabs">{[['all','Tous'],['published','Publiés'],['draft','Brouillons'],['review','À relire']].map(([v,t])=><button key={v} className={`filter-tab ${status===v?'selected':''}`} onClick={()=>setStatus(v)}>{t}</button>)}</div></div>
      {filtered.length?<div className="data-table-wrap"><table className="data-table"><thead><tr><th>Tantara</th><th>Thème</th><th>Révision</th><th>Traduction</th><th>Statut</th><th>Actions</th></tr></thead><tbody>
        {filtered.map(s=><tr key={s.id}><td><div className="story-table-identity">{s.coverUrl?<img className="story-cover-thumb" src={s.coverUrl} alt="" loading="lazy"/>:<span className="story-cover-thumb story-cover-placeholder"><BookOpen size={20}/></span>}<span><strong>{s.title}</strong><small>{s.titre_mg || s.slug}</small></span></div></td><td>{s.theme}</td><td>{s.revision || '1.0'}</td><td><span className={`translation-status translation-${s.translation_state?.state||'NONE'}`}>{({PENDING:'En file',FAILED:'Erreur',REVIEW_REQUIRED:'À relire',NONE:'—'})[s.translation_state?.state||'NONE']}</span></td><td><Status value={effectiveStatus(s)}/></td><td><div className="table-actions">{s.translation_state?.state==='FAILED'&&<button title="Relancer la traduction MG" onClick={async()=>{try{await perform(()=>translationApi.retry('content_api.Tantara',s.id))}catch(e){alert(e.message)}}}><RefreshCw size={16}/></button>}<button className="preview-open-btn" title="Prévisualiser le parcours complet" onClick={()=>navigate(`/previsualisation?story=${encodeURIComponent(s.id)}`)}><Eye size={16}/> Aperçu</button>{['ready','published'].includes(s.status)&&<button className="preview-open-btn" title="Publier une release avec les récits approuvés" disabled={busy} onClick={()=>{setActionError('');setReleaseNumber(new Date().toISOString().replace(/[-:]/g,'').slice(0,15));setPublishTarget(s)}}><Send size={16}/> {publishedSlugs.has(s.slug)?'Republier':'Publier'}</button>}<button title="Éditer les détails" onClick={()=>edit(s)}><Pencil size={16}/></button><button title="Éditer l’arbre" onClick={()=>navigate(`/arbre?story=${encodeURIComponent(s.id)}`)}><GitBranch size={16}/></button><button title="Supprimer" onClick={()=>del(s)}><Trash2 size={16}/></button></div></td></tr>)}
      </tbody></table></div>:<EmptyState title="Aucune histoire" description="Ajoutez un Tantara ou modifiez les filtres."/>}
      <div className="table-footer">Contenus enregistrés sur Django · aucune progression de joueur collectée</div>
    </Panel>
    {publishTarget&&<Dialog title={`Publier ${publishTarget.title}`} onClose={()=>setPublishTarget(null)}><form className="form-stack" onSubmit={publish}>
      <p>Cette release publie les Tantara approuvés, dont cette histoire. Les contrôles du backend restent obligatoires.</p>
      <Field label="Version unique"><input required maxLength={40} pattern="[a-zA-Z0-9][a-zA-Z0-9._-]{0,39}" value={releaseNumber} onChange={e=>setReleaseNumber(e.target.value)}/></Field>
      <div className="publish-preflight" role="status" aria-live="polite">
        <div className="publish-check-heading"><strong>Vérification avant publication</strong><button type="button" className="btn btn-outline" disabled={publishCheck.state==='checking'} onClick={()=>setPreflightRevision(r=>r+1)}>Revérifier</button></div>
        {publishCheck.state==='checking'&&<p>Vérification des contenus auprès de Django…</p>}
        {publishCheck.state==='valid'&&<p className="track-status-ready">{publishCheck.message}</p>}
        {publishCheck.state==='invalid'&&<p className="api-error">{publishCheck.message}</p>}
        {localPublishIssues.map(issue=><p key={issue} className="form-hint">• {issue}</p>)}
        <div className="publish-help-links"><Link to={`/arbre?story=${encodeURIComponent(publishTarget.id)}`} onClick={()=>setPublishTarget(null)}>Corriger le graphe</Link><Link to="/voix" onClick={()=>setPublishTarget(null)}>Préparer les pistes FR</Link></div>
      </div>
      {actionError&&<p role="alert" className="api-error">{actionError}</p>}
      <button className="btn btn-primary" disabled={busy||publishCheck.state!=='valid'}>Confirmer la publication</button>
    </form></Dialog>}
    {modal&&<Dialog title={modal.mode==='create'?'Créer un Tantara':'Modifier le Tantara'} onClose={()=>setModal(null)}><form className="form-stack" onSubmit={save}>
      <p className="form-hint">Rédige en français. Le backend génère les traductions malgaches en arrière-plan ; elles doivent être relues avant publication.</p>
      <div className="form-two"><Field label="Identifiant (slug)" required><input value={form.slug} required maxLength={40} onChange={e=>setForm(p=>({...p,slug:slug(e.target.value)}))}/></Field><Field label="Numéro (01–99)" required><input required maxLength={2} pattern="[0-9]{2}" value={form.numero} onChange={e=>setForm(p=>({...p,numero:e.target.value}))}/></Field></div>
      {fields.map(([key,label])=><Field key={key} label={label} required>{['description','avertissement'].includes(key)?<textarea required rows={2} value={form[`${key}_fr`]} onChange={e=>setForm(p=>({...p,[`${key}_fr`]:e.target.value}))}/>:<input required value={form[`${key}_fr`]} onChange={e=>setForm(p=>({...p,[`${key}_fr`]:e.target.value,...(key==='titre'&&modal.mode==='create'&&!p.slug?{slug:slug(e.target.value)}:{})}))}/>}</Field>)}
      <Field label="Image de couverture (facultatif)">
        <div className="cover-picker">
          <div className="cover-visual">
            {coverPreview ? <img src={coverPreview} alt="Aperçu de la couverture"/> : <div className="cover-no-image"><ImagePlus size={30}/><span>Aucune couverture</span></div>}
          </div>
          <div className="cover-controls">
            <label className="cover-file-label"><ImagePlus size={16}/>{coverPreview ? 'Remplacer l’image' : 'Choisir une image'}
              <input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>{setNewCover(e.target.files?.[0]||null);e.target.value='';}}/>
            </label>
            {coverPreview && <button className="btn btn-outline" type="button" onClick={()=>{setCoverFile(null);setRemoveCover(true)}}><X size={15}/> Retirer</button>}
            <small>PNG, JPEG, WebP · 5 Mo max. · format conseillé 16:9. Illustration fictive, sans données personnelles.</small>
          </div>
        </div>
      </Field>
      <div className="form-two"><Field label="Durée indicative" required><div className="number-with-unit"><input required type="number" inputMode="numeric" min="1" max="180" step="1" value={minutes} onChange={e=>setMinutes(e.target.value===''?'':Number(e.target.value))}/><span>minutes</span></div></Field><Field label="Décisions par parcours" required><input required type="number" min="1" max="30" step="1" value={form.decisions_attendues} onChange={e=>setForm(p=>({...p,decisions_attendues:e.target.value}))}/></Field></div>
      {actionError&&<p role="alert" className="api-error">{actionError}</p>}
      <div className="form-actions"><button type="button" className="btn btn-outline" onClick={()=>setModal(null)}>Annuler</button><button disabled={busy} className="btn btn-primary">{busy?'Enregistrement…':'Enregistrer'}</button></div>
    </form></Dialog>}
  </div>;
}
