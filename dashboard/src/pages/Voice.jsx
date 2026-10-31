import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AudioLines, FileAudio, Mic2, Play, Square, WandSparkles, Plus, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';
import { Dialog, Field, Panel, StatCard } from '../components/UI';
import { useAdmin } from '../lib/store';
import { studioApi } from '../services/editor';
import { apiError } from '../services/api';
import ScenePlayback from '../components/ScenePlayback';
import { draftSceneSources } from '../lib/sceneAudio';

export default function Voice() {
  const { voices, scenes, jobs, languages, nodes, stories, media, perform, refresh, busy } = useAdmin();
  const [storyId,setStoryId]=useState('');
  const [activeStudioTab,setActiveStudioTab]=useState('scenes');
  const [expanded,setExpanded]=useState({browser:false, django:false});
  const [previewLang,setPreviewLang]=useState('fr');
  const activeStoryId=storyId || stories[0]?.id || '';
  const [trackOnly,setTrackOnly]=useState(false);
  const [quickTrack,setQuickTrack] = useState(null);
  const [quickFile,setQuickFile] = useState(null);
  const [quickRights,setQuickRights] = useState(false);
  const [quickSource,setQuickSource] = useState('file');
  const [quickSaving,setQuickSaving] = useState(false);
  const [quickError,setQuickError] = useState('');
  const [lang,setLang] = useState('fr');
  const [text,setText] = useState('Tu peux demander de l’aide à une personne de confiance.');
  const [playing,setPlaying] = useState(false);
  const [dialog,setDialog] = useState(null);
  const [previewSceneId,setPreviewSceneId] = useState(null);
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
  const mediaById = (id) => media.find(m=>String(m.id)===String(id));
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
  const uniqueMediaNodes = useMemo(() => new Set(scenes.map(s => String(s.noeud))).size, [scenes]);
  const storyNodes = useMemo(() => stories.filter(story=>String(story.id)===String(activeStoryId)).map(story => ({ story, items: nodes.filter(n => String(n.tantara) === String(story.id)) })).filter(g => g.items.length), [stories, nodes, activeStoryId]);
  const nodeScene = (nodeId, code) => { const id = languages.find(l => l.code === code)?.id; return scenes.find(s => String(s.noeud) === String(nodeId) && String(s.langue) === String(id)); };
  const openNodeForLanguage = (node, code) => { const l = languages.find(item => item.code === code); if (!l) return; setError(''); setAudioUpload({file:null,title:'',licence:'',rights:false}); const fr=nodeScene(node.id,'fr');setSceneForm({...blankScene(), noeud:node.id, langue:l.id,video:fr?.video||'',image:fr?.image||'',mode:fr?.video?'VIDEO_AUDIO':fr?.image?'IMAGE_AUDIO':'AUDIO_ONLY',narration_texte:code==='fr'?node.texte_fr||'':'',voix:voices.find(v=>v.actif&&v.langue===l.id)?.id||''}); setDialog('scene'); };
  const latestJob = (sceneId, type) => jobs.find(job => String(job.scene) === String(sceneId) && (!type || job.type === type));
  const jobFailureLabel = code => ({
    QUEUE_UNAVAILABLE:'Worker indisponible (broker Celery)',
    TTS_PROVIDER_DISABLED:'Fournisseur TTS désactivé',
    TTS_VOICE_INVALID:'Voix TTS invalide',
    MISSING_AUDIO:'Piste source introuvable',
    FFMPEG_NOT_INSTALLED:'FFmpeg absent du worker',
    RENDER_FAILED:'Échec du rendu FFmpeg',
    TTS_DAILY_LIMIT:'Quota TTS épuisé',
  })[code] || code || 'Erreur inconnue';
  const trackStatus = (nodeId, code) => {
    const scene = nodeScene(nodeId, code);
    if (!scene) return { label: code === 'mg' ? 'Facultative · absente' : 'Absente', state:'missing' };
    const job = latestJob(scene.id);
    const status = job?.statut;
    if (status === 'PENDING') return {label:`En attente du worker · ${job.type}${job.created_at && Date.now()-new Date(job.created_at).getTime()>120000 ? ' (vérifier Celery)' : ''}`,state:'pending'};
    if (status === 'RUNNING') return {label:`En cours · ${job.type}`,state:'running'};
    if (status === 'FAILED' && scene.statut !== 'READY') return {label:`Échec · ${jobFailureLabel(job.code_erreur)}`,state:'failed'};
    if (scene.statut === 'READY' && scene.audio_finale) return mediaById(scene.audio)?.droits_confirmes === false || mediaById(scene.audio_finale)?.droits_confirmes === false ? {label:'Terminé · droits à valider',state:'draft'} : {label:'Terminé · piste finalisée',state:'ready'};
    if (scene.audio) return {label:'Fichier reçu · rendu à terminer',state:'draft'};
    if (scene.narration_texte) return {label:'Texte enregistré · aucun worker TTS actif',state:'draft'};
    return {label:'Aucune tâche ni piste',state:'missing'};
  };
  const openQuickTrack = (node, code) => {
    const scene = nodeScene(node.id,code);
    const french = nodeScene(node.id,'fr');
    setQuickFile(null);setQuickRights(false);setQuickError('');
    setQuickSource(code === 'mg' ? 'file' : (scene?.audio ? 'file' : 'text'));
    setQuickTrack({nodeId:node.id,language:code,existing:scene?.id || '',
      audio:scene?.audio || scene?.audio_finale || '',
      text:scene?.narration_texte || (code === 'fr' ? node.texte_fr || '' : ''),
      voice:scene?.voix || voices.find(v=>v.actif && String(v.langue)===String(languages.find(l=>l.code===code)?.id))?.id || '',
      sync_mode:scene?.sync_mode || 'FREEZE_LAST',
      audio_trim_start_ms:scene?.audio_trim_start_ms || 0,
      audio_trim_end_ms:scene?.audio_trim_end_ms ?? null,
      video:scene?.video || french?.video || '',
      image:scene?.image || french?.image || ''});
    setDialog('track');
  };
  const saveQuickTrack = async event => {
    event.preventDefault();
    if (!quickTrack || quickSaving) return;
    setQuickError('');
    const language = languages.find(item=>item.code===quickTrack.language);
    if (!language) {setQuickError('Langue indisponible dans Django.');return;}
    if (quickSource==='file' && !quickFile && !quickTrack.audio) {setQuickError('Choisis un fichier audio pour cette piste.');return;}
    if (quickSource==='file' && quickFile && !quickRights) {setQuickError('Confirme les droits de diffusion de cette voix.');return;}
    if (quickSource==='text' && !quickTrack.text.trim()) {setQuickError('Renseigne le texte français à lire.');return;}
    setQuickSaving(true);
    try {
      const suppliedVoice = voices.find(v=>v.actif && String(v.id)===String(quickTrack.voice) && String(v.langue)===String(language.id)) || voices.find(v=>v.actif && String(v.langue)===String(language.id));
      let audioId = quickSource === 'file' ? quickTrack.audio || null : null;
      if (quickSource === 'file' && quickFile) {
        const form = new FormData();
        form.append('fichier',quickFile);
        form.append('type','AUDIO');
        form.append('langue',quickTrack.language);
        form.append('titre',quickFile.name.replace(/\.[^.]+$/, '').slice(0,200) || 'Narration');
        form.append('licence','Voix importée par l’administrateur · droits de diffusion confirmés');
        form.append('droits_confirmes','true');
        const uploaded = await studioApi.upload(form);
        audioId = uploaded.data.id;
        setQuickFile(null);
        setQuickTrack(p=>({...p,audio:audioId}));
      }
      const existing = scenes.find(s => String(s.noeud)===String(quickTrack.nodeId) && String(s.langue)===String(language.id));
      const payload = {
        noeud:quickTrack.nodeId,langue:language.id,
        mode: quickTrack.video ? 'VIDEO_AUDIO' : quickTrack.image ? 'IMAGE_AUDIO' : 'AUDIO_ONLY',
        video: quickTrack.video || null, image:quickTrack.video ? null : (quickTrack.image || null),
        audio:audioId,
        voix:quickSource==='text' ? (suppliedVoice?.id || null) : null,
        narration_texte:quickSource==='text' ? quickTrack.text.trim() : '',
        sync_mode:quickTrack.sync_mode,
        audio_trim_start_ms:Number(quickTrack.audio_trim_start_ms || 0),
        audio_trim_end_ms:quickTrack.audio_trim_end_ms === '' ? null : quickTrack.audio_trim_end_ms,
      };
      const saved = existing ? await studioApi.updateScene(existing.id,payload) : await studioApi.createScene(payload);
      if (audioId) await studioApi.render(saved.data.id);
      await refresh();
      setDialog(null);setQuickTrack(null);
    } catch (e) {
      setQuickError(apiError(e));
      await refresh().catch(()=>{});
    } finally {setQuickSaving(false);}
  };
  const chosenScene = scenes.find(s => s.id === synth.scene);
  const voiceLanguage = languages.find(l=>l.id===voiceForm.langue)?.code;
  const selectedLang = languages.find(l => l.code === synth.langue);
  const toggleExpand = key => setExpanded(previous => ({...previous,[key]:!previous[key]}));
  const showScenePreview = (id, code = 'fr') => { setPreviewLang(code);setPreviewSceneId(id);setActiveStudioTab('renders'); };
  useEffect(() => {
    if (activeStudioTab !== 'renders' || !previewSceneId) return;
    document.getElementById(`scene-${previewSceneId}`)?.scrollIntoView({behavior:'smooth',block:'nearest'});
  }, [activeStudioTab, previewSceneId]);
  const voiceChoices = voices.filter(v => v.actif && (!chosenScene || v.langue===chosenScene.langue) && (!selectedLang || v.langue===selectedLang.id));
  useEffect(()=>{if(!jobs.some(j=>['PENDING','RUNNING'].includes(j.statut)))return;const timer=setInterval(()=>refresh(),4000);return()=>clearInterval(timer)},[jobs,refresh]);
  const stop = () => {if(supported) window.speechSynthesis.cancel();setPlaying(false)};
  useEffect(() => () => {if(supported) window.speechSynthesis.cancel()},[supported]);
  const preview = () => {if(!supported||!text.trim())return;stop();const u=new SpeechSynthesisUtterance(text.trim());u.lang=lang==='mg'?'mg-MG':'fr-FR';u.rate=.95;u.onend=()=>setPlaying(false);u.onerror=()=>setPlaying(false);setPlaying(true);window.speechSynthesis.speak(u)};
  const run = async fn => {setError('');try {await perform(fn);setDialog(null)}catch(e){setError(e.message)}};
  const createVoice = e => {e.preventDefault();run(()=>studioApi.createVoice(voiceForm))};
  const createScene = e => {e.preventDefault();
    const d={...sceneForm};
    if(trackOnly)d.mode=d.video?'VIDEO_AUDIO':d.image?'IMAGE_AUDIO':'AUDIO_ONLY';
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
    if(trackOnly&&!d.audio&&!d.narration_texte.trim()&&languages.find(l=>l.id===d.langue)?.code==='mg'){setError('Fournis un fichier ou le texte malagasy.');return;}
    run(async()=>{
    const existing=scenes.find(s=>s.noeud===d.noeud&&s.langue===d.langue);
    const response=existing ? await studioApi.updateScene(existing.id,d) : await studioApi.createScene(d);
    if(d.audio)await studioApi.render(response.data.id);
    return response;
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
    try {await perform(async()=>{
      const nodeId=synth.scene.startsWith('node:')?synth.scene.slice(5):scenes.find(s=>s.id===synth.scene)?.noeud;
      const language=languages.find(l=>l.code===synth.langue);
      const existing=nodeScene(nodeId,synth.langue);
      const base=existing||nodeScene(nodeId,'fr');
      const data={noeud:nodeId,langue:language.id,voix:synth.voix,narration_texte:synth.texte,audio:null,
        video:base?.video||null,image:base?.image||null,mode:base?.video?'VIDEO_AUDIO':base?.image?'IMAGE_AUDIO':'AUDIO_ONLY'};
      return existing?studioApi.updateScene(existing.id,data):studioApi.createScene(data);
    })}catch(e){setError(e.message)}
  };
  const render=async id=>{if(!confirm('Assembler maintenant la vidéo et la voix avec FFmpeg ?'))return;setError('');try{await perform(()=>studioApi.render(id))}catch(e){setError(e.message)}};
  const openVoice=()=>{setError('');setCatalog([]);setCatalogNote('');setVoiceForm(f=>({...f,langue:f.langue||languages.find(l=>l.code==='fr')?.id||''}));setDialog('voice')};
  const openScene=()=>{setTrackOnly(false);setError('');setAudioUpload({file:null,title:'',licence:'',rights:false});setSceneForm({...blankScene(),langue:languages.find(l=>l.code==='fr')?.id||''});setDialog('scene')};
  const editScene=(sc, audioOnly=false)=>{setTrackOnly(audioOnly);setError('');setAudioUpload({file:null,title:'',licence:'',rights:false});setSceneForm({
    noeud:sc.noeud,langue:sc.langue,mode:audioOnly?(sc.video?'VIDEO_AUDIO':sc.image?'IMAGE_AUDIO':'AUDIO_ONLY'):sc.mode,image:sc.image||'',video:sc.video||'',audio:sc.audio||'',
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
      <StatCard label="Nœuds distincts" value={uniqueMediaNodes} note={`${scenes.length} variantes FR/MG`} icon={AudioLines} tone="blue"/>
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
    <div className="voice-collapsible-grid">
      <section className="cut-card panel voice-collapsible">
        <button type="button" className="voice-collapse-header" onClick={()=>toggleExpand('browser')} aria-expanded={expanded.browser}>
          <Mic2 size={17}/> <strong>Aperçu navigateur</strong>{expanded.browser?<ChevronDown size={17}/>:<ChevronRight size={17}/>}
        </button>
        {expanded.browser && <div className="voice-collapse-body"><div className="form-stack">
        <Field label="Langue"><select value={lang} onChange={e=>{stop();setLang(e.target.value)}}><option value="fr">Français</option><option value="mg">Malagasy</option></select></Field>
        <Field label="Texte fictif"><textarea rows={5} value={text} maxLength={2500} onChange={e=>setText(e.target.value)}/></Field>
        <button className="btn btn-outline" disabled={!supported||!text.trim()} onClick={playing?stop:preview}>{playing?<Square size={16}/>:<Play size={16}/>} {playing?'Arrêter':'Écouter'}</button>
        <span className="muted">Aperçu local gratuit, dépendant des voix installées dans le navigateur (pas d'export audio serveur).</span>
      </div></div>}
      </section>
      <section className="cut-card panel voice-collapsible">
        <button type="button" className="voice-collapse-header" onClick={()=>toggleExpand('django')} aria-expanded={expanded.django}>
          <WandSparkles size={17}/> <strong>Synthèse vocale Django</strong>{expanded.django?<ChevronDown size={17}/>:<ChevronRight size={17}/>}
        </button>
        {expanded.django && <div className="voice-collapse-body"><form className="form-stack" onSubmit={generate}>
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
      </form></div>}
      </section>
    </div>
    <div className="cut-card panel voice-workspace">
      <div className="voice-workspace-tabs" role="tablist" aria-label="Outils du studio vocal">
        {[{id:'scenes',label:'Toutes les scènes du Tantara',icon:AudioLines},
          {id:'renders',label:'Scènes et rendus',icon:FileAudio},
          {id:'jobs',label:'Traitements récents',icon:WandSparkles}].map(tab=>
          <button key={tab.id} type="button" role="tab" aria-selected={activeStudioTab===tab.id}
            id={`voice-tab-${tab.id}`} aria-controls={`voice-pane-${tab.id}`}
            className={activeStudioTab===tab.id?'voice-tab selected':'voice-tab'} onClick={()=>setActiveStudioTab(tab.id)}>
            <tab.icon size={16}/>{tab.label}</button>)}
      </div>
      <div className="voice-workspace-content" id={`voice-pane-${activeStudioTab}`} role="tabpanel" aria-labelledby={`voice-tab-${activeStudioTab}`}>
    {activeStudioTab==='scenes' && <div className="form-stack voice-tab-content">
      <Field label="Tantara"><select value={activeStoryId} onChange={e=>setStoryId(e.target.value)}>{stories.map(story=><option key={story.id} value={story.id}>{story.title}</option>)}</select></Field>
      <button className="btn btn-outline" disabled={busy||!activeStoryId} onClick={async()=>{setError('');try{await perform(async()=>{const {data}=await studioApi.prepareAudio(activeStoryId);const errors=data.results.filter(r=>r.error);if(errors.length)setError(errors.map(r=>`${nodes.find(n=>n.id===r.node)?.titre_fr||r.node} : ${r.error}`).join(' · '));})}catch(e){setError(e.message)}}}>Préparer / réessayer les pistes FR manquantes</button>
      {storyNodes.map(group => <div key={group.story.id} className="story-node-group">
        <div className="story-node-heading"><strong>{group.story.title}</strong><Link className="btn btn-outline" to={`/previsualisation?story=${encodeURIComponent(group.story.id)}`}><Play size={14}/> Lire le parcours complet</Link></div>
        {group.items.map(n => <div className="story-node-row" key={n.id}>
          <div><strong>{n.titre_fr}</strong><small>{n.type === 'DECISION' ? 'DÉCISION : choix du joueur, sans vidéo' : n.type === 'ENDING' ? 'FIN' : 'SCÈNE'}</small></div>
          {n.type !== 'DECISION' && ['fr','mg'].map(code => {const sc=nodeScene(n.id,code);const status=trackStatus(n.id,code);return <div className="story-node-language" key={code}><span className={`track-status track-status-${status.state}`} title={status.label}>{code.toUpperCase()} : {status.label}</span><button className="btn btn-outline" disabled={busy} onClick={() => openQuickTrack(n,code)}>{sc?.audio || sc?.narration_texte ? 'Modifier' : 'Associer'} audio {code.toUpperCase()}</button></div>})}
          {n.type !== 'DECISION'&&<div className="story-node-actions"><button className="btn btn-outline" disabled={busy} onClick={()=>{setTrackOnly(false);const sc=nodeScene(n.id,'fr');sc?editScene(sc):openNodeForLanguage(n,'fr')}}>Paramètres</button><button className="btn btn-outline" disabled={!nodeScene(n.id,'fr')} onClick={()=>{const sc=nodeScene(n.id,'fr');if(sc)showScenePreview(sc.id,'fr')}}>Voir · FR</button></div>}
        </div>)}
      </div>)}
      {!storyNodes.length && <div className="empty-state">Aucun nœud Django appliqué. Reviens dans « Arbres narratifs », enregistre puis applique le graphe.</div>}
      <span className="muted">La narration française est obligatoire pour chaque scène et fin. La piste malagasy est facultative. Sans fichier FR, le texte de la scène est synthétisé avec une voix configurée. Un nœud narratif peut avoir deux montages distincts (FR et MG). « DRAFT » signifie que le média n'est pas encore finalisé ; « READY » indique un rendu prêt. Les décisions ne nécessitent pas de média.</span>
    </div>}
    {activeStudioTab==='renders'&&<div className="resource-list voice-tab-content">
      {scenes.map(s=><div className="resource-list-row studio-preview-row" id={`scene-${s.id}`} key={s.id}><span className="resource-list-icon"><AudioLines size={18}/></span><span className="resource-list-main"><strong>{nodes.find(n=>n.id===s.noeud)?.titre_fr||s.noeud}</strong><small>{s.mode} · {languages.find(l=>l.id===s.langue)?.code||s.langue} · {trackStatus(s.noeud,languages.find(l=>l.id===s.langue)?.code||'fr').label}</small></span><div className="table-actions"><button className="btn btn-outline" disabled={busy} onClick={()=>editScene(s)}>Modifier</button>
      {s.audio&&!mediaById(s.audio)?.droits_confirmes&&<button className="btn btn-outline" disabled={busy} onClick={()=>{const licence=window.prompt('Licence vérifiée de cette voix générée :');if(licence?.trim())run(async()=>{await studioApi.confirmRights(s.audio,licence.trim());await studioApi.render(s.id)})}}>Valider les droits de la voix</button>}
      <button disabled={s.mode==='TEXT_ONLY'||busy} className="btn btn-outline" onClick={()=>render(s.id)}>{s.mode==='AUDIO_ONLY'?'Finaliser la voix':'Assembler'}</button>
      <button type="button" className="btn btn-outline" onClick={()=>{setPreviewLang(languages.find(l=>l.id===s.langue)?.code||'fr');setPreviewSceneId(p=>p===s.id?null:s.id)}}>{previewSceneId===s.id?'Fermer l’aperçu':'Écouter / Voir'}</button></div>
      {previewSceneId===s.id&&<div className="studio-scene-preview">
        <div className="studio-preview-heading">
          <strong>Aperçu de la scène et de sa narration</strong>
          <label>Voix <select value={previewLang} onChange={e=>setPreviewLang(e.target.value)} aria-label="Langue de la piste audio">
            <option value="fr">Français (FR)</option><option value="mg">Malagasy (MG)</option>
          </select></label>
        </div>
        {(() => {
          const sources = draftSceneSources({scenes,languages,media,nodeId:s.noeud,lang:previewLang});
          return <>
            {sources.audioLanguage && sources.audioLanguage !== previewLang && <p className="form-hint" role="status">Piste {previewLang.toUpperCase()} indisponible : lecture de la piste FR.</p>}
            {!sources.audio && !sources.embeddedAudio && <p className="form-hint">Aucune narration disponible : configure ou finalise la piste FR.</p>}
            <ScenePlayback key={s.noeud} title={nodes.find(n=>n.id===s.noeud)?.titre_fr || 'Scène'}
              video={sources.video} audio={sources.audio} image={sources.image} embeddedAudio={sources.embeddedAudio}/>
          </>;
        })()}
      </div>}</div>)}
      {!scenes.length&&<div className="empty-state">Les nœuds narratifs s'affichent au-dessus après application de l'arbre. Associe leur média ou prépare un montage.</div>}
    </div>}
    {activeStudioTab==='jobs'&&<div className="resource-list voice-tab-content">{jobs.slice(0,20).map(j=><div className="resource-list-row" key={j.id}><span className="resource-list-icon"><WandSparkles size={18}/></span><span className="resource-list-main"><strong>{j.type} · {j.statut}</strong><small>{j.code_erreur||'Traitement du studio'} · {j.created_at?.slice(0,16)}</small></span>{j.resultat_url&&<span className="muted">Fichier prêt dans la médiathèque</span>}</div>)}</div>}
      </div>
    </div>
    {dialog==='track' && quickTrack && <Dialog title={`Piste ${quickTrack.language.toUpperCase()} · ${nodes.find(n=>String(n.id)===String(quickTrack.nodeId))?.titre_fr || 'Scène'}`} className="dialog-track-quick" onClose={()=>{if(!quickSaving)setDialog(null)}}>
      <form className="form-stack quick-track-form" onSubmit={saveQuickTrack}>
        {(() => {const status=trackStatus(quickTrack.nodeId,quickTrack.language);return <div className={`track-status track-status-${status.state}`} role="status">Traitement : {status.label}</div>})()}
        {quickTrack.language==='fr'&&<Field label="Source de la narration"><select value={quickSource} onChange={e=>{setQuickSource(e.target.value);setQuickFile(null);setQuickError('')}}><option value="text">Texte à lire par TTS</option><option value="file">Voix enregistrée (fichier)</option></select></Field>}
        {quickSource==='file' ? <>
          {quickTrack.audio && <div className="soft-note">Piste actuellement associée : <strong>{mediaById(quickTrack.audio)?.titre || 'Fichier audio existant'}</strong>. Conserve-la ou remplace-la ci-dessous.</div>}
          <Field label={quickTrack.audio?'Remplacer la piste audio (facultatif)':'Fichier audio (WAV, MP3, M4A ou OGG)'}><input type="file" accept=".wav,.mp3,.m4a,.ogg,audio/*" onChange={e=>{setQuickFile(e.target.files?.[0]||null);setQuickRights(false);if(e.target.files?.[0])setQuickTrack(p=>({...p,audio_trim_start_ms:0,audio_trim_end_ms:null}))}} /></Field>
          {quickFile && <label className="quick-track-rights"><input type="checkbox" checked={quickRights} onChange={e=>setQuickRights(e.target.checked)}/> Je confirme disposer des droits nécessaires pour diffuser cet audio.</label>}
          <small className="muted">Aucun fournisseur TTS à configurer : le fichier sera associé directement et finalisé par le worker FFmpeg.</small>
        </> : <>
          <Field label="Texte français à lire"><textarea rows={4} maxLength={2500} value={quickTrack.text} onChange={e=>setQuickTrack(p=>({...p,text:e.target.value}))} /></Field>
          <small className="muted">{voices.find(v=>v.actif && String(v.id)===String(quickTrack.voice))?.nom || voices.find(v=>v.actif && String(v.langue)===String(languages.find(l=>l.code==='fr')?.id))?.nom || 'Aucune voix TTS française configurée'} · la voix active sera utilisée automatiquement.</small>
          {!voices.some(v=>v.actif&&String(v.langue)===String(languages.find(l=>l.code==='fr')?.id)) && <p className="form-hint">Le texte pourra être enregistré, mais la piste FR ne pourra pas être finalisée avant de configurer une voix ou d'importer un fichier.</p>}
        </>}
        <Field label="Synchronisation de la longueur"><select value={quickTrack.sync_mode} onChange={e=>setQuickTrack(p=>({...p,sync_mode:e.target.value,audio_trim_start_ms:0,audio_trim_end_ms:null}))}>
          <option value="FREEZE_LAST">Durée originale · figer la dernière image (recommandé)</option><option value="SPEED">Adapter la vitesse de la voix à la vidéo</option><option value="TRIM">Découper un segment audio</option><option value="TRIM_SPEED">Découper puis adapter la vitesse</option>
        </select></Field>
        {['TRIM','TRIM_SPEED'].includes(quickTrack.sync_mode)&&<div className="form-two">
          <Field label="Début (secondes)"><input type="number" min="0" step="0.01" value={Number(quickTrack.audio_trim_start_ms||0)/1000} onChange={e=>setQuickTrack(p=>({...p,audio_trim_start_ms:Math.round(Number(e.target.value)*1000)}))}/></Field>
          <Field label="Fin (secondes ; vide = fin de la piste)"><input type="number" min="0" step="0.01" value={quickTrack.audio_trim_end_ms===null?'':Number(quickTrack.audio_trim_end_ms)/1000} onChange={e=>setQuickTrack(p=>({...p,audio_trim_end_ms:e.target.value===''?null:Math.round(Number(e.target.value)*1000)}))}/></Field>
        </div>}
        {quickError&&<p role="alert" className="api-error">{quickError}</p>}
        <div className="form-actions"><button type="button" className="btn btn-outline" disabled={quickSaving} onClick={()=>setDialog(null)}>Annuler</button><button type="submit" className="btn btn-primary" disabled={quickSaving||busy||(quickSource==='file'&&!quickTrack.audio&&!quickFile)||(quickFile&&!quickRights)}>{quickSaving?'Enregistrement / lancement…':'Enregistrer la piste'}</button></div>
      </form>
    </Dialog>}
    {dialog==='voice'&&<Dialog title="Configurer une voix TTS" onClose={()=>setDialog(null)}><form className="form-stack" onSubmit={createVoice}>
      <Field label="Langue"><select required value={voiceForm.langue} onChange={e=>{setVoiceForm(p=>({...p,langue:e.target.value,voice_id:''}));setCatalog([])}}><option value="">Choisir une langue</option>{languages.map(l=><option key={l.id} value={l.id}>{l.nom_fr||l.code}</option>)}</select></Field>
      <Field label="Fournisseur"><select value={voiceForm.provider} onChange={e=>{setVoiceForm(p=>({...p,provider:e.target.value,model_id:'',voice_id:''}));setCatalog([])}}><option value="GOOGLE_CLOUD">Google Cloud TTS (quota limité)</option><option value="ELEVENLABS">ElevenLabs (plan gratuit limité)</option><option value="GEMINI">Gemini</option></select></Field>
      {voiceForm.provider!=='GEMINI'&&<button className="btn btn-outline" type="button" onClick={loadVoices} disabled={catalogBusy||!voiceForm.langue}><RefreshCw size={15}/>{catalogBusy?'Recherche…':'Charger les voix disponibles'}</button>}
      {catalogNote&&<p className="form-hint">{catalogNote}</p>}
      {!!catalog.length&&<Field label="Voix proposées par l'API"><select value="" onChange={e=>{const v=catalog[Number(e.target.value)];if(v)setVoiceForm(p=>({...p,nom:v.name,model_id:v.model_id,voice_id:v.voice_id}))}}><option value="">Choisir une voix</option>{catalog.map((v,i)=><option value={String(i)} key={v.voice_id}>{v.name} · {v.provider}</option>)}</select></Field>}
      <Field label="Nom du profil"><input required value={voiceForm.nom} onChange={e=>setVoiceForm(p=>({...p,nom:e.target.value}))}/></Field>
      <Field label="Model ID"><input required value={voiceForm.model_id} onChange={e=>setVoiceForm(p=>({...p,model_id:e.target.value}))}/></Field>
      <Field label="Voice ID"><input required value={voiceForm.voice_id} onChange={e=>setVoiceForm(p=>({...p,voice_id:e.target.value}))}/></Field>
      <div className="soft-note">L'affichage d'une voix dans le catalogue ne garantit pas qu'elle soit autorisée par ton abonnement. Une voix active permet la génération automatique des narrations manquantes lors de l’enregistrement des scènes.</div>
      {error&&<p className="api-error" role="alert">{error}</p>}
      <div className="form-actions"><button type="button" className="btn btn-outline" onClick={()=>setDialog(null)}>Annuler</button><button disabled={busy} className="btn btn-primary">Enregistrer</button></div>
    </form></Dialog>}
    {dialog==='scene'&&<Dialog title="Configurer les médias et la narration" className="dialog-scene-wide" onClose={()=>setDialog(null)}><form className="form-stack scene-config-form" onSubmit={createScene}>
      <Field label="Nœud narratif"><select disabled={trackOnly} required value={sceneForm.noeud} onChange={e=>setSceneForm(p=>({...p,noeud:e.target.value}))}><option value="">Choisir une scène ou une fin</option>{availableNodes.map(n=><option key={n.id} value={n.id}>{n.titre_fr}</option>)}</select></Field>
      {!availableNodes.length&&<p className="form-hint">Le graphe doit d'abord être appliqué au backend.</p>}
      <Field label="Langue"><select disabled={trackOnly} required value={sceneForm.langue} onChange={e=>setSceneForm(p=>({...p,langue:e.target.value}))}><option value="">Choisir une langue</option>{languages.map(l=><option key={l.id} value={l.id}>{l.nom_fr||l.code}</option>)}</select></Field>
      <Field label="Mode"><select disabled={trackOnly} value={sceneForm.mode} onChange={e=>setSceneForm(p=>({...p,mode:e.target.value}))}><option value="TEXT_ONLY">Texte seul</option><option value="AUDIO_ONLY">Voix uniquement (sans vidéo)</option><option value="VIDEO_ORIGINAL">Vidéo avec son</option><option value="VIDEO_AUDIO">Vidéo + narration distincte</option><option value="IMAGE_AUDIO">Image + narration</option></select></Field>
      {sceneForm.mode.startsWith('VIDEO')&&<Field label="Vidéo"><select required value={sceneForm.video} onChange={e=>setSceneForm(p=>({...p,video:e.target.value}))}><option value="">Choisir une vidéo</option>{media.filter(m=>m.type==='VIDEO'&&m.droits_confirmes).map(m=><option key={m.id} value={m.id}>{m.titre}</option>)}</select></Field>}
      {sceneForm.mode==='IMAGE_AUDIO'&&<Field label="Image"><select required value={sceneForm.image} onChange={e=>setSceneForm(p=>({...p,image:e.target.value}))}><option value="">Choisir une image</option>{media.filter(m=>m.type==='IMAGE'&&m.droits_confirmes).map(m=><option key={m.id} value={m.id}>{m.titre}</option>)}</select></Field>}
      {['VIDEO_AUDIO','IMAGE_AUDIO','AUDIO_ONLY'].includes(sceneForm.mode)&&<>
        <Field label="Audio importé / enregistré (sans texte obligatoire)"><select value={sceneForm.audio} onChange={e=>setSceneForm(p=>({...p,audio:e.target.value}))}><option value="">Aucun fichier — générer automatiquement depuis le texte</option>{media.filter(m=>m.type==='AUDIO'&&m.droits_confirmes).map(m=><option key={m.id} value={m.id}>{m.titre}</option>)}</select></Field>
        <div className="soft-note scene-wide-note">Ou importer une voix déjà enregistrée directement dans la médiathèque privée :</div>
        <Field label="Fichier audio (MP3, WAV, M4A, OGG)"><input type="file" accept="audio/mpeg,audio/mp4,audio/wav,audio/ogg,.mp3,.wav,.m4a,.ogg" onChange={e=>{const file=e.target.files?.[0]||null;setAudioUpload(v=>({...v,file,title:file?.name?.replace(/\.[^.]+$/, '')||''}))}} /></Field>
        {audioUpload.file&&<>
          <Field label="Titre du fichier"><input value={audioUpload.title} onChange={e=>setAudioUpload(v=>({...v,title:e.target.value}))}/></Field>
          <Field label="Licence / provenance"><input value={audioUpload.licence} onChange={e=>setAudioUpload(v=>({...v,licence:e.target.value}))}/></Field>
          <label className="form-hint"><input type="checkbox" checked={audioUpload.rights} onChange={e=>setAudioUpload(v=>({...v,rights:e.target.checked}))}/> Je confirme la provenance et les droits de ce fichier fictif.</label>
          <button type="button" className="btn btn-outline" disabled={uploadBusy||!audioUpload.rights||!audioUpload.licence.trim()||!audioUpload.title.trim()} onClick={uploadAudio}>{uploadBusy?'Import…':'Importer puis sélectionner cette voix'}</button>
        </>}
        <Field label="Voix"><select value={sceneForm.voix} onChange={e=>setSceneForm(p=>({...p,voix:e.target.value}))}><option value="">Choisir une voix ultérieurement</option>{voices.filter(v=>v.actif&&v.langue===sceneForm.langue).map(v=><option key={v.id} value={v.id}>{v.nom}</option>)}</select></Field>
        {!sceneForm.audio&&!voices.some(v=>v.actif&&v.langue===sceneForm.langue)&&<p className="api-error">Configure une voix active pour cette langue avant de générer la narration. Le texte seul peut être enregistré en brouillon.</p>}
        <Field label="Texte à lire (à défaut, description française de la scène)"><textarea rows={3} value={sceneForm.narration_texte} onChange={e=>setSceneForm(p=>({...p,narration_texte:e.target.value}))}/></Field>
        {sceneForm.mode==='VIDEO_AUDIO'&&<div className="form-stack scene-sync-settings">
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
      {error&&<p className="api-error scene-wide-note" role="alert">{error}</p>}
      <div className="form-actions scene-config-actions"><button type="button" className="btn btn-outline" onClick={()=>setDialog(null)}>Annuler</button><button className="btn btn-primary" disabled={busy||uploadBusy||!availableNodes.length||!!syncError}>Enregistrer</button></div>
    </form></Dialog>}
  </div>;
}
