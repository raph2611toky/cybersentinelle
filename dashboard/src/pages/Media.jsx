import { useMemo, useState } from 'react';
import {
  FileAudio2, FileImage, FileVideo2, Grid2x2, List,
  Pencil, Play, Search, Trash2, UploadCloud,
} from 'lucide-react';
import { Dialog, EmptyState, Field, Panel } from '../components/UI';
import { useAdmin } from '../lib/store';
import { studioApi } from '../services/editor';

const icons = { IMAGE: FileImage, VIDEO: FileVideo2, AUDIO: FileAudio2, SUBTITLE: FileAudio2 };
const kindFromFile = file => file?.type?.startsWith('video/') ? 'VIDEO'
  : file?.type?.startsWith('image/') ? 'IMAGE'
    : file?.type?.startsWith('audio/') ? 'AUDIO' : 'SUBTITLE';
const mb = bytes => `${(Number(bytes || 0) / 1048576).toFixed(2)} Mo`;

// URL privée de la même origine que l'API ; cookies de session Django conservés.
// Ne jamais utiliser une URL d'origine arbitraire fournie par un média.
const API_ROOT = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
const mediaSrc = id => `${API_ROOT}/editor/studio/media/${encodeURIComponent(id)}/file/`;

function MediaThumb({ item }) {
  const Icon = icons[item.type] || FileImage;
  const [failed, setFailed] = useState(false);
  const [ready, setReady] = useState(false);
  const src = mediaSrc(item.id);

  return <span className="media-thumb-content">
    {!failed && item.type === 'IMAGE' &&
      <img src={src} alt="" loading="lazy" onLoad={() => setReady(true)} onError={() => setFailed(true)} />}
    {!failed && item.type === 'VIDEO' &&
      <video
        src={`${src}#t=0.1`}
        muted
        playsInline
        preload="metadata"
        aria-hidden="true"
        onLoadedData={() => setReady(true)}
        onError={() => setFailed(true)}
      />}
    {(!ready || failed || !['IMAGE', 'VIDEO'].includes(item.type)) &&
      <Icon className="media-thumb-placeholder" size={36} aria-hidden="true" />}
    {!failed && item.type === 'VIDEO' && <span className="media-video-play" aria-hidden="true"><Play size={16} fill="currentColor" /></span>}
  </span>;
}

