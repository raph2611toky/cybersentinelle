"""Montage FFmpeg sûr : ajuste EXPLICITEMENT l'audio à la durée vidéo.

Mode SPEED: lecture de tout l'audio à la vitesse exacte nécessaire.
Mode TRIM: coupe un segment exactement égal à la durée vidéo, vitesse 1x.
Mode TRIM_SPEED: coupe [début, fin], puis ajuste sa vitesse à la vidéo.
Mode AUDIO_ONLY: aucun visuel artificiel ; export MP3 autonome.
La durée et les flux sont vérifiés avec ffprobe avant de persister le résultat.
"""
import json
import math
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings


class RenderError(Exception):
    def __init__(self, code='RENDER_FAILED'):
        self.code = code
        super().__init__(code)


def probe(filepath):
    try:
        proc = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(filepath)],
            capture_output=True, check=True, timeout=12,
        )
        if len(proc.stdout) > 100_000:
            raise RenderError('INVALID_MEDIA')
        return json.loads(proc.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError):
        raise RenderError('INVALID_MEDIA') from None


def duration_sec(filepath, expected):
    data = probe(filepath)
    streams = data.get('streams', [])
    if not any(s.get('codec_type') == expected for s in streams):
        raise RenderError('INVALID_MEDIA_STREAM')
    try:
        duration = float(data['format']['duration'])
    except (TypeError, KeyError, ValueError, OverflowError):
        raise RenderError('INVALID_MEDIA_DURATION') from None
    if not math.isfinite(duration) or duration <= 0:
        raise RenderError('INVALID_MEDIA_DURATION')
    return duration


def _run(command):
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=settings.STUDIO_RENDER_TIMEOUT)
    except FileNotFoundError:
        raise RenderError('FFMPEG_NOT_INSTALLED') from None
    except subprocess.TimeoutExpired:
        raise RenderError('RENDER_TIMEOUT') from None
    except subprocess.CalledProcessError:
        raise RenderError('RENDER_FAILED') from None


def _audio_sources(scene):
    if scene.audio_id:
        return [scene.audio.fichier.path]
    lines = list(scene.dialogues.select_related('audio').order_by('ordre'))
    if lines and all(line.audio_id for line in lines):
        return [line.audio.fichier.path for line in lines]
    raise RenderError('MISSING_AUDIO')


def _normalized_audio(paths, tmp):
    """Concatène en PCM après rééchantillonnage, même si les codecs diffèrent."""
    path = Path(tmp) / 'normalized.wav'
    cmd = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y']
    for src in paths:
        duration_sec(src, 'audio')
        cmd += ['-i', str(src)]
    if len(paths) == 1:
        filter_graph = '[0:a:0]aresample=48000,aformat=sample_fmts=s16:channel_layouts=stereo[a]'
    else:
        filters = []
        for idx in range(len(paths)):
            filters.append(f'[{idx}:a:0]aresample=48000,aformat=sample_fmts=s16:channel_layouts=stereo[a{idx}]')
        filters.append(''.join(f'[a{idx}]' for idx in range(len(paths))) + f'concat=n={len(paths)}:v=0:a=1[a]')
        filter_graph = ';'.join(filters)
    _run(cmd + ['-filter_complex', filter_graph, '-map', '[a]', '-c:a', 'pcm_s16le', str(path)])
    return path, duration_sec(path, 'audio')


def _sync_plan(scene, source_seconds, video_seconds):
    """Calcule le segment choisi et sa vitesse. Refuse les écarts, aucune troncature silencieuse."""
    from ..models import SceneMedia
    mode = scene.sync_mode or SceneMedia.SyncMode.SPEED
    start = (scene.audio_trim_start_ms or 0) / 1000.0
    end = (scene.audio_trim_end_ms / 1000.0) if scene.audio_trim_end_ms is not None else source_seconds
    if mode == SceneMedia.SyncMode.SPEED:
        start, end = 0.0, source_seconds
    if start < 0 or end <= start or end > source_seconds + 0.025:
        raise RenderError('INVALID_AUDIO_SEGMENT')
    end = min(end, source_seconds)
    selected = end - start
    if mode == SceneMedia.SyncMode.TRIM:
        if abs(selected - video_seconds) > 0.020:
            raise RenderError('TRIM_LENGTH_MUST_MATCH_VIDEO')
        rate = 1.0
    elif mode in {SceneMedia.SyncMode.SPEED, SceneMedia.SyncMode.TRIM_SPEED}:
        rate = selected / video_seconds
        if not 0.5 <= rate <= 2.5:
            raise RenderError('AUDIO_SPEED_OUT_OF_RANGE')
    else:
        raise RenderError('UNKNOWN_SYNC_MODE')
    return start, end, rate


def _atempo_chain(speed):
    # FFmpeg atempo est stable entre 0.5 et 2.0. Chaîner pour 2.0-2.5.
    pieces = []
    remaining = float(speed)
    while remaining > 2.0:
        pieces.append('atempo=2.0')
        remaining /= 2.0
    pieces.append(f'atempo={remaining:.9f}')
    return ','.join(pieces)


