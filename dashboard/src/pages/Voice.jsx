import { useEffect, useState } from 'react';
import { AudioLines, FileAudio, Mic2, Play, Square, WandSparkles } from 'lucide-react';
import { Field, Panel, StatCard } from '../components/UI';

export default function Voice() {
  const [language,setLanguage]=useState('fr');
  const [text,setText]=useState('Tu peux demander de l’aide à une personne de confiance.');
  const [playing,setPlaying]=useState(false);
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window;
  const stop = ()=>{if(supported) window.speechSynthesis.cancel();setPlaying(false)};
  useEffect(()=>()=>{if(supported)window.speechSynthesis.cancel()},[supported]);
  const preview=()=>{
    if(!supported||!text.trim())return;
    stop();
    const utterance=new SpeechSynthesisUtterance(text.trim());
    utterance.lang=language==='mg'?'mg-MG':'fr-FR';utterance.rate=.95;
    utterance.onend=()=>setPlaying(false);utterance.onerror=()=>setPlaying(false);
    setPlaying(true);window.speechSynthesis.speak(utterance);
  };
  return <div className="page-stack">
    <div className="stats-grid compact-stats">
      <StatCard label="Lecture navigateur" value="TTS" note="Aperçu vocal local" icon={Mic2} tone="purple"/>
      <StatCard label="Langues ciblées" value="02" note="Français / Malagasy" icon={AudioLines} tone="blue"/>
      <StatCard label="Assemblage" value="FFmpeg" note="Prévu côté backend" icon={FileAudio} tone="purple"/>
      <StatCard label="API externe" value="—" note="Non connectée" icon={WandSparkles} tone="blue"/>
    </div>
    <div className="content-grid">
      <Panel title="Aperçu de narration" icon={Mic2}>
        <div className="form-stack"><Field label="Langue"><select value={language} onChange={e=>{stop();setLanguage(e.target.value)}}><option value="fr">Français</option><option value="mg">Malagasy</option></select></Field><Field label="Texte de narration"><textarea rows={7} value={text} maxLength={3000} onChange={e=>setText(e.target.value)} placeholder="Texte fictif à lire..."/></Field><div className="voice-controls"><button className="btn btn-primary" disabled={!supported||!text.trim()} onClick={playing?stop:preview}>{playing?<Square size={16}/>:<Play size={16}/>} {playing?'Arrêter':'Écouter l’aperçu'}</button><span className="muted">Voix disponibles selon le navigateur et le système.</span></div></div>
      </Panel>
      <Panel title="Studio de production" icon={AudioLines}>
        <div className="voice-visual"><div className="wave-bars" aria-hidden="true">{Array.from({length:43},(_,i)=><span key={i} style={{height:`${18+(Math.sin(i*1.9)**2)*56}%`}}/>)}</div><span>PISTE AUDIO · APERÇU</span></div>
        <div className="workflow-steps"><div><span className="step-num">01</span><div><strong>Texte</strong><small>Dialogues FR / MG</small></div></div><div><span className="step-num">02</span><div><strong>Voix</strong><small>Importer ou synthétiser</small></div></div><div><span className="step-num">03</span><div><strong>Assemblage</strong><small>Audio + vidéo via Django</small></div></div></div>
        <div className="soft-note">ElevenLabs et Gemini ne sont pas branchés. L’aperçu utilise uniquement l’API vocale disponible dans le navigateur, dont le traitement dépend du système.</div>
      </Panel>
    </div>
  </div>;
}
