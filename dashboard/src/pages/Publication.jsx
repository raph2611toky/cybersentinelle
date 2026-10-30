import { useState } from 'react';
import { BookOpen, CheckCheck, CircleAlert, GitBranch, Send, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Dialog, Field, Panel, StatCard, Status } from '../components/UI';
import { useAdmin } from '../lib/store';
import { publicationApi } from '../services/editor';
import { apiError } from '../services/api';

const today=()=>new Date().toLocaleDateString('en-CA');
export default function Publication(){
  const {stories,releases,updateStory,perform,busy,refresh}=useAdmin();
  const [message,setMessage]=useState('');const [approve,setApprove]=useState(null);
  const [fields,setFields]=useState({valide_le:today(),validateur_role:'',relecture_fr_le:today(),relecture_mg_le:today(),relecteur_fr_role:'',relecteur_mg_role:''});
  const [publishForm,setPublishForm]=useState({numero:'',journal:''});const [showPublish,setShowPublish]=useState(false);
  const active=releases.find(r=>r.statut==='ACTIVE');
  const validate=async()=>{setMessage('');try{const {data}=await publicationApi.validate();setMessage(`Validation serveur réussie : ${data.files} fichier(s), ${data.visuals} visuel(s).`)}catch(e){setMessage(apiError(e))}};
  const approveStory=async e=>{e.preventDefault();setMessage('');try{await updateStory(approve.id,{...fields,statut_editorial:'APPROUVE'});setApprove(null);setMessage('Récit approuvé après relecture éditoriale.')}catch(e){setMessage(e.message)}};
  const publish=e=>{e.preventDefault();if(!confirm(`Publier la version ${publishForm.numero} ? Cette action active une nouvelle release pour les utilisateurs.`))return;perform(()=>publicationApi.publish(publishForm)).then(()=>{setShowPublish(false);setMessage('Nouvelle version publiée côté Django.')}).catch(e=>setMessage(e.message))};
  const rollback=async r=>{if(!confirm(`Réactiver l’ancienne release ${r.numero} ?`))return;try{await perform(()=>publicationApi.rollback(r.id));setMessage('Release réactivée.')}catch(e){setMessage(e.message)}};
  return <div className="page-stack">
    <div className="stats-grid compact-stats">
      <StatCard icon={BookOpen} label="Tantara" value={stories.length} note="Dans la base éditoriale" tone="purple"/>
      <StatCard icon={CheckCheck} label="Approuvés" value={stories.filter(s=>s.status==='ready').length} note="Prêts au contrôle global" tone="blue"/>
      <StatCard icon={CircleAlert} label="À finaliser" value={stories.filter(s=>['draft','review'].includes(s.status)).length} note="Brouillons / relecture" tone="purple"/>
      <StatCard icon={Send} label="Releases" value={releases.length} note="Snapshots immuables" tone="blue"/>
    </div>
    <div className="section-toolbar"><span className="section-hint">Version active : {active?.numero || 'Aucune'}</span><div className="tree-toolbar-actions"><button className="btn btn-outline" onClick={()=>refresh()}><RefreshCw size={16}/> Actualiser</button><button className="btn btn-outline" onClick={validate}>Valider les contenus</button><button className="btn btn-primary" onClick={()=>{setMessage('');setShowPublish(true)}}><Send size={17}/> Publier une release</button></div></div>
    {message&&<div role="status" className="api-banner">{message}</div>}
    <Panel title="Récits et relectures" icon={GitBranch}><div className="publication-grid">{stories.map(s=><article className="publication-item" key={s.id}><div className="publication-top"><div><strong>{s.title}</strong><small>{s.theme} · {s.revision}</small></div><Status value={s.status}/></div>
      <div className="checklist"><div className={`check-row ${s.relecture_fr_le?'ok':'missing'}`}><span>{s.relecture_fr_le?'✓':'!'}</span>Relecture française</div><div className={`check-row ${s.relecture_mg_le?'ok':'missing'}`}><span>{s.relecture_mg_le?'✓':'!'}</span>Relecture malgache</div><div className={`check-row ${s.valide_le?'ok':'missing'}`}><span>{s.valide_le?'✓':'!'}</span>Validation pédagogique</div></div>
      <div className="publication-actions"><Link className="btn btn-outline" to={`/arbre?story=${encodeURIComponent(s.id)}`}>Voir l’arbre</Link><button className="btn btn-primary" disabled={s.status==='ready'||s.status==='published'||busy} onClick={()=>{setApprove(s);setMessage('')}}>Approuver</button></div>
    </article>)}</div><div className="soft-note">L’approbation de chaque histoire nécessite les relectures FR/MG et la validation humaine. Une release distincte publie les contenus approuvés.</div></Panel>
    <Panel title="Historique des publications" icon={Send}><div className="resource-list">{releases.map(r=><div className="resource-list-row" key={r.id}><span className="resource-list-icon"><Send size={18}/></span><span className="resource-list-main"><strong>{r.numero} · {r.statut}</strong><small>{r.date_publication?.slice(0,16)||r.created_at?.slice(0,16)} · {r.fichiers?.length||0} fichier(s)</small></span>{r.statut!=='ACTIVE'&&<button className="btn btn-outline" onClick={()=>rollback(r)}>Réactiver</button>}</div>)}{!releases.length&&<p className="muted">Aucune release enregistrée.</p>}</div></Panel>
    {approve&&<Dialog title={`Approuver ${approve.title}`} onClose={()=>setApprove(null)}><form className="form-stack" onSubmit={approveStory}>
      <div className="form-two"><Field label="Validation pédagogique"><input type="date" required value={fields.valide_le} onChange={e=>setFields(p=>({...p,valide_le:e.target.value}))}/></Field><Field label="Rôle du validateur"><input required value={fields.validateur_role} onChange={e=>setFields(p=>({...p,validateur_role:e.target.value}))} placeholder="Ex. Équipe pédagogique"/></Field></div>
      <div className="form-two"><Field label="Relecture FR"><input type="date" required value={fields.relecture_fr_le} onChange={e=>setFields(p=>({...p,relecture_fr_le:e.target.value}))}/></Field><Field label="Rôle relecteur FR"><input required value={fields.relecteur_fr_role} onChange={e=>setFields(p=>({...p,relecteur_fr_role:e.target.value}))}/></Field></div>
      <div className="form-two"><Field label="Relecture MG"><input type="date" required value={fields.relecture_mg_le} onChange={e=>setFields(p=>({...p,relecture_mg_le:e.target.value}))}/></Field><Field label="Rôle relecteur MG"><input required value={fields.relecteur_mg_role} onChange={e=>setFields(p=>({...p,relecteur_mg_role:e.target.value}))}/></Field></div>
      <div className="soft-note">Le graphe doit avoir été appliqué aux nœuds relationnels avant la validation de publication.</div>
      <div className="form-actions"><button type="button" className="btn btn-outline" onClick={()=>setApprove(null)}>Annuler</button><button disabled={busy} className="btn btn-primary">Valider</button></div>
    </form></Dialog>}
    {showPublish&&<Dialog title="Publier une version" onClose={()=>setShowPublish(false)}><form className="form-stack" onSubmit={publish}>
      <Field label="Numéro de version unique"><input required pattern="[a-zA-Z0-9][a-zA-Z0-9._-]{0,39}" value={publishForm.numero} onChange={e=>setPublishForm(p=>({...p,numero:e.target.value}))} placeholder="2026.10.30-r1"/></Field>
      <Field label="Journal de modifications"><textarea rows={3} maxLength={2000} value={publishForm.journal} onChange={e=>setPublishForm(p=>({...p,journal:e.target.value}))}/></Field>
      <div className="soft-note">Le backend vérifiera à nouveau tous les prérequis avant de créer le snapshot immuable. Cette opération n’est pas une simulation.</div>
      <div className="form-actions"><button type="button" className="btn btn-outline" onClick={()=>setShowPublish(false)}>Annuler</button><button className="btn btn-primary" disabled={busy}>Confirmer la publication</button></div>
    </form></Dialog>}
  </div>;
}
