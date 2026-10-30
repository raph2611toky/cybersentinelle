import { BookOpen, CheckCheck, CircleAlert, GitBranch, Send } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Panel, StatCard, Status } from '../components/UI';
import { useAdmin } from '../lib/store';

function checks(story){
  const nodes=story.graph?.nodes||[],edges=story.graph?.edges||[];
  return [
    {label:'Scènes présentes',ok:nodes.length>0},
    {label:'Au moins une fin',ok:nodes.some(n=>n.data.kind==='ending')},
    {label:'Scènes reliées',ok:nodes.filter(n=>n.data.kind==='scene').every(n=>edges.some(e=>e.source===n.id))},
    {label:'Traductions de titres FR/MG',ok:nodes.every(n=>n.data.title?.fr?.trim()&&n.data.title?.mg?.trim())},
    {label:'Choix reliés',ok:nodes.filter(n=>n.data.kind==='decision').every(n=>(n.data.options||[]).every(o=>edges.some(e=>e.source===n.id&&e.sourceHandle===o.id)))}
  ];
}
export default function Publication(){
  const {stories,updateStory}=useAdmin();
  const ready=stories.filter(s=>checks(s).every(c=>c.ok));
  const publish=story=>{const checksDone=checks(story).every(c=>c.ok);if(!checksDone)return alert('Corrigez les points bloquants dans l’arbre.');if(confirm('Marquer ce Tantara comme publié dans la démo locale ?'))updateStory(story.id,{status:'published'});};
  return <div className="page-stack">
    <div className="stats-grid compact-stats"><StatCard label="Tantara" value={stories.length} icon={BookOpen} note="Récits enregistrés" tone="purple"/><StatCard label="Prêts" value={ready.length} icon={CheckCheck} note="Contrôles techniques validés" tone="blue"/><StatCard label="Brouillons" value={stories.filter(s=>s.status==='draft').length} icon={CircleAlert} note="À relire" tone="purple"/><StatCard label="Publiés" value={stories.filter(s=>s.status==='published').length} icon={Send} note="Statut local" tone="blue"/></div>
    <Panel title="Contrôle avant publication" icon={GitBranch}>
      <div className="publication-grid">{stories.map(s=>{const list=checks(s),valid=list.every(x=>x.ok);return <article className="publication-item" key={s.id}><div className="publication-top"><div><strong>{s.title}</strong><small>{s.theme}</small></div><Status value={s.status}/></div><div className="checklist">{list.map((c,i)=><div className={c.ok?'check-row ok':'check-row missing'} key={i}><span>{c.ok?'✓':'!'}</span>{c.label}</div>)}</div><div className="publication-actions"><Link className="btn btn-outline" to={`/arbre?story=${encodeURIComponent(s.id)}`}>Éditer l’arbre</Link><button className="btn btn-primary" disabled={!valid||s.status==='published'} onClick={()=>publish(s)}><Send size={15}/>{s.status==='published'?'Publié': 'Publier (démo)'}</button></div></article>})}</div>
      <div className="soft-note">Ces contrôles ne remplacent pas la validation pédagogique, juridique, linguistique et humaine. Aucune publication serveur n’est déclenchée.</div>
    </Panel>
  </div>;
}
