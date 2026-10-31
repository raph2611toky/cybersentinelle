import { ArrowUpRight, MoreHorizontal } from 'lucide-react';
import { Children, isValidElement } from 'react';
import { Link } from 'react-router-dom';
import { Sparkline } from './Charts';

export function Panel({ title, icon: Icon, action, children, className = '' }) {
  return <section className={`cut-card panel ${className}`}><div className="cut-inner">
    {title && <div className="panel-header"><div className="panel-title">{Icon && <span className="mini-icon"><Icon size={18} /></span>}<h2>{title}</h2></div>{action}</div>}
    {children}
  </div></section>;
}

export function StatCard({ icon: Icon, label, value, note, tone = 'purple', trend }) {
  return <article className={`cut-card stat-card tone-${tone}`}><div className="cut-inner">
    <div className="stat-top"><span className="stat-icon"><Icon size={21}/></span><span>{label}</span></div>
    <strong className="stat-value">{value}</strong><span className="stat-note">{note}</span>
    {trend && <Sparkline className="stat-spark" values={trend} color={tone === 'blue' ? '#5fc7ff' : '#b78bff'}/>}
  </div></article>;
}

export function Status({ value }) {
  const names = { published: 'Publié', draft: 'Brouillon', review: 'À vérifier', ready: 'Validé' };
  return <span className={`status status-${value}`}>{names[value] || value}</span>;
}

export function TextLink({ to, children }) {
  return <Link className="text-link" to={to}>{children} <ArrowUpRight size={14}/></Link>;
}

export function EmptyState({ title, description }) {
  return <div className="empty-state"><MoreHorizontal size={23}/><strong>{title}</strong><span>{description}</span></div>;
}

export function Field({ label, children, required = false }) {
  const inferred = Children.toArray(children).some(node => isValidElement(node) && node.props.required);
  return <label className="field"><span className="field-label">{label}{(required || inferred) && <span className="required-asterisk" aria-label="obligatoire"> *</span>}</span>{children}</label>;
}

export function Dialog({ title, onClose, children, className = '' }) {
  return <div className="dialog-backdrop" onMouseDown={e => { if(e.target === e.currentTarget) onClose(); }}>
    <section className={`dialog ${className}`} role="dialog" aria-modal="true" aria-label={title}>
      <div className="dialog-title"><h2>{title}</h2><button className="icon-button" onClick={onClose} aria-label="Fermer">×</button></div>
      {children}
    </section>
  </div>;
}
