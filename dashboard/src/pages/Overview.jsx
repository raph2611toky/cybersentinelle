import { BookOpen, CheckCircle2, Clock3, FileVideo2, GitBranch, Layers3, LibraryBig, Mic2, Pencil, Send, TrendingUp } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Panel, StatCard, Status, TextLink } from '../components/UI';
import { AreaChart, Donut } from '../components/Charts';
import { useAdmin } from '../lib/store';

export default function Overview() {
  const { stories, resources, nodes:backendNodes, options:backendOptions } = useAdmin();
  const published = stories.filter(s => s.status === 'published').length;
  const drafts = stories.filter(s => s.status === 'draft').length;
  const review = stories.filter(s => s.status === 'review' || s.status === 'ready').length;
  const nodes = backendNodes.length;
  const choices = backendOptions.length;
  const issues = stories.filter(s => s.status !== 'published');

  // Données réelles : nombre de contenus mis à jour chaque semaine.
  const now=new Date();
  const activity=Array.from({length:8},(_,i)=>{
    const end=new Date(now);end.setDate(end.getDate()-(7-i)*7);
    const begin=new Date(end);begin.setDate(begin.getDate()-7);
    return {label:`S${i+1}`,a:stories.filter(s=>{const d=new Date(s.updatedAt);return d>=begin&&d<end}).length,
      b:backendNodes.filter(n=>{const d=new Date(n.updated_at);return d>=begin&&d<end}).length};
  });

  const segments = [
    { label: 'Publiés', value: published || 0, color: '#31b7ff' },
    { label: 'Brouillons', value: drafts || 0, color: '#9555ff' },
    { label: 'À vérifier', value: review || 0, color: '#f1b36a' },
  ].filter(s => s.value > 0);

  return <div className="page-stack">
    <div className="stats-grid">
      <StatCard label="Tantara" value={stories.length.toString().padStart(2, '0')} note="Histoires disponibles" icon={BookOpen} tone="purple" />
      <StatCard label="Publiés" value={String(published).padStart(2, '0')} note="Statuts éditoriaux en base" icon={CheckCircle2} tone="blue" />
      <StatCard label="Brouillons" value={String(drafts).padStart(2, '0')} note="À finaliser" icon={Pencil} tone="purple" />
      <StatCard label="Nœuds narratifs" value={String(nodes).padStart(2, '0')} note="Scènes, choix et fins" icon={GitBranch} tone="blue" />
    </div>

    <div className="chart-grid">
      <Panel title="Activité éditoriale" icon={TrendingUp} className="chart-card"
             action={<span className="chart-tag">8 dernières semaines</span>}>
        <AreaChart data={activity} legend={['Tantara', 'Nœuds']}/>
      </Panel>
      <Panel title="Répartition" icon={Layers3} className="donut-card">
        <div className="donut-wrap">
          <Donut segments={segments.length ? segments : [{ label: '—', value: 1, color: '#2a3a52' }]}
                 centerValue={String(stories.length).padStart(2, '0')} centerLabel="Tantara"/>
          <div className="donut-legend">
            {segments.map(s => <div key={s.label} className="donut-legend-row">
              <span className="dot" style={{ background: s.color }}/><span>{s.label}</span>
              <strong>{String(s.value).padStart(2, '0')}</strong>
            </div>)}
            <div className="donut-legend-row total">
              <span className="dot" style={{ background: '#5f7694' }}/><span>Choix narratifs</span>
              <strong>{String(choices).padStart(2, '0')}</strong>
            </div>
          </div>
        </div>
      </Panel>
    </div>

    <div className="content-grid">
      <Panel title="Tantara récents" icon={LibraryBig} action={<TextLink to="/tantara">Tout voir</TextLink>}>
        <div className="story-list">{stories.slice(0,4).map((story, i) => <Link key={story.id} className="story-list-row" to={`/arbre?story=${encodeURIComponent(story.id)}`}>
          <span className={`story-art art-${i % 3}`}><BookOpen size={20}/></span>
          <span className="story-info"><strong>{story.title}</strong><small>{story.theme}</small></span>
          <Status value={story.status}/><GitBranch size={17} className="faint"/>
        </Link>)}</div>
      </Panel>
      <Panel title="À finaliser" icon={Clock3} action={<TextLink to="/publication">Vérification</TextLink>}>
        <div className="review-list">{issues.length ? issues.map(story => <Link to={`/arbre?story=${encodeURIComponent(story.id)}`} key={story.id} className="review-row">
          <span className="review-icon"><GitBranch size={18}/></span><span><strong>{story.title}</strong><small>Vérifier les branches et les traductions</small></span><span className="review-arrow">↗</span>
        </Link>) : <p className="muted">Aucun brouillon en attente.</p>}</div>
        <div className="soft-note"><span className="active-dot"/>Données éditoriales uniquement · aucun suivi des joueurs</div>
      </Panel>
    </div>

    <div className="bottom-grid">
      <Panel title="Studio médias" icon={FileVideo2} action={<TextLink to="/medias">Ouvrir</TextLink>}>
        <div className="summary-tiles"><Link to="/medias" className="summary-tile"><FileVideo2 size={22}/><strong>Vidéos</strong><span>Importer et associer</span></Link><Link to="/voix" className="summary-tile"><Mic2 size={22}/><strong>Voix</strong><span>Narration FR / MG</span></Link><Link to="/arbre" className="summary-tile"><Layers3 size={22}/><strong>Scènes</strong><span>Relier les médias</span></Link></div>
      </Panel>
      <Panel title="Ressources d’aide" icon={BookOpen} action={<TextLink to="/ressources">Gérer</TextLink>}>
        <div className="resource-highlight"><div><div className="resource-count">{String(resources.length).padStart(2,'0')}</div><span>Fiches pédagogiques</span></div><div className="resource-meta"><Send size={20}/><span>Liens officiels à contrôler avant publication</span></div></div>
      </Panel>
    </div>
  </div>;
}