export default function Media() {
  const { media, languages, perform, busy } = useAdmin();
  const [tab, setTab] = useState('ALL');
  const [query, setQuery] = useState('');
  const [layout, setLayout] = useState('grid');
  const [form, setForm] = useState(null);
  const [editing, setEditing] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');

  const activeLanguages = (languages || []).filter(l => l.actif);
  const counts = kind => media.filter(m => m.type === kind).length;
  const filtered = useMemo(() => media.filter(item =>
    (tab === 'ALL' || item.type === tab) &&
    (item.titre || '').toLowerCase().includes(query.toLowerCase())
  ), [media, tab, query]);

  const choose = file => {
    if (!file) return;
    setError('');
    setForm({ file, title: file.name.replace(/\.[^.]+$/, ''), type: kindFromFile(file), licence: '', rights: false, langue: '' });
  };

  const upload = async event => {
    event.preventDefault();
    setError('');
    if (!form?.rights) { setError('Confirmez les droits avant import.'); return; }
    const payload = new FormData();
    payload.append('fichier', form.file);
    payload.append('titre', form.title);
    payload.append('type', form.type);
    payload.append('licence', form.licence);
    payload.append('droits_confirmes', 'true');
    if (form.langue) payload.append('langue', form.langue);
    try {
      await perform(() => studioApi.upload(payload));
      setForm(null);
    } catch (err) { setError(err.message); }
  };

  const edit = item => {
    setError('');
    setEditing({ id: item.id, type: item.type, titre: item.titre, licence: item.licence || '', langue: item.langue || '' });
  };

  const saveEdit = async event => {
    event.preventDefault();
    if (!editing) return;
    setError('');
    try {
      await perform(() => studioApi.updateMedia(editing.id, {
        titre: editing.titre.trim(),
        licence: editing.licence.trim(),
        langue: editing.langue,
      }));
      setEditing(null);
    } catch (err) { setError(err.message); }
  };

  const del = async item => {
    if (!confirm(`Supprimer le média « ${item.titre} » ?`)) return;
    setError('');
    try {
      await perform(() => studioApi.deleteMedia(item.id));
      if (preview?.id === item.id) setPreview(null);
    } catch (err) { setError(err.message); }
  };

  const langOptions = <>
    <option value="">Sans langue</option>
    {activeLanguages.map(lang => <option key={lang.code} value={lang.code}>{lang.nom_fr || lang.code}</option>)}
  </>;

  return <div className="page-stack">
    <div className="section-toolbar">
      <span className="section-hint">Médiathèque privée Django · droits vérifiés</span>
      <label className="btn btn-primary" style={{ cursor: 'pointer' }}>
        <UploadCloud size={17}/> Importer un fichier
        <input type="file" accept="video/*,audio/*,image/*,.srt,.vtt" hidden onChange={event => { choose(event.target.files?.[0]); event.target.value = ''; }}/>
      </label>
    </div>
    <div className="stats-grid compact-stats">
      <div className="media-stat purple-tint"><FileVideo2/><strong>{counts('VIDEO')}</strong><span>Vidéos</span></div>
      <div className="media-stat blue-tint"><FileAudio2/><strong>{counts('AUDIO')}</strong><span>Audios</span></div>
      <div className="media-stat purple-tint"><FileImage/><strong>{counts('IMAGE')}</strong><span>Images</span></div>
      <div className="media-stat blue-tint"><Grid2x2/><strong>{media.length}</strong><span>Fichiers</span></div>
    </div>
    <Panel title="Bibliothèque multimédia" icon={FileImage}>
      <div className="table-toolbar">
        <div className="filter-tabs">
          {[
            ['ALL', 'Tous'], ['VIDEO', 'Vidéos'], ['IMAGE', 'Images'],
            ['AUDIO', 'Audios'], ['SUBTITLE', 'Sous-titres'],
          ].map(([value, label]) => <button key={value} type="button" onClick={() => setTab(value)} className={`filter-tab ${tab === value ? 'selected' : ''}`}>{label}</button>)}
        </div>
        <label className="search-control"><Search size={16}/><input placeholder="Rechercher un fichier" value={query} onChange={event => setQuery(event.target.value)}/></label>
        <div className="view-switch"><button type="button" className={layout === 'grid' ? 'active' : ''} onClick={() => setLayout('grid')} title="Grille"><Grid2x2 size={17}/></button><button type="button" className={layout === 'list' ? 'active' : ''} onClick={() => setLayout('list')} title="Liste"><List size={17}/></button></div>
      </div>
      {error && !form && !editing && <div role="alert" className="api-error">{error}</div>}
      {filtered.length ? <div className={`media-grid ${layout === 'list' ? 'media-list' : ''}`}>
        {filtered.map(item => <article className="media-tile" key={item.id}>
          <button type="button" className={`media-thumbnail thumbnail-${item.type.toLowerCase()}`} onClick={() => { setError(''); setPreview(item); }} title={`Prévisualiser : ${item.titre}`} aria-label={`Prévisualiser ${item.titre}`}>
            <MediaThumb item={item}/>
          </button>
          <div className="media-tile-info">
            <span><strong title={item.titre}>{item.titre}</strong><small>{item.type} · {mb(item.taille_octets)} · {item.langue || '—'}</small></span>
            <div className="media-tile-actions">
              <button type="button" title="Modifier" aria-label={`Modifier ${item.titre}`} className="icon-button" disabled={busy} onClick={() => edit(item)}><Pencil size={16}/></button>
              <button type="button" title="Supprimer" aria-label={`Supprimer ${item.titre}`} className="icon-button" disabled={busy} onClick={() => del(item)}><Trash2 size={16}/></button>
            </div>
          </div>
        </article>)}
      </div> : <EmptyState title="Médiathèque vide" description="Importez un fichier autorisé."/>}
      <div className="table-footer">Les médias privés sont servis via une route staff et une session valide.</div>
    </Panel>

    {preview && <Dialog title={preview.titre} onClose={() => setPreview(null)}>
      <div className="file-preview">
        {preview.type === 'IMAGE' ? <img src={mediaSrc(preview.id)} alt={preview.titre}/>
          : preview.type === 'VIDEO' ? <video src={mediaSrc(preview.id)} controls preload="metadata" playsInline/>
            : preview.type === 'AUDIO' ? <audio src={mediaSrc(preview.id)} controls preload="metadata"/>
              : <a href={mediaSrc(preview.id)} download>Consulter le sous-titre</a>}
      </div>
    </Dialog>}

    {editing && <Dialog title="Modifier le média" onClose={() => { setEditing(null); setError(''); }}>
      <form className="form-stack" onSubmit={saveEdit}>
        <p className="muted">Type : {editing.type} · fichier original conservé</p>
        <Field label="Titre"><input required maxLength={200} value={editing.titre} onChange={event => setEditing(p => ({ ...p, titre: event.target.value }))}/></Field>
        <Field label="Licence / provenance"><input required maxLength={160} value={editing.licence} onChange={event => setEditing(p => ({ ...p, licence: event.target.value }))}/></Field>
        <Field label="Langue facultative"><select value={editing.langue} onChange={event => setEditing(p => ({ ...p, langue: event.target.value }))}>{langOptions}</select></Field>
        {error && <p role="alert" className="api-error">{error}</p>}
        <div className="form-actions">
          <button type="button" className="btn btn-outline" onClick={() => { setEditing(null); setError(''); }}>Annuler</button>
          <button type="submit" className="btn btn-primary" disabled={busy || !editing.titre.trim() || !editing.licence.trim()}>{busy ? 'Enregistrement…' : 'Enregistrer les modifications'}</button>
        </div>
      </form>
    </Dialog>}

    {form && <Dialog title="Importer un média" onClose={() => { setForm(null); setError(''); }}>
      <form onSubmit={upload} className="form-stack">
        <p className="muted">{form.file.name} · {mb(form.file.size)}</p>
        <Field label="Titre"><input required maxLength={200} value={form.title} onChange={event => setForm(p => ({ ...p, title: event.target.value }))}/></Field>
        <Field label="Type"><select value={form.type} onChange={event => setForm(p => ({ ...p, type: event.target.value }))}><option value="IMAGE">Image</option><option value="VIDEO">Vidéo</option><option value="AUDIO">Audio</option><option value="SUBTITLE">Sous-titres</option></select></Field>
        <Field label="Licence / provenance"><input required maxLength={160} value={form.licence} onChange={event => setForm(p => ({ ...p, licence: event.target.value }))} placeholder="Ex. Création originale de l’équipe"/></Field>
        <Field label="Langue facultative"><select value={form.langue} onChange={event => setForm(p => ({ ...p, langue: event.target.value }))}>{langOptions}</select></Field>
        <label className="checkbox-line"><input type="checkbox" checked={form.rights} onChange={event => setForm(p => ({ ...p, rights: event.target.checked }))}/> Je confirme que nous avons les droits d'utilisation et que le contenu est fictif.</label>
        {error && <p role="alert" className="api-error">{error}</p>}
        <div className="form-actions"><button type="button" className="btn btn-outline" onClick={() => { setForm(null); setError(''); }}>Annuler</button><button type="submit" className="btn btn-primary" disabled={busy || !form.rights}>{busy ? 'Import…' : 'Importer sur Django'}</button></div>
      </form>
    </Dialog>}
  </div>;
}