def _check_final(filepath, target, audio=True):
    stream_data = probe(filepath)['streams']
    vs = next((s for s in stream_data if s.get('codec_type') == 'video'), None)
    au = next((s for s in stream_data if s.get('codec_type') == 'audio'), None)
    if audio and not au:
        raise RenderError('RENDER_AUDIO_MISSING')
    if target > settings.STUDIO_MAX_MEDIA_SECONDS:
        raise RenderError('RENDER_DURATION_LIMIT')
    if vs:
        video_len = float(vs.get('duration') or duration_sec(filepath, 'video'))
        if abs(video_len - target) > 0.085:
            raise RenderError('RENDER_DURATION_MISMATCH')
        if audio and abs(float(au.get('duration') or target) - video_len) > 0.085:
            raise RenderError('AUDIO_VIDEO_DURATION_MISMATCH')
    elif audio and abs(duration_sec(filepath, 'audio') - target) > 0.09:
        raise RenderError('RENDER_DURATION_MISMATCH')


def _validate_result(output):
    if not output.is_file() or not output.stat().st_size:
        raise RenderError('RENDER_EMPTY')
    if output.stat().st_size > settings.STUDIO_MAX_OUTPUT_BYTES:
        raise RenderError('RENDER_TOO_LARGE')
    return output.read_bytes()


def render_audio_only(scene):
    """Scène sans image/vidéo : narration MP3 autonome (TTS ou importée)."""
    with tempfile.TemporaryDirectory(prefix='safidiko-audio-') as tmp:
        src, duration = _normalized_audio(_audio_sources(scene), tmp)
        if duration > settings.STUDIO_MAX_MEDIA_SECONDS:
            raise RenderError('RENDER_DURATION_LIMIT')
        output = Path(tmp) / 'result.mp3'
        _run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
              '-i', str(src), '-vn', '-codec:a', 'libmp3lame', '-b:a', '160k', str(output)])
        _check_final(output, duration)
        return _validate_result(output)


def render_scene(scene):
    """Produit une vidéo avec narration ayant la même durée que la vidéo source."""
    from ..models import SceneMedia
    mode = scene.mode
    if mode in (SceneMedia.Mode.TEXT_ONLY, SceneMedia.Mode.AUDIO_ONLY):
        raise RenderError('SCENE_HAS_NO_VIDEO_OUTPUT')
    if mode in {SceneMedia.Mode.VIDEO_AUDIO, SceneMedia.Mode.VIDEO_ORIGINAL} and not scene.video_id:
        raise RenderError('MISSING_VIDEO')
    if mode == SceneMedia.Mode.IMAGE_AUDIO and not scene.image_id:
        raise RenderError('MISSING_IMAGE')

    with tempfile.TemporaryDirectory(prefix='safidiko-render-') as tmp:
        if mode == SceneMedia.Mode.IMAGE_AUDIO:
            src, audio_duration = _normalized_audio(_audio_sources(scene), tmp)
            target = math.ceil(audio_duration * 25) / 25
            audio_plan = (0.0, audio_duration, 1.0)
            inputs = ['-loop', '1', '-framerate', '25', '-i', scene.image.fichier.path]
        else:
            length = duration_sec(scene.video.fichier.path, 'video')
            target = math.ceil(length * 25) / 25
            inputs = ['-i', scene.video.fichier.path]
            if mode == SceneMedia.Mode.VIDEO_AUDIO:
                src, audio_duration = _normalized_audio(_audio_sources(scene), tmp)
                audio_plan = _sync_plan(scene, audio_duration, target)
        if target <= 0 or target > settings.STUDIO_MAX_MEDIA_SECONDS:
            raise RenderError('RENDER_DURATION_LIMIT')
        filters = []
        frame = 'scale=w=1280:h=720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25'
        if mode != SceneMedia.Mode.IMAGE_AUDIO:
            # Marginale extension de dernière frame pour les vidéos à durée non multiple de 40 ms.
            frame += ',tpad=stop_mode=clone:stop_duration=0.120'
        filters.append(f'[0:v:0]{frame},trim=duration={target:.6f},setpts=PTS-STARTPTS[vout]')
        mapping = ['-map', '[vout]']
        if mode == SceneMedia.Mode.VIDEO_ORIGINAL:
            mapping += ['-map', '0:a:0?']
        else:
            inputs += ['-i', str(src)]
            start, end, speed = audio_plan
            audio_filter = (f'[1:a:0]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS,'
                            f'{_atempo_chain(speed)},aresample=48000:async=1:first_pts=0,'
                            f'apad=whole_dur={target:.6f},atrim=duration={target:.6f},'
                            'asetpts=PTS-STARTPTS[aout]')
            filters.append(audio_filter)
            mapping += ['-map', '[aout]']
        output = Path(tmp) / 'result.mp4'
        _run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
              *inputs, '-filter_complex', ';'.join(filters), *mapping,
              '-t', f'{target:.6f}', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
              '-preset', 'veryfast', '-crf', '26', '-c:a', 'aac', '-b:a', '128k',
              '-movflags', '+faststart', str(output)])
        _check_final(output, target, audio=mode != SceneMedia.Mode.VIDEO_ORIGINAL)
        return _validate_result(output)
