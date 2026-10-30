import { useEffect, useState } from 'react';
import { AudioLines, FileAudio, Mic2, Play, Square, WandSparkles, Plus, RefreshCw } from 'lucide-react';
import { Dialog, Field, Panel, StatCard } from '../components/UI';
import { useAdmin } from '../lib/store';
import { studioApi } from '../services/editor';

export default function Voice(){
  const {voices,scenes,jobs,languages,nodes,media,perform,refresh,busy}=useAdmin();
  const [lang,setLang]=useState('fr');const [text,setText]=useState('Tu peux demander de l’aide à une personne de confiance.');
  const [playing,setPlaying]=useState(false),[dialog,setDialog]=useState(null),[error,setError]=useState('');
  const [voiceForm,setVoiceForm]=useState({nom:'',langue:'',provider:'GEMINI',model_id:'',voice_id:'',style:''});
  const [sceneForm,setSceneForm]=useState({noeud:'',langue:'',mode:'TEXT_ONLY',image:'',video:'',audio:'',narration_texte:'',voix:''});
  const [synth,setSynth]=useState({scene:'',voix:'',texte:''});
  const supported=typeof window!=='undefined'&&'speechSynthesis' in window;
  const stop=()=>{if(supported)window.speechSynthesis.cancel();setPlaying(false)};
  useEffect(()=>()=>{if(supported)window.speechSynthesis.cancel()},[supported]);
  const preview=()=>{if(!supported||!text.trim())return;stop();const u=new SpeechSynthesisUtterance(text.trim());u.lang=lang==='mg'?'mg-MG':'fr-FR';u.rate=.95;u.onend=()=>setPlaying(false);u.onerror=()=>setPlaying(false);setPlaying(true);window.speechSynthesis.speak(u)};
  const run=async(fn)=>{setError('');try{await perform(fn);setDialog(null)}catch(e){setError(e.message)}};
  const createVoice=e=>{e.preventDefault();run(()=>studioApi.createVoice(voiceForm))};
  const createScene=e=>{e.preventDefault();const d={...sceneForm};for(const k of ['image','video','audio','voix'])if(!d[k])delete d[k];run(()=>studioApi.createScene(d))};
  const generate=e=>{e.preventDefault();run(()=>studioApi.tts(synth))};
  const render=async id=>{if(!confirm('Lancer un assemblage FFmpeg pour cette scène ?'))return;try{await perform(()=>studioApi.render(id))}catch(e){setError(e.message)}};
  return <div className="page-stack">
    <div className="stats-grid compact-stats">
      <StatCard label="Voix configurées" value={voices.length} note="Gemini / ElevenLabs" icon={Mic2} tone="purple"/>
      <StatCard label="Nœuds avec médias" value={scenes.length} note="Scènes média" icon={AudioLines} tone="blue"/>
      <StatCard label="Jobs terminés" value={jobs.filter(j=>j.statut==='SUCCESS').length} note="TTS / Rendu" icon={FileAudio} tone="purple"/>
      <StatCard label="En attente" value={jobs.filter(j=>['PENDING','RUNNING'].includes(j.statut)).length} note="Tâches asynchrones" icon={WandSparkles} tone="blue"/>
    </div>
    <div className="section-toolbar"><span className="section-hint">Synthèse vocale volontaire · aucune vidéo générée par IA</span><div className="tree-toolbar-actions"><button className="btn btn-outline" onClick={()=>refresh()}><RefreshCw size={16}/> Actualiser</button><button className="btn btn-outline" onClick={()=>{setError('');setDialog('voice')}}><Plus size={16}/> Configurer une voix</button><button className="btn btn-primary" onClick={()=>{setError('');setDialog('scene')}}><Plus size={16}/> Associer un nœud</button></div></div>
    {error&&<div className="api-banner" role="alert">{error}</div>}
    <div className="content-grid">
      <Panel title="Aperçu navigateur" icon={Mic2}><div className="form-stack"><Field label="Langue"><select value={lang} onChange={e=>{stop();setLang(e.target.value)}}><option value="fr">Français</option><option value="mg">Malagasy</option></select></Field><Field label="Texte fictif"><textarea rows={5} value={text} maxLength={2500} onChange={e=>setText(e.target.value)}/></Field><button className="btn btn-outline" disabled={!supported||!text.trim()} onClick={playing?stop:preview}>{playing?<Square size={16}/>:<Play size={16}/>} {playing?'Arrêter':'Écouter'}</button><span className="muted">Voix du navigateur : aperçu distinct de l’API serveur.</span></div></Panel>
      <Panel title="Synthèse vocale Django" icon={WandSparkles}><div className="form-stack">
        <Field label="Scène média"><select value={synth.scene} onChange={e=>setSynth(p=>({...p,scene:e.target.value}))}><option value="">Choisir une scène</option>{scenes.map(s=><option key={s.id} value={s.id}>{nodes.find(n=>n.id===s.noeud)?.titre_fr||s.noeud} · {languages.find(l=>l.id===s.langue)?.code||'?'}</option>)}</select></Field>
        <Field label="Voix"><select value={synth.voix} onChange={e=>setSynth(p=>({...p,voix:e.target.value}))}><option value="">Choisir un profil de voix</option>{voices.filter(v=>v.actif).map(v=><option key={v.id} value={v.id}>{v.nom} · {v.provider}</option>)}</select></Field>
        <Field label="Texte à convertir"><textarea rows={4} value={synth.texte} maxLength={1200} onChange={e=>setSynth(p=>({...p,texte:e.target.value}))}/></Field>
        <button className="btn btn-primary" disabled={busy||!synth.scene||!synth.voix||!synth.texte.trim()} onClick={generate}><Mic2 size={16}/> Générer avec l’API TTS</button>
        <div className="soft-note">Le texte transmis aux fournisseurs doit être entièrement fictif. La scène et la voix doivent avoir la même langue ; quota et crédits selon le fournisseur.</div>
      </div></Panel>
    </div>
    <Panel title="Scènes et rendus" icon={AudioLines}><div className="resource-list">{scenes.map(s=><div className="resource-list-row" key={s.id}><span className="resource-list-icon"><AudioLines size={18}/></span><span className="resource-list-main"><strong>{nodes.find(n=>n.id===s.noeud)?.titre_fr||s.noeud}</strong><small>{s.mode} · {languages.find(l=>l.id===s.langue)?.code||s.langue} · {s.statut}</small></span><div className="table-actions"><button disabled={s.mode==='TEXT_ONLY'||busy} className="btn btn-outline" onClick={()=>render(s.id)}>Assembler</button></div></div>)}{!scenes.length&&<div className="empty-state">Associez d'abord une scène ou une fin à une langue.</div>}</div></Panel>
    <Panel title="Traitements récents" icon={FileAudio}><div className="resource-list">{jobs.slice(0,20).map(j=><div className="resource-list-row" key={j.id}><span className="resource-list-icon"><WandSparkles size={18}/></span><span className="resource-list-main"><strong>{j.type} · {j.statut}</strong><small>{j.code_erreur||'Traitement du studio'} · {j.created_at?.slice(0,16)}</small></span>{j.resultat_url&&<span className="muted">Fichier prêt dans la médiathèque</span>}</div>)}</div></Panel>
    {dialog==='voice'&&<Dialog title="Configurer un profil TTS" onClose={()=>setDialog(null)}><form className="form-stack" onSubmit={createVoice}>
      <Field label="Nom du profil"><input required value={voiceForm.nom} onChange={e=>setVoiceForm(p=>({...p,nom:e.target.value}))}/></Field>
      <Field label="Langue"><select required value={voiceForm.langue} onChange={e=>setVoiceForm(p=>({...p,langue:e.target.value}))}><option value="">Choisir une langue</option>{languages.map(l=><option key={l.id} value={l.id}>{l.nom_fr||l.code}</option>)}</select></Field>
      <Field label="Fournisseur"><select value={voiceForm.provider} onChange={e=>setVoiceForm(p=>({...p,provider:e.target.value}))}><option value="GEMINI">Gemini</option><option value="ELEVENLABS">ElevenLabs</option></select></Field>
      <Field label="Model ID"><input required value={voiceForm.model_id} onChange={e=>setVoiceForm(p=>({...p,model_id:e.target.value}))}/></Field>
      <Field label="Voice ID"><input required value={voiceForm.voice_id} onChange={e=>setVoiceForm(p=>({...p,voice_id:e.target.value}))}/></Field>
      {error&&<p className="api-error" role="alert">{error}</p>}
      <div className="form-actions"><button type="button" className="btn btn-outline" onClick={()=>setDialog(null)}>Annuler</button><button disabled={busy} className="btn btn-primary">Enregistrer</button></div>
    </form></Dialog>}
    {dialog==='scene'&&<Dialog title="Associer un média à un nœud" onClose={()=>setDialog(null)}><form className="form-stack" onSubmit={createScene}>
      <Field label="Nœud narratif"><select required value={sceneForm.noeud} onChange={e=>setSceneForm(p=>({...p,noeud:e.target.value}))}><option value="">Choisir une scène ou une fin</option>{nodes.filter(n=>['SCENE','ENDING'].includes(n.type)).map(n=><option key={n.id} value={n.id}>{n.tantara_detail?.slug||''} · {n.titre_fr}</option>)}</select></Field>
      <Field label="Langue"><select required value={sceneForm.langue} onChange={e=>setSceneForm(p=>({...p,langue:e.target.value}))}><option value="">Choisir une langue</option>{languages.map(l=><option value={l.id} key={l.id}>{l.nom_fr||l.code}</option>)}</select></Field>
      <Field label="Mode"><select value={sceneForm.mode} onChange={e=>setSceneForm(p=>({...p,mode:e.target.value}))}><option value="TEXT_ONLY">Texte seul</option><option value="VIDEO_ORIGINAL">Vidéo avec son</option><option value="VIDEO_AUDIO">Vidéo + audio distinct</option><option value="IMAGE_AUDIO">Image + audio</option></select></Field>
      {sceneForm.mode.startsWith('VIDEO')&&<Field label="Vidéo"><select required value={sceneForm.video} onChange={e=>setSceneForm(p=>({...p,video:e.target.value}))}><option value="">Choisir une vidéo</option>{media.filter(m=>m.type==='VIDEO').map(m=><option key={m.id} value={m.id}>{m.titre}</option>)}</select></Field>}
      {sceneForm.mode==='IMAGE_AUDIO'&&<Field label="Image"><select required value={sceneForm.image} onChange={e=>setSceneForm(p=>({...p,image:e.target.value}))}><option value="">Choisir une image</option>{media.filter(m=>m.type==='IMAGE').map(m=><option key={m.id} value={m.id}>{m.titre}</option>)}</select></Field>}
      {['VIDEO_AUDIO','IMAGE_AUDIO'].includes(sceneForm.mode)&&<><Field label="Audio importé facultatif"><select value={sceneForm.audio} onChange={e=>setSceneForm(p=>({...p,audio:e.target.value}))}><option value="">Narration TTS ultérieure</option>{media.filter(m=>m.type==='AUDIO').map(m=><option key={m.id} value={m.id}>{m.titre}</option>)}</select></Field><Field label="Texte narratif facultatif"><textarea rows={2} value={sceneForm.narration_texte} onChange={e=>setSceneForm(p=>({...p,narration_texte:e.target.value}))}/></Field></>}
      {error&&<p className="api-error" role="alert">{error}</p>}
      <div className="form-actions"><button type="button" className="btn btn-outline" onClick={()=>setDialog(null)}>Annuler</button><button className="btn btn-primary" disabled={busy}>Associer</button></div>
    </form></Dialog>}
  </div>;
}
