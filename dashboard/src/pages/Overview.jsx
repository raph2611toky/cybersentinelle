import { BookOpen, CheckCircle2, Clock3, FileVideo2, GitBranch, Layers3, LibraryBig, Mic2, Pencil, Send, TrendingUp } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Panel, StatCard, Status, TextLink } from '../components/UI';
import { AreaChart, Donut } from '../components/Charts';
import { useAdmin } from '../lib/store';

export default function Overview() {
  const { stories, resources } = useAdmin();
  const published = stories.filter(s => s.status === 'published').length;
  const drafts = stories.filter(s => s.status === 'draft').length;
  const review = stories.filter(s => s.status === 'review' || s.status === 'ready').length;
  const nodes = stories.reduce((sum, s) => sum + (s.graph?.nodes?.length || 0), 0);
  const choices = stories.reduce((sum, s) => sum + (s.graph?.edges?.length || 0), 0);
  const issues = stories.filter(s => s.status !== 'published');

  // Activité éditoriale (démo) — contenus ajoutés par semaine
  const activity = [
    { label: 'S1', a: 2, b: 1 }, { label: 'S2', a: 4, b: 2 }, { label: 'S3', a: 3, b: 3 },
    { label: 'S4', a: 6, b: 4 }, { label: 'S5', a: 5, b: 4 }, { label: 'S6', a: 8, b: 6 },
    { label: 'S7', a: 7, b: 6 }, { label: 'S8', a: 10, b: 8 },
  ];

  const segments = [
    { label: 'Publiés', value: published || 0, color: '#31b7ff' },
    { label: 'Brouillons', value: drafts || 0, color: '#9555ff' },
    { label: 'À vérifier', value: review || 0, color: '#f1b36a' },
  ].filter(s => s.value > 0);

  return <div className="page-stack">
    <div className="stats-grid">
      <StatCard label="Tantara" value={stories.length.toString().padStart(2, '0')} note="Histoires disponibles" icon={BookOpen} tone="purple" trend={[3, 4, 4, 5, 6, 6, 7, stories.length]}/>
      <StatCard label="Publiés" value={String(published).padStart(2, '0')} note="Contenus en ligne (démo)" icon={CheckCircle2} tone="blue" trend={[1, 1, 2, 2, 2, 3, 3, published]}/>
      <StatCard label="Brouillons" value={String(drafts).padStart(2, '0')} note="À finaliser" icon={Pencil} tone="purple" trend={[2, 2, 3, 2, 3, 2, 2, drafts]}/>
      <StatCard label="Nœuds narratifs" value={String(nodes).padStart(2, '0')} note="Scènes, choix et fins" icon={GitBranch} tone="blue" trend={[4, 6, 7, 9, 10, 11, 12, nodes]}/>
    </div>

    <div className="chart-grid">
      <Panel title="Activité éditoriale" icon={TrendingUp} className="chart-card"
             action={<span className="chart-tag">8 dernières semaines</span>}>
        <AreaChart data={activity} legend={['Scènes', 'Choix']}/>
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
