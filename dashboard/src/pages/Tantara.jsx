import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { BookOpen, Copy, Eye, GitBranch, Pencil, Plus, Search, Trash2 } from 'lucide-react';
import { Dialog, EmptyState, Field, Panel, StatCard, Status } from '../components/UI';
import { useAdmin } from '../lib/store';

export default function Tantara() {
  const { stories, addStory, updateStory, removeStory } = useAdmin();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [search, setSearch] = useState(params.get('q') || '');
  const [status, setStatus] = useState('all');
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({ title: '', theme: '' });
  useEffect(() => setSearch(params.get('q') || ''), [params]);
  const filtered = useMemo(() => stories.filter(s => (status === 'all' || s.status === status) && `${s.title} ${s.theme}`.toLowerCase().includes(search.toLowerCase())), [stories, search, status]);
  const openCreate = () => { setForm({ title:'', theme:'' }); setModal({mode:'create'}); };
  const openEdit = story => { setForm({title:story.title, theme:story.theme}); setModal({mode:'edit', story}); };
  const save = e => {
    e.preventDefault(); if (!form.title.trim()) return;
    if (modal.mode === 'edit') updateStory(modal.story.id, { title: form.title.trim(), theme: form.theme.trim() });
    else addStory(form);
    setModal(null);
  };
  const del = story => { if (window.confirm(`Supprimer définitivement « ${story.title} » dans cette démo ?`)) removeStory(story.id); };
  const duplicate = story => { addStory({ title: `${story.title} — copie`, theme: story.theme }); };

  return <div className="page-stack">
    <div className="section-toolbar"><span className="section-hint">Catalogue éditorial</span><button className="btn btn-primary" onClick={openCreate}><Plus size={17}/> Nouveau Tantara</button></div>
    <div className="stats-grid compact-stats">
      <StatCard icon={BookOpen} label="Total" value={stories.length} note="Histoires" tone="purple"/>
      <StatCard icon={Eye} label="Publiés" value={stories.filter(s=>s.status==='published').length} note="Disponibles" tone="blue"/>
      <StatCard icon={Pencil} label="Brouillons" value={stories.filter(s=>s.status==='draft').length} note="À compléter" tone="purple"/>
      <StatCard icon={GitBranch} label="Branches" value={stories.reduce((n,s)=>n+(s.graph?.edges?.length||0),0)} note="Liaisons du graphe" tone="blue"/>
    </div>
    <Panel title="Histoires" icon={BookOpen}>
      <div className="table-toolbar"><label className="search-control"><Search size={16}/><input placeholder="Rechercher une histoire" value={search} onChange={e=>setSearch(e.target.value)}/></label><div className="filter-tabs">{[['all','Tous'],['published','Publiés'],['draft','Brouillons']].map(([k,label])=><button key={k} className={`filter-tab ${status===k?'selected':''}`} onClick={()=>setStatus(k)}>{label}</button>)}</div></div>
      {filtered.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Tantara</th><th>Langues</th><th>Nœuds</th><th>Statut</th><th>Actions</th></tr></thead><tbody>{filtered.map((story,index)=><tr key={story.id}>
        <td><div className="table-name"><span className={`story-art art-${index%3}`}><BookOpen size={18}/></span><span><strong>{story.title}</strong><small>{story.theme}</small></span></div></td>
        <td><span className="lang-tag">{story.language}</span></td><td>{story.graph?.nodes?.length||0}</td><td><Status value={story.status}/></td>
        <td><div className="table-actions"><button title="Éditer" onClick={()=>openEdit(story)}><Pencil size={16}/></button><button title="Arbre narratif" onClick={()=>navigate(`/arbre?story=${encodeURIComponent(story.id)}`)}><GitBranch size={16}/></button><button title="Dupliquer (nouveau récit)" onClick={()=>duplicate(story)}><Copy size={16}/></button><button title="Supprimer" className="danger-hover" onClick={()=>del(story)}><Trash2 size={16}/></button></div></td>
      </tr>)}</tbody></table></div> : <EmptyState title="Aucun résultat" description="Essayez un autre filtre ou créez une histoire."/>}
      <div className="table-footer">{filtered.length} histoire(s) affichée(s) · données de démonstration</div>
    </Panel>
    {modal && <Dialog title={modal.mode === 'edit' ? 'Modifier le Tantara' : 'Nouveau Tantara'} onClose={()=>setModal(null)}><form onSubmit={save} className="form-stack"><Field label="Titre"><input required maxLength={120} value={form.title} onChange={e=>setForm(f=>({...f,title:e.target.value}))} placeholder="Titre du récit"/></Field><Field label="Thème"><input maxLength={140} value={form.theme} onChange={e=>setForm(f=>({...f,theme:e.target.value}))} placeholder="Cyberharcèlement, sextorsion..."/></Field><div className="form-actions"><button type="button" className="btn btn-outline" onClick={()=>setModal(null)}>Annuler</button><button className="btn btn-primary" type="submit">Enregistrer</button></div></form></Dialog>}
  </div>;
}
