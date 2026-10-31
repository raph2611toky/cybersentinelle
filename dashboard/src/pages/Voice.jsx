import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AudioLines, FileAudio, Mic2, Play, Square, WandSparkles, Plus, RefreshCw } from 'lucide-react';
import { Dialog, Field, Panel, StatCard } from '../components/UI';
import { useAdmin } from '../lib/store';
import { studioApi } from '../services/editor';
import { apiError } from '../services/api';

export default function Voice() {
  const { voices, scenes, jobs, languages, nodes, media, perform, refresh, busy } = useAdmin();
  const [lang,setLang] = useState('fr');
  const [text,setText] = useState('Tu peux demander de l’aide à une personne de confiance.');
  const [playing,setPlaying] = useState(false);
  const [dialog,setDialog] = useState(null);
  const [error,setError] = useState('');
  const [catalog,setCatalog] = useState([]);
  const [catalogBusy,setCatalogBusy] = useState(false);
  const [catalogNote,setCatalogNote] = useState('');
  const [voiceForm,setVoiceForm] = useState({nom:'',langue:'',provider:'GOOGLE_CLOUD',model_id:'',voice_id:'',style:''});
  const blankScene = () => ({noeud:'',langue:'',mode:'TEXT_ONLY',image:'',video:'',audio:'',narration_texte:'',voix:'',sync_mode:'FREEZE_LAST',audio_trim_start_ms:0,audio_trim_end_ms:null});
  const [sceneForm,setSceneForm] = useState(blankScene);
  const [audioUpload,setAudioUpload] = useState({file:null, title:'',licence:'',rights:false});
  const [uploadBusy,setUploadBusy] = useState(false);
  const [targetSpeed,setTargetSpeed] = useState('1');
  const [synth,setSynth] = useState({scene:'',langue:'fr',voix:'',texte:''});
  const currentVideo = media.find(m=>m.id===sceneForm.video);
  const currentAudio = media.find(m=>m.id===sceneForm.audio);
  const videoMs = currentVideo?.duree_ms ? Math.ceil(currentVideo.duree_ms / 40) * 40 : 0;
  const audioMs = currentAudio?.duree_ms || 0;
  const trimFrom = Number(sceneForm.audio_trim_start_ms || 0);
  const trimTo = sceneForm.audio_trim_end_ms === null || sceneForm.audio_trim_end_ms === '' ? audioMs : Number(sceneForm.audio_trim_end_ms);
  const selectedMs = Math.max(0, trimTo - trimFrom);
  const rate = sceneForm.sync_mode === 'FREEZE_LAST' ? 1 : videoMs ? (sceneForm.sync_mode === 'SPEED' ? audioMs / videoMs : sceneForm.sync_mode === 'TRIM' ? 1 : selectedMs / videoMs) : 1;
  const syncError = sceneForm.mode==='VIDEO_AUDIO'&&audioMs&&videoMs
    ? (!['SPEED','FREEZE_LAST'].includes(sceneForm.sync_mode)&&(trimFrom<0||trimTo<=trimFrom||trimTo>audioMs) ? 'Segment audio hors de la durée du fichier.'
    : sceneForm.sync_mode==='TRIM'&&Math.abs(selectedMs-videoMs)>20 ? 'Le segment doit avoir exactement la durée de la vidéo. Utilise « Ajuster la fin ».'
    : (!['TRIM','FREEZE_LAST'].includes(sceneForm.sync_mode)&&(rate<0.5||rate>2.5)) ? 'Vitesse nécessaire hors limites (0,5× à 2,5×). Sélectionne un segment plus court.' : '') : '';
  const formattedDuration = value => (value / 1000).toFixed(2).replace('.', ',') + ' s';
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window;
  const availableNodes = useMemo(() => nodes.filter(n => ['SCENE','ENDING'].includes(n.type)),[nodes]);
  const chosenScene = scenes.find(s => s.id === synth.scene);
  const voiceLanguage = languages.find(l=>l.id===voiceForm.langue)?.code;
  const selectedLang = languages.find(l => l.code === synth.langue);
  const voiceChoices = voices.filter(v => v.actif && (!chosenScene || v.langue===chosenScene.langue) && (!selectedLang || v.langue===selectedLang.id));
  const stop = () => {if(supported) window.speechSynthesis.cancel();setPlaying(false)};
  useEffect(() => () => {if(supported) window.speechSynthesis.cancel()},[supported]);
  const preview = () => {if(!supported||!text.trim())return;stop();const u=new SpeechSynthesisUtterance(text.trim());u.lang=lang==='mg'?'mg-MG':'fr-FR';u.rate=.95;u.onend=()=>setPlaying(false);u.onerror=()=>setPlaying(false);setPlaying(true);window.speechSynthesis.speak(u)};
  const run = async fn => {setError('');try {await perform(fn);setDialog(null)}catch(e){setError(e.message)}};
  const createVoice = e => {e.preventDefault();run(()=>studioApi.createVoice(voiceForm))};
  const createScene = e => {e.preventDefault();
    const d={...sceneForm};
    if(d.mode==='TEXT_ONLY') {d.video=null;d.image=null;d.audio=null;}
    else if(d.mode==='AUDIO_ONLY') {d.video=null;d.image=null;}
    else if(d.mode==='IMAGE_AUDIO') {d.video=null;if(!d.audio)d.audio=null;}
    else {d.image=null;if(d.mode==='VIDEO_ORIGINAL')d.audio=null;}
    if(!d.voix)d.voix=null;
    if(!d.audio)d.audio=null;
    if(!d.video)d.video=null;
    if(!d.image)d.image=null;
    if(d.audio_trim_end_ms === '')d.audio_trim_end_ms=null;
    if(syncError){setError(syncError);return;}
    run(async()=>{
    const existing=scenes.find(s=>s.noeud===d.noeud&&s.langue===d.langue);
    return existing ? studioApi.updateScene(existing.id,d) : studioApi.createScene(d);
  })};
  const loadVoices = async () => {
    setError('');setCatalog([]);setCatalogNote('');
    if(!voiceLanguage){setCatalogNote('Choisis une langue avant de rechercher les voix.');return}
    if(voiceForm.provider === 'GEMINI'){setCatalogNote('Gemini : configure un Model ID et un Voice ID compatibles dans ton compte.');return}
    setCatalogBusy(true);
    try {
      const {data}=await studioApi.voiceCatalog(voiceForm.provider,voiceLanguage);
      setCatalog(data.results||[]);
      setCatalogNote(data.results?.length ? `${data.results.length} voix proposées par le compte. L'accès effectif et les quotas sont contrôlés à la synthèse.` : 'Aucune voix disponible pour cette langue auprès de ce fournisseur.');
    } catch(e){setCatalogNote(apiError(e))} finally{setCatalogBusy(false)}
  };
  const generate = async e => {
    e.preventDefault();setError('');
    if(!synth.voix||!synth.texte.trim()||!synth.scene) return;
    try {
      await perform(async()=>{
        let sceneId=synth.scene;
        let scene=scenes.find(s=>String(s.id)===String(sceneId));
        if(sceneId.startsWith('node:')) {
          const nodeId=sceneId.slice(5);
          const langObj=languages.find(l=>l.code===synth.langue);
          if(!langObj) throw new Error('Langue indisponible dans le backend.');
          scene=scenes.find(s=>s.noeud===nodeId&&s.langue===langObj.id);
          if(!scene){
            const resp=await studioApi.createScene({noeud:nodeId,langue:langObj.id,mode:'TEXT_ONLY'});
            scene=resp.data;
          }
          sceneId=scene.id;
        }
        if(scene.mode==='TEXT_ONLY' && !scene.video && !scene.image) {
          // La synthèse seule produit un vrai asset AUDIO, sans générer de vidéo noire.
          await studioApi.updateScene(sceneId,{mode:'AUDIO_ONLY',voix:synth.voix,narration_texte:synth.texte});
        }
        if(scene.mode==='VIDEO_ORIGINAL'&&scene.video) {
          // Générer une narration distincte sans écraser la bande sonore d'origine.
          await studioApi.updateScene(sceneId,{mode:'VIDEO_AUDIO',voix:synth.voix,narration_texte:synth.texte});
        }
        return studioApi.tts({scene:sceneId,voix:synth.voix,texte:synth.texte});
      });
    } catch(e){setError(e.message)}
  };
  const render=async id=>{if(!confirm('Assembler maintenant la vidéo et la voix avec FFmpeg ?'))return;setError('');try{await perform(()=>studioApi.render(id))}catch(e){setError(e.message)}};
  const openVoice=()=>{setError('');setCatalog([]);setCatalogNote('');setVoiceForm(f=>({...f,langue:f.langue||languages.find(l=>l.code==='fr')?.id||''}));setDialog('voice')};
  const openScene=()=>{setError('');setAudioUpload({file:null,title:'',licence:'',rights:false});setSceneForm({...blankScene(),langue:languages.find(l=>l.code==='fr')?.id||''});setDialog('scene')};
  const editScene=(sc)=>{setError('');setAudioUpload({file:null,title:'',licence:'',rights:false});setSceneForm({
    noeud:sc.noeud,langue:sc.langue,mode:sc.mode,image:sc.image||'',video:sc.video||'',audio:sc.audio||'',
    narration_texte:sc.narration_texte||'',voix:sc.voix||'',sync_mode:sc.sync_mode||'FREEZE_LAST',
    audio_trim_start_ms:sc.audio_trim_start_ms||0,audio_trim_end_ms:sc.audio_trim_end_ms??null,
  });setDialog('scene')};
  const uploadAudio=async()=>{
    if(!audioUpload.file||!audioUpload.licence.trim()||!audioUpload.title.trim()||!audioUpload.rights)return;
    setUploadBusy(true);setError('');
    try{
      const data=new FormData();
      data.append('fichier',audioUpload.file);data.append('type','AUDIO');
      data.append('titre',audioUpload.title);data.append('licence',audioUpload.licence);
      data.append('droits_confirmes','true');
      const lc=languages.find(l=>l.id===sceneForm.langue)?.code;if(lc)data.append('langue',lc);
      const resp=await studioApi.upload(data);
      setSceneForm(v=>({...v,audio:resp.data.id}));
      await refresh();
      setAudioUpload({file:null,title:'',licence:'',rights:false});
    }catch(e){setError(apiError(e))}finally{setUploadBusy(false)}
  };
  return <div className="page-stack">
    <div className="stats-grid compact-stats">
      <StatCard label="Voix configurées" value={voices.length} note="Google Cloud / ElevenLabs / Gemini" icon={Mic2} tone="purple"/>
      <StatCard label="Nœuds avec médias" value={scenes.length} note="Scènes et fins" icon={AudioLines} tone="blue"/>
      <StatCard label="Jobs terminés" value={jobs.filter(j=>j.statut==='SUCCESS').length} note="TTS / Rendu" icon={FileAudio} tone="purple"/>
      <StatCard label="En attente" value={jobs.filter(j=>['PENDING','RUNNING'].includes(j.statut)).length} note="Tâches asynchrones" icon={WandSparkles} tone="blue"/>
    </div>
    <div className="section-toolbar"><span className="section-hint">Studio audio et montage FFmpeg · les scènes proviennent des nœuds appliqués dans Django</span><div className="tree-toolbar-actions">
      <button className="btn btn-outline" onClick={()=>refresh()}><RefreshCw size={16}/> Actualiser</button>
      <button className="btn btn-outline" onClick={openVoice}><Plus size={16}/> Configurer une voix</button>
      <button className="btn btn-primary" onClick={openScene}><Plus size={16}/> Associer un nœud</button>
    </div></div>
    {error&&<div className="api-banner" role="alert">{error}</div>}
    {!availableNodes.length&&<div className="api-banner">Aucune scène n'est appliquée dans Django. Dans <Link to="/arbre">Arbres narratifs</Link>, enregistre le graphe, attends la traduction FR/MG puis clique « Appliquer au backend ». Les brouillons seuls ne créent pas de nœuds.</div>}
    <div className="content-grid">
      <Panel title="Aperçu navigateur" icon={Mic2}><div className="form-stack">
        <Field label="Langue"><select value={lang} onChange={e=>{stop();setLang(e.target.value)}}><option value="fr">Français</option><option value="mg">Malagasy</option></select></Field>
        <Field label="Texte fictif"><textarea rows={5} value={text} maxLength={2500} onChange={e=>setText(e.target.value)}/></Field>
        <button className="btn btn-outline" disabled={!supported||!text.trim()} onClick={playing?stop:preview}>{playing?<Square size={16}/>:<Play size={16}/>} {playing?'Arrêter':'Écouter'}</button>
        <span className="muted">Aperçu local gratuit, dépendant des voix installées dans le navigateur (pas d'export audio serveur).</span>
      </div></Panel>
      <Panel title="Synthèse vocale Django" icon={WandSparkles}><form className="form-stack" onSubmit={generate}>
        <Field label="Langue"><select value={synth.langue} onChange={e=>setSynth(s=>({...s,langue:e.target.value,scene:'',voix:''}))}><option value="fr">Français</option><option value="mg">Malagasy</option></select></Field>
        <Field label="Scène / fin narrative"><select value={synth.scene} onChange={e=>setSynth(p=>({...p,scene:e.target.value,voix:''}))} required>
          <option value="">Choisir une scène ou une fin</option>
          {availableNodes.map(n=>{
            const match=scenes.find(s=>s.noeud===n.id&&s.langue===selectedLang?.id);
            return <option key={n.id} value={match?.id||`node:${n.id}`}>{n.titre_fr} · {match ? match.mode : 'Montage à créer automatiquement'}</option>;
          })}
        </select></Field>
        <Field label="Voix enregistrée"><select value={synth.voix} onChange={e=>setSynth(p=>({...p,voix:e.target.value}))} required>
          <option value="">Choisir un profil de voix</option>{voiceChoices.map(v=><option key={v.id} value={v.id}>{v.nom} · {v.provider}</option>)}
        </select></Field>
        {!voiceChoices.length&&<span className="muted">Aucune voix configurée pour cette langue. Clique sur « Configurer une voix » pour consulter les fournisseurs.</span>}
        <Field label="Texte à convertir"><textarea rows={4} value={synth.texte} maxLength={1200} onChange={e=>setSynth(p=>({...p,texte:e.target.value}))} required/></Field>
        <button type="submit" className="btn btn-primary" disabled={busy||!synth.scene||!synth.voix||!synth.texte.trim()}><Mic2 size={16}/> Générer la voix et préparer le rendu</button>
        <div className="soft-note">Lorsque la scène possède déjà une image ou vidéo, le TTS déclenche automatiquement l'assemblage après réussite. Si aucun visuel n'est associé, la narration est conservée comme audio seul. Google Cloud possède un quota gratuit limité et peut facturer les dépassements.</div>
      </form></Panel>
    </div>
    <Panel title="Scènes et rendus" icon={AudioLines}><div className="resource-list">
      {scenes.map(s=><div className="resource-list-row" key={s.id}><span className="resource-list-icon"><AudioLines size={18}/></span><span className="resource-list-main"><strong>{nodes.find(n=>n.id===s.noeud)?.titre_fr||s.noeud}</strong><small>{s.mode} · {languages.find(l=>l.id===s.langue)?.code||s.langue} · {s.statut}</small></span><div className="table-actions"><button className="btn btn-outline" disabled={busy} onClick={()=>editScene(s)}>Modifier</button>
      <button disabled={s.mode==='TEXT_ONLY'||busy} className="btn btn-outline" onClick={()=>render(s.id)}>{s.mode==='AUDIO_ONLY'?'Finaliser la voix':'Assembler'}</button>
      {(s.audio_finale_url||s.video_finale_url)&&<a className="btn btn-outline" href={s.audio_finale_url||s.video_finale_url} target="_blank" rel="noopener noreferrer">Écouter / Voir</a>}</div></div>)}
      {!scenes.length&&<div className="empty-state">Les nœuds narratifs s'affichent au-dessus après application de l'arbre. Associe leur média ou prépare un montage.</div>}
    </div></Panel>
    <Panel title="Traitements récents" icon={FileAudio}><div className="resource-list">{jobs.slice(0,20).map(j=><div className="resource-list-row" key={j.id}><span className="resource-list-icon"><WandSparkles size={18}/></span><span className="resource-list-main"><strong>{j.type} · {j.statut}</strong><small>{j.code_erreur||'Traitement du studio'} · {j.created_at?.slice(0,16)}</small></span>{j.resultat_url&&<span className="muted">Fichier prêt dans la médiathèque</span>}</div>)}</div></Panel>
    {dialog==='voice'&&<Dialog title="Configurer une voix TTS" onClose={()=>setDialog(null)}><form className="form-stack" onSubmit={createVoice}>
      <Field label="Langue"><select required value={voiceForm.langue} onChange={e=>{setVoiceForm(p=>({...p,langue:e.target.value,voice_id:''}));setCatalog([])}}><option value="">Choisir une langue</option>{languages.map(l=><option key={l.id} value={l.id}>{l.nom_fr||l.code}</option>)}</select></Field>
      <Field label="Fournisseur"><select value={voiceForm.provider} onChange={e=>{setVoiceForm(p=>({...p,provider:e.target.value,model_id:'',voice_id:''}));setCatalog([])}}><option value="GOOGLE_CLOUD">Google Cloud TTS (quota limité)</option><option value="ELEVENLABS">ElevenLabs (plan gratuit limité)</option><option value="GEMINI">Gemini</option></select></Field>
      {voiceForm.provider!=='GEMINI'&&<button className="btn btn-outline" type="button" onClick={loadVoices} disabled={catalogBusy||!voiceForm.langue}><RefreshCw size={15}/>{catalogBusy?'Recherche…':'Charger les voix disponibles'}</button>}
      {catalogNote&&<p className="form-hint">{catalogNote}</p>}
      {!!catalog.length&&<Field label="Voix proposées par l'API"><select value="" onChange={e=>{const v=catalog[Number(e.target.value)];if(v)setVoiceForm(p=>({...p,nom:v.name,model_id:v.model_id,voice_id:v.voice_id}))}}><option value="">Choisir une voix</option>{catalog.map((v,i)=><option value={String(i)} key={v.voice_id}>{v.name} · {v.provider}</option>)}</select></Field>}
      <Field label="Nom du profil"><input required value={voiceForm.nom} onChange={e=>setVoiceForm(p=>({...p,nom:e.target.value}))}/></Field>
      <Field label="Model ID"><input required value={voiceForm.model_id} onChange={e=>setVoiceForm(p=>({...p,model_id:e.target.value}))}/></Field>
      <Field label="Voice ID"><input required value={voiceForm.voice_id} onChange={e=>setVoiceForm(p=>({...p,voice_id:e.target.value}))}/></Field>
      <div className="soft-note">L'affichage d'une voix dans le catalogue ne garantit pas qu'elle soit autorisée par ton abonnement. Aucune génération sans action explicite.</div>
      {error&&<p className="api-error" role="alert">{error}</p>}
      <div className="form-actions"><button type="button" className="btn btn-outline" onClick={()=>setDialog(null)}>Annuler</button><button disabled={busy} className="btn btn-primary">Enregistrer</button></div>
    </form></Dialog>}
    {dialog==='scene'&&<Dialog title="Configurer les médias et la narration" onClose={()=>setDialog(null)}><form className="form-stack" onSubmit={createScene}>
      <Field label="Nœud narratif"><select required value={sceneForm.noeud} onChange={e=>setSceneForm(p=>({...p,noeud:e.target.value}))}><option value="">Choisir une scène ou une fin</option>{availableNodes.map(n=><option key={n.id} value={n.id}>{n.titre_fr}</option>)}</select></Field>
      {!availableNodes.length&&<p className="form-hint">Le graphe doit d'abord être appliqué au backend.</p>}
      <Field label="Langue"><select required value={sceneForm.langue} onChange={e=>setSceneForm(p=>({...p,langue:e.target.value}))}><option value="">Choisir une langue</option>{languages.map(l=><option key={l.id} value={l.id}>{l.nom_fr||l.code}</option>)}</select></Field>
      <Field label="Mode"><select value={sceneForm.mode} onChange={e=>setSceneForm(p=>({...p,mode:e.target.value}))}><option value="TEXT_ONLY">Texte seul</option><option value="AUDIO_ONLY">Voix uniquement (sans vidéo)</option><option value="VIDEO_ORIGINAL">Vidéo avec son</option><option value="VIDEO_AUDIO">Vidéo + narration distincte</option><option value="IMAGE_AUDIO">Image + narration</option></select></Field>
      {sceneForm.mode.startsWith('VIDEO')&&<Field label="Vidéo"><select required value={sceneForm.video} onChange={e=>setSceneForm(p=>({...p,video:e.target.value}))}><option value="">Choisir une vidéo</option>{media.filter(m=>m.type==='VIDEO'&&m.droits_confirmes).map(m=><option key={m.id} value={m.id}>{m.titre}</option>)}</select></Field>}
      {sceneForm.mode==='IMAGE_AUDIO'&&<Field label="Image"><select required value={sceneForm.image} onChange={e=>setSceneForm(p=>({...p,image:e.target.value}))}><option value="">Choisir une image</option>{media.filter(m=>m.type==='IMAGE'&&m.droits_confirmes).map(m=><option key={m.id} value={m.id}>{m.titre}</option>)}</select></Field>}
      {['VIDEO_AUDIO','IMAGE_AUDIO','AUDIO_ONLY'].includes(sceneForm.mode)&&<>
        <Field label="Audio importé / enregistré (sans texte obligatoire)"><select value={sceneForm.audio} onChange={e=>setSceneForm(p=>({...p,audio:e.target.value}))}><option value="">Aucun — synthèse TTS facultative plus tard</option>{media.filter(m=>m.type==='AUDIO'&&m.droits_confirmes).map(m=><option key={m.id} value={m.id}>{m.titre}</option>)}</select></Field>
        <div className="soft-note">Ou importer une voix déjà enregistrée directement dans la médiathèque privée :</div>
        <Field label="Fichier audio (MP3, WAV, M4A, OGG)"><input type="file" accept="audio/mpeg,audio/mp4,audio/wav,audio/ogg,.mp3,.wav,.m4a,.ogg" onChange={e=>{const file=e.target.files?.[0]||null;setAudioUpload(v=>({...v,file,title:file?.name?.replace(/\.[^.]+$/, '')||''}))}} /></Field>
        {audioUpload.file&&<>
          <Field label="Titre du fichier"><input value={audioUpload.title} onChange={e=>setAudioUpload(v=>({...v,title:e.target.value}))}/></Field>
          <Field label="Licence / provenance"><input value={audioUpload.licence} onChange={e=>setAudioUpload(v=>({...v,licence:e.target.value}))}/></Field>
          <label className="form-hint"><input type="checkbox" checked={audioUpload.rights} onChange={e=>setAudioUpload(v=>({...v,rights:e.target.checked}))}/> Je confirme la provenance et les droits de ce fichier fictif.</label>
          <button type="button" className="btn btn-outline" disabled={uploadBusy||!audioUpload.rights||!audioUpload.licence.trim()||!audioUpload.title.trim()} onClick={uploadAudio}>{uploadBusy?'Import…':'Importer puis sélectionner cette voix'}</button>
        </>}
        <Field label="Voix"><select value={sceneForm.voix} onChange={e=>setSceneForm(p=>({...p,voix:e.target.value}))}><option value="">Choisir une voix ultérieurement</option>{voices.filter(v=>v.actif&&v.langue===sceneForm.langue).map(v=><option key={v.id} value={v.id}>{v.nom}</option>)}</select></Field>
        <Field label="Narration TTS facultative"><textarea rows={3} value={sceneForm.narration_texte} onChange={e=>setSceneForm(p=>({...p,narration_texte:e.target.value}))}/></Field>
        {sceneForm.mode==='VIDEO_AUDIO'&&<div className="form-stack" style={{border:'1px solid #45415c',padding:14}}>
          <strong>Synchronisation audio / vidéo</strong>
          <small className="muted">La voix et la vidéo démarrent ensemble. En mode « Figer la dernière image », aucune parole n'est coupée et la vitesse ne change pas. Les autres réglages restent disponibles.</small>
          <div className="form-hint">Vidéo : {videoMs?formattedDuration(videoMs):'à sélectionner'} · Audio : {audioMs?formattedDuration(audioMs):'à importer ou générer'}</div>
          <Field label="Méthode d'ajustement"><select value={sceneForm.sync_mode} onChange={e=>setSceneForm(v=>({...v,sync_mode:e.target.value,audio_trim_start_ms:0,audio_trim_end_ms:null}))}>
            <option value="FREEZE_LAST">Conserver les durées · figer la dernière image si besoin (recommandé)</option>
            <option value="SPEED">Adapter la vitesse de toute la voix</option>
            <option value="TRIM">Découper un segment (vitesse 1×)</option>
            <option value="TRIM_SPEED">Découper puis ajuster sa vitesse</option>
          </select></Field>
          {!['SPEED','FREEZE_LAST'].includes(sceneForm.sync_mode)&&<>
            <Field label="Début du segment audio (secondes)"><input type="number" min="0" step="0.01" value={trimFrom/1000} onChange={e=>setSceneForm(v=>({...v,audio_trim_start_ms:Math.round(Number(e.target.value)*1000)}))}/></Field>
            <Field label="Fin du segment audio (secondes)"><input type="number" min="0" step="0.01" value={sceneForm.audio_trim_end_ms===null?'':Number(sceneForm.audio_trim_end_ms)/1000} placeholder="Fin du fichier" onChange={e=>setSceneForm(v=>({...v,audio_trim_end_ms:e.target.value===''?null:Math.round(Number(e.target.value)*1000)}))}/></Field>
            {videoMs>0&&<button type="button" className="btn btn-outline" onClick={()=>setSceneForm(v=>({...v,audio_trim_end_ms:Number(v.audio_trim_start_ms||0)+videoMs}))}>Ajuster la fin à la durée vidéo (1×)</button>}
          </>}
          {sceneForm.sync_mode==='TRIM_SPEED'&&videoMs>0&&<>
            <Field label="Vitesse souhaitée (0,5× à 2,5×)"><input type="number" min="0.5" max="2.5" step="0.05" value={targetSpeed} onChange={e=>{setTargetSpeed(e.target.value);const speed=Number(e.target.value);if(Number.isFinite(speed)&&speed>=0.5&&speed<=2.5)setSceneForm(v=>({...v,audio_trim_end_ms:Math.round(Number(v.audio_trim_start_ms||0)+videoMs*speed)}))}}/></Field>
            <small className="muted">Changer la vitesse ajuste automatiquement la fin du segment. Tu peux aussi ajuster librement les bornes.</small>
          </>}
          {audioMs>0&&videoMs>0&&<strong className="form-hint">{sceneForm.sync_mode==='FREEZE_LAST'
            ? `Audio intégral : ${formattedDuration(audioMs)} · Vidéo originale : ${formattedDuration(videoMs)} · Durée finale : ${formattedDuration(Math.max(audioMs,videoMs))} · Dernière image figée pendant ${formattedDuration(Math.max(0,audioMs-videoMs))}`
            : `Segment : ${formattedDuration(sceneForm.sync_mode==='SPEED'?audioMs:selectedMs)} · Vitesse appliquée : ${rate.toFixed(2)}× · Durée finale cible : ${formattedDuration(videoMs)}`}</strong>}
          {syncError&&<p className="api-error" role="alert">{syncError}</p>}
          <small className="muted">Mode durées libres : audio naturel à 1×, aucune coupe, fin de la vidéo figée à sa résolution native. Si la voix est plus courte, l'image animée continue jusqu'à la fin de la vidéo. Les autres modes conservent leurs limites de vitesse et de découpage.</small>
        </div>}
      </>}
      {error&&<p className="api-error" role="alert">{error}</p>}
      <div className="form-actions"><button type="button" className="btn btn-outline" onClick={()=>setDialog(null)}>Annuler</button><button className="btn btn-primary" disabled={busy||uploadBusy||!availableNodes.length||!!syncError}>Enregistrer</button></div>
    </form></Dialog>}
  </div>;
}
