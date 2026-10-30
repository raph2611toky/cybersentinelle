import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, Lock, Mail, ShieldCheck } from 'lucide-react';
import { useAdmin } from '../lib/store';

export default function Login() {
  const { auth, login } = useAdmin();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [lang, setLang] = useState('FR');
  const [submitError,setSubmitError] = useState('');
  const [submitting,setSubmitting] = useState(false);

  const to = location.state?.from?.pathname || '/';
  useEffect(() => { if (auth.authed) navigate(to, { replace: true }); }, [auth.authed]);

  const submit = async e => {
    e.preventDefault();
    setSubmitError('');setSubmitting(true);
    try {await login(email, password); navigate(to, {replace:true});}
    catch(error){setSubmitError(error?.response?.data?.error?.message || error?.message || 'Échec de connexion.');}
    finally {setSubmitting(false)}
  };

  return <div className="auth-shell">
    {/* Panneau de marque */}
    <aside className="auth-visual">
      <div className="auth-brand"><span className="brand-mark">S</span><span className="brand-text">SAFIDIKO<small>ADMIN STUDIO</small></span></div>

      <div className="auth-visual-body">
        <h2>Composez des récits<br/>qui protègent.</h2>
        <p>Studio d’administration des Tantara, médias et ressources pédagogiques.</p>
        <svg className="auth-graph" viewBox="0 0 300 180" aria-hidden="true">
          <defs>
            <linearGradient id="agline" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#31b7ff"/><stop offset="1" stopColor="#9555ff"/>
            </linearGradient>
          </defs>
          <path d="M60 36 L60 88" stroke="url(#agline)" strokeWidth="2"/>
          <path d="M60 88 L150 132" stroke="url(#agline)" strokeWidth="2"/>
          <path d="M60 88 L240 92" stroke="url(#agline)" strokeWidth="2"/>
          <path d="M240 92 L240 140" stroke="url(#agline)" strokeWidth="2"/>
          <g className="ag-node"><rect x="24" y="18" width="72" height="30" rx="4"/><circle cx="60" cy="33" r="3"/></g>
          <g className="ag-node decision"><rect x="24" y="72" width="72" height="30" rx="4"/><circle cx="60" cy="87" r="3"/></g>
          <g className="ag-node"><rect x="114" y="118" width="72" height="30" rx="4"/></g>
          <g className="ag-node"><rect x="204" y="78" width="72" height="30" rx="4"/></g>
          <g className="ag-node ending"><rect x="204" y="126" width="72" height="30" rx="4"/></g>
        </svg>
      </div>

      <div className="auth-foot"><ShieldCheck size={15}/><span>Données éditoriales uniquement · aucun suivi des joueurs</span></div>
    </aside>

    {/* Formulaire */}
    <main className="auth-main">
      <section className="cut-card auth-card"><form className="cut-inner auth-form" onSubmit={submit}>
        <span className="auth-eyebrow"><span className="active-dot"/>ESPACE ADMIN</span>
        <h1>Connexion</h1>

        <label className="auth-field">
          <span>Adresse e-mail</span>
          <div className="auth-input"><Mail size={16}/><input type="email" required value={email}
               onChange={e => setEmail(e.target.value)} placeholder="admin@safidiko.mg" autoComplete="username"/></div>
        </label>

        <label className="auth-field">
          <span>Mot de passe</span>
          <div className="auth-input"><Lock size={16}/><input type="password" required value={password}
               onChange={e => setPassword(e.target.value)} placeholder="••••••••" autoComplete="current-password"/></div>
        </label>

        <div className="auth-row">
          <div className="auth-lang" role="group" aria-label="Langue">
            {['FR', 'MG'].map(l => <button type="button" key={l}
                 className={lang === l ? 'selected' : ''} onClick={() => setLang(l)}>{l}</button>)}
          </div>
          <span className="auth-link">Réinitialisation via l’administrateur Django</span>
        </div>

        <button type="submit" className="auth-submit" disabled={submitting}>{submitting?"Connexion…":"Se connecter"}<ArrowRight size={17}/></button>
        {submitError && <p role="alert" className="api-error">{submitError}</p>}
        <p className="auth-note">Accès réservé à l’équipe éditoriale SAFIDIKO.</p>
      </form></section>
    </main>
  </div>;
}
