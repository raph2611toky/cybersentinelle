import { Database, LockKeyhole, Palette, RotateCcw, Server } from 'lucide-react';
import { Panel } from '../components/UI';
import { useAdmin } from '../lib/store';
export default function SettingsPage(){
  const {resetDemo}=useAdmin();
  return <div className="page-stack"><div className="content-grid">
    <Panel title="Identité visuelle" icon={Palette}><div className="settings-colors"><div><i style={{background:'#090d16'}}/>Fond noir bleuté <code>#090D16</code></div><div><i style={{background:'#9555ff'}}/>Violet primaire <code>#9555FF</code></div><div><i style={{background:'#31b7ff'}}/>Bleu primaire <code>#31B7FF</code></div><div><i style={{background:'#f1b36a'}}/>Ambre secondaire <code>#F1B36A</code></div></div></Panel>
    <Panel title="Backend et confidentialité" icon={LockKeyhole}><div className="settings-status"><Database size={18}/><span>Mode démonstration : données éditoriales en localStorage.</span></div><div className="settings-status"><Server size={18}/><span>API Django REST : connexion non configurée.</span></div><div className="settings-status"><LockKeyhole size={18}/><span>Authentification administrateur : à raccorder côté backend.</span></div></Panel>
  </div><Panel title="Réinitialiser le prototype" icon={RotateCcw}><div className="section-toolbar"><p className="muted">Efface les modifications locales des histoires et des ressources.</p><button className="btn btn-outline" onClick={()=>{if(confirm('Effacer toutes les modifications de la démo ?')){resetDemo();window.location.assign('/')}}}><RotateCcw size={16}/> Réinitialiser</button></div></Panel></div>;
}
