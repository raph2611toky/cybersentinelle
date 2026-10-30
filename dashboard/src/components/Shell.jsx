import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { BookOpen, ChevronLeft, ChevronRight, CircleHelp, FileText, GitBranch, LayoutDashboard, LogOut, Menu, Mic2, Search, Send, Settings, Film, Plus, Bell } from 'lucide-react';
import { useState } from 'react';
import { useAdmin } from '../lib/store';

const nav = [
  { to: '/', label: 'Vue d’ensemble', icon: LayoutDashboard, end: true },
  { to: '/tantara', label: 'Tantara', icon: BookOpen },
  { to: '/arbre', label: 'Arbres narratifs', icon: GitBranch },
  { to: '/medias', label: 'Médiathèque', icon: Film },
  { to: '/voix', label: 'Voix & audio', icon: Mic2 },
  { to: '/ressources', label: 'Ressources d’aide', icon: CircleHelp },
  { to: '/publication', label: 'Publication', icon: Send },
  { to: '/parametres', label: 'Paramètres', icon: Settings },
];

const titles = {
  '/': ['Vue d’ensemble', 'Gérez vos histoires, vos médias et les publications.'],
  '/tantara': ['Tantara', 'Création et gestion des récits interactifs.'],
  '/arbre': ['Arbres narratifs', 'Concevez les scènes et leurs embranchements.'],
  '/medias': ['Médiathèque', 'Images, vidéos et fichiers audio.'],
  '/voix': ['Studio vocal', 'Lecture, narration et assemblage sonore.'],
  '/ressources': ['Ressources d’aide', 'Conseils pédagogiques et orientations vérifiées.'],
  '/publication': ['Publication', 'Vérifiez les contenus avant diffusion.'],
  '/parametres': ['Paramètres', 'Préférences du studio administratif.'],
};

export default function Shell() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { auth, logout } = useAdmin();
  const [title, desc] = titles[location.pathname] || titles['/'];

  const userName = auth.user?.name || 'Administrateur';
  const userRole = auth.user?.role || 'Studio SAFIDIKO';
  const initials = (userName.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()) || 'AD';

  const doSearch = e => { e.preventDefault(); if (search.trim()) { navigate(`/tantara?q=${encodeURIComponent(search.trim())}`); setMobileOpen(false); } };
  const handleLogout = () => { logout(); navigate('/login', { replace: true }); };

  return <div className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">S</span>{!collapsed && <span className="brand-text">SAFIDIKO<small>ADMIN STUDIO</small></span>}</div>
      <div className="nav-label">{!collapsed && 'ESPACE DE TRAVAIL'}</div>
      <nav className="nav-list">{nav.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} title={label} onClick={()=>setMobileOpen(false)} className={({isActive})=>`nav-item ${isActive?'active':''}`}><Icon size={19}/>{!collapsed && <span>{label}</span>}</NavLink>)}</nav>
      <div className="sidebar-bottom"><div className="profile-chip"><span className="avatar">{initials}</span>{!collapsed && <span><strong>{userName}</strong><small>{userRole}</small></span>}</div><div className="sidebar-actions"><button className="collapse-btn" title="Réduire le menu" onClick={()=>setCollapsed(v=>!v)}>{collapsed?<ChevronRight size={18}/>:<ChevronLeft size={18}/>}{!collapsed&&'Réduire'}</button><button className="logout-btn" title="Se déconnecter" onClick={handleLogout}><LogOut size={17}/>{!collapsed&&<span>Déconnexion</span>}</button></div></div>
    </aside>
    {mobileOpen && <button aria-label="Fermer le menu" className="mobile-scrim" onClick={()=>setMobileOpen(false)}/>}
    <main className="main-area">
      <header className="topbar"><button className="mobile-menu icon-button" onClick={()=>setMobileOpen(true)} aria-label="Ouvrir le menu"><Menu size={22}/></button>
        <div className="heading"><span className="eyebrow"><span className="active-dot"/>SAFIDIKO / ADMIN</span><h1>{title}</h1><p>{desc}</p></div>
        <div className="top-actions"><form onSubmit={doSearch} className={`global-search ${showSearch?'expanded':''}`}><Search size={17}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Rechercher un Tantara..." aria-label="Rechercher"/><button type="submit" title="Rechercher"><ChevronRight size={16}/></button></form><button className="icon-button mobile-search" onClick={()=>setShowSearch(v=>!v)} aria-label="Recherche"><Search size={20}/></button><span className="header-divider"/><span className="top-avatar" title={userName}>{initials}</span></div>
      </header>
      <div className="page-body"><Outlet /></div>
    </main>
  </div>;
}
