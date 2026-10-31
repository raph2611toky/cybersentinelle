import { useEffect, useRef, useState } from 'react';
import { Film, Play, Volume2 } from 'lucide-react';

/**
 * Lecteur unique pour les médias privés du Studio et ceux d'une release.
 * - MP4 final : une seule piste audio (déjà multiplexée par FFmpeg).
 * - Brouillon vidéo/audio : deux fichiers, départ commun à t=0 ; la vidéo
 *   reste sur sa dernière image quand l'audio est plus long.
 * - Audio seul / image+audio : lecture de la voix sans vidéo fictive.
 * Les événements de fin attendent la fin de TOUS les flux nécessaires.
 */
export default function ScenePlayback({ video = '', audio = '', image = '', embeddedAudio = false, title = '', onFinished }) {
  const videoRef = useRef(null);
  const audioRef = useRef(null);
  const completed = useRef({ video: false, audio: false, notified: false });
  const sourceHistory = useRef(null);
  const switchingTrack = useRef(false);
  const lastPlaybackTime = useRef(0);
  const [problem, setProblem] = useState('');
  const [videoFinished, setVideoFinished] = useState(false);
  const [playing, setPlaying] = useState(false);
  const paired = !!(video && audio && !embeddedAudio);
  const audioTrack = paired || (!video && !!audio);

  // Conserver la position vidéo lorsqu'on passe de la narration FR à MG.
  // Les changements de scène (nouvelle clé React) repartent normalement de zéro.
  useEffect(() => () => {videoRef.current?.pause();audioRef.current?.pause();}, []);
  useEffect(() => {
    const previous = sourceHistory.current;
    const switchTrack = previous && previous.video === video && previous.audio !== audio;
    const videoElement = videoRef.current;
    const audioElement = audioRef.current;
    const position = videoElement && !videoElement.ended ? videoElement.currentTime : lastPlaybackTime.current || 0;
    const wasPlaying = Boolean((videoElement && !videoElement.paused && !videoElement.ended) || playing);
    sourceHistory.current = {video,audio};
    completed.current = { video: !video || Boolean(videoElement?.ended), audio: !audioTrack, notified: false };
    setProblem('');
    switchingTrack.current = Boolean(switchTrack);
    if (!switchTrack) {lastPlaybackTime.current=0;setPlaying(false); setVideoFinished(false);}
    if (!switchTrack || !audioElement || !audio) {switchingTrack.current=false;return undefined;}

    let active = true;
    const resumeAudio = () => {
      if (!active) return;
      try {
        audioElement.currentTime = Number.isFinite(audioElement.duration)
          ? Math.min(position, Math.max(0, audioElement.duration - 0.02)) : position;
      } catch { /* L'audio sera repositionné à la lecture si les métadonnées tardent. */ }
      if (wasPlaying && !audioElement.ended) {
        audioElement.play().catch(() => setProblem('Nouvelle piste sélectionnée : clique sur « Lire avec le son » pour autoriser la narration.'));
      }
      switchingTrack.current=false;
    };
    audioElement.addEventListener('loadedmetadata', resumeAudio, {once:true});
    if (audioElement.readyState >= 1) resumeAudio();
    return () => {active = false;audioElement.removeEventListener('loadedmetadata', resumeAudio);};
  }, [video, audio, audioTrack]);

  const completedPart = (part) => {
    completed.current[part] = true;
    if (!completed.current.notified && completed.current.video && completed.current.audio) {
      completed.current.notified = true;
      onFinished?.();
    }
  };

  const play = () => {
    if (playing) {
      videoRef.current?.pause();
      audioRef.current?.pause();
      setPlaying(false);
      return;
    }
    setProblem('');
    const v = videoRef.current;
    const a = audioRef.current;
    // Two play() calls occur synchronously in the SAME user gesture.
    if (paired && a && v && !v.ended) {
      if (!v.seeking && Math.abs(a.currentTime - v.currentTime) > .4 && !a.ended) {
        a.currentTime = Math.min(v.currentTime, Number.isFinite(a.duration) ? a.duration : v.currentTime);
      }
      if (!a.ended) a.play().catch(() => setProblem('La voix est bloquée par le navigateur : clique sur lecture dans la piste audio.'));
    } else if (a && !a.ended) {
      a.play().catch(() => setProblem('Clique sur le lecteur audio pour démarrer la voix.'));
    }
    if (v && !v.ended) {
      v.play().catch(() => setProblem('Clique sur le lecteur vidéo pour démarrer la lecture.'));
    }
  };

  const onVideoPlay = () => {
    setPlaying(true);
    const a = audioRef.current;
    if (paired && a && !a.ended) {
      if (Math.abs(a.currentTime - videoRef.current.currentTime) > .4) a.currentTime = videoRef.current.currentTime;
      a.play().catch(() => setProblem('Active la piste audio avec son bouton Lecture.'));
    }
  };

  const onVideoPause = () => {
    setPlaying(false);
    // Ne pas interrompre la narration lorsque la vidéo est terminée.
    if (paired && !videoRef.current?.ended && !videoRef.current?.seeking) audioRef.current?.pause();
  };

  const onVideoSeek = () => {
    const v = videoRef.current;
    const a = audioRef.current;
    if (!paired || !v || !a || !Number.isFinite(a.duration)) return;
    a.currentTime = Math.min(v.currentTime, Math.max(0, a.duration - .02));
  };

  const onAudioPlay = () => {
    setPlaying(true);
    if (paired && videoRef.current && !videoRef.current.ended && videoRef.current.paused) {
      videoRef.current.play().catch(() => setProblem('Clique sur lecture dans la vidéo pour la synchroniser.'));
    }
  };

  const onAudioPause = () => {
    if(switchingTrack.current)return;
    if (paired && !audioRef.current?.ended && videoRef.current && !videoRef.current.ended) videoRef.current.pause();
    setPlaying(false);
  };

  const onVideoEnded = () => {
    setVideoFinished(true);
    setPlaying(Boolean(audioRef.current && !audioRef.current.paused && !audioRef.current.ended));
    completedPart('video');
    // Le navigateur conserve la dernière frame ; laisser la voix poursuivre.
  };

  const onAudioEnded = () => {
    setPlaying(Boolean(videoRef.current && !videoRef.current.paused && !videoRef.current.ended));
    completedPart('audio');
  };

  const showVideo = !!video;
  const showImage = !showVideo && !!image;

  return <div className="scene-playback">
    {showVideo && <video
      ref={videoRef} src={video} controls playsInline preload="metadata"
      muted={paired} onPlay={onVideoPlay} onPause={onVideoPause}
      onSeeking={onVideoSeek} onTimeUpdate={e=>{lastPlaybackTime.current=e.currentTarget.currentTime;}} onEnded={onVideoEnded}
      onError={() => setProblem('Impossible de charger la vidéo. Vérifie les droits de lecture et le fichier.')}
      aria-label={`Vidéo de ${title}`}
    />}
    {showImage && <img src={image} alt={title || 'Illustration de la scène'} />}
    {!showVideo && !showImage && <div className="story-preview-placeholder"><Film size={36}/><span>{audio ? 'Scène avec narration audio' : 'Aucun média disponible pour cette scène'}</span></div>}
    {audioTrack && <div className="scene-playback-audio">
      <span><Volume2 size={15}/> {paired ? 'Voix de la scène · synchronisée' : 'Voix de la scène'}</span>
      <audio ref={audioRef} src={audio} controls preload="metadata" onPlay={onAudioPlay} onPause={onAudioPause} onTimeUpdate={e=>{if(!video || videoRef.current?.ended)lastPlaybackTime.current=e.currentTarget.currentTime;}} onEnded={onAudioEnded}
        onError={() => setProblem('Impossible de charger la piste audio. Vérifie le média dans la médiathèque.')} />
    </div>}
    {showVideo && embeddedAudio && <div className="scene-playback-info"><Volume2 size={14}/> Voix intégrée à la vidéo finale</div>}
    {paired && videoFinished && !completed.current.audio && <div className="scene-playback-info">Dernière image maintenue jusqu’à la fin de la voix.</div>}
    {(showVideo || audioTrack) && <button className="btn btn-outline scene-playback-start" type="button" onClick={play}>
      <Play size={15}/> {playing ? 'Pause' : 'Lire avec le son'}
    </button>}
    {problem && <p role="alert" className="api-error">{problem}</p>}
  </div>;
}
