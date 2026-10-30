import { Database, LockKeyhole, Palette, Server, RefreshCw } from 'lucide-react';
import { Panel } from '../components/UI';
import { useAdmin } from '../lib/store';
export default function SettingsPage(){
  const {auth,refresh,stories,media,resources}=useAdmin();
  return <div className="page-stack"><div className="content-grid">
    <Panel title="Identité visuelle" icon={Palette}><div className="settings-colors"><div><i style={{background:'var(--bg)'}}/>Noir principal <code>#050507</code></div><div><i style={{background:'var(--purple)'}}/>Violet primaire <code>#9D66F9</code></div><div><i style={{background:'var(--blue)'}}/>Bleu primaire <code>#47B8FF</code></div><div><i style={{background:'var(--amber)'}}/>Ambre secondaire <code>#F4BC70</code></div></div></Panel>
    <Panel title="Connexion et sécurité" icon={LockKeyhole}><div className="settings-status"><Database size={18}/><span>Django : {stories.length} Tantara, {resources.length} ressources, {media.length} médias.</span></div><div className="settings-status"><Server size={18}/><span>API : {import.meta.env.VITE_API_BASE_URL||'/api'}</span></div><div className="settings-status"><LockKeyhole size={18}/><span>Session HttpOnly Django + CSRF · {auth.user?.username||'Administrateur'}</span></div><div className="settings-status"><LockKeyhole size={18}/><span>Rôle : {auth.user?.role||'Éditeur'} · {auth.user?.permissions?.length||0} permissions</span></div></Panel>
  </div><Panel title="Synchroniser" icon={RefreshCw}><div className="section-toolbar"><p className="muted">Relit les données du serveur sans supprimer ni modifier les contenus.</p><button className="btn btn-outline" onClick={()=>refresh()}><RefreshCw size={16}/> Actualiser</button></div></Panel></div>;
}
