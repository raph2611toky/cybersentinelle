"""FFprobe et rendu déterministe : narration synchronisée et jamais tronquée par -shortest.

Cas pris en charge : vidéo avec son d'origine, vidéo + narration, image + narration,
plusieurs répliques concaténées. Une bande son plus longue que la vidéo gèle sa dernière
image ; une bande son plus courte est complétée par du silence. Aucune voix synthétisée ici.
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


def render_scene(scene):
    """Produit MP4, en maintenant la vidéo visible toute la durée de l'audio.

    Tous les délais sont lus avec ffprobe : ne pas se fier à un nombre de mots,
    au nombre de caractères ou au titre du média pour calculer la narration.
    """
    from ..models import SceneMedia
    mode = scene.mode
    if mode == SceneMedia.Mode.TEXT_ONLY:
        raise RenderError('TEXT_ONLY_NO_VIDEO')
    if mode in (SceneMedia.Mode.VIDEO_ORIGINAL, SceneMedia.Mode.VIDEO_AUDIO) and not scene.video_id:
        raise RenderError('MISSING_VIDEO')
    lines = list(scene.dialogues.select_related('audio').order_by('ordre'))
    if mode in (SceneMedia.Mode.VIDEO_AUDIO, SceneMedia.Mode.IMAGE_AUDIO):
        if scene.audio_id:
            audio_paths = [scene.audio.fichier.path]
        elif lines and all(line.audio_id for line in lines):
            audio_paths = [line.audio.fichier.path for line in lines]
        else:
            raise RenderError('MISSING_AUDIO')
    else:
        audio_paths = []

    video_duration = None
    if mode == SceneMedia.Mode.IMAGE_AUDIO:
        if not scene.image_id:
            raise RenderError('MISSING_IMAGE')
    else:
        video_duration = duration_sec(scene.video.fichier.path, 'video')

    audio_duration = sum(duration_sec(path, 'audio') for path in audio_paths)
    if mode == SceneMedia.Mode.VIDEO_ORIGINAL:
        total = video_duration
    elif mode == SceneMedia.Mode.IMAGE_AUDIO:
        total = audio_duration + 0.15  # ne pas couper la dernière syllabe à la frame près
    else:
        total = max(video_duration, audio_duration + 0.15)

    max_duration = settings.STUDIO_MAX_MEDIA_SECONDS
    if total <= 0 or total > max_duration:
        raise RenderError('RENDER_DURATION_LIMIT')
    # Forcer une durée stable (arrondie au nombre de frames), marge de 1 frame.
    total = math.ceil(total * 25) / 25

    with tempfile.TemporaryDirectory(prefix='safidiko-render-') as tmp:
        output = Path(tmp) / 'output.mp4'
        if mode == SceneMedia.Mode.IMAGE_AUDIO:
            inputs = ['-loop', '1', '-framerate', '25', '-i', scene.image.fichier.path]
        else:
            inputs = ['-i', scene.video.fichier.path]
        for path in audio_paths:
            inputs += ['-i', path]
        filter_parts = []
        standard_video = 'scale=w=1280:h=720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25'
        if mode == SceneMedia.Mode.VIDEO_AUDIO and video_duration < total:
            freeze = total - video_duration
            standard_video += f',tpad=stop_mode=clone:stop_duration={freeze:.3f}'
        elif mode == SceneMedia.Mode.VIDEO_ORIGINAL:
            # Certains conteneurs ont leur dernière frame à durée-1/fps. Ne pas la supprimer.
            standard_video += ',tpad=stop_mode=clone:stop_duration=0.040'
        filter_parts.append(f'[0:v:0]{standard_video},trim=duration={total:.3f},setpts=PTS-STARTPTS[vout]')
        mapping = ['-map', '[vout]']
        if mode == SceneMedia.Mode.VIDEO_ORIGINAL:
            mapping += ['-map', '0:a:0?']
        else:
            if len(audio_paths) == 1:
                prefix = '[1:a:0]'
            else:
                prefix = '[combined]'
                filter_parts.append(''.join(f'[{i}:a:0]' for i in range(1, len(audio_paths)+1))
                                    + f'concat=n={len(audio_paths)}:v=0:a=1{prefix}')
            filter_parts.append(f'{prefix}aresample=48000,apad=whole_dur={total:.3f},atrim=duration={total:.3f},asetpts=PTS-STARTPTS[aout]')
            mapping += ['-map', '[aout]']

        command = [
            'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
            *inputs, '-filter_complex', ';'.join(filter_parts), *mapping,
            '-t', f'{total:.3f}', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-preset', 'veryfast', '-crf', '26', '-c:a', 'aac', '-b:a', '128k',
            '-movflags', '+faststart', str(output),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, timeout=settings.STUDIO_RENDER_TIMEOUT)
        except FileNotFoundError:
            raise RenderError('FFMPEG_NOT_INSTALLED') from None
        except subprocess.TimeoutExpired:
            raise RenderError('RENDER_TIMEOUT') from None
        except subprocess.CalledProcessError:
            raise RenderError('RENDER_FAILED') from None
        if not output.is_file() or not output.stat().st_size:
            raise RenderError('RENDER_EMPTY')
        if output.stat().st_size > settings.STUDIO_MAX_OUTPUT_BYTES:
            raise RenderError('RENDER_TOO_LARGE')
        # Contrôle réel : erreur >2 frames => ne pas publier un clip tronqué.
        actual = duration_sec(output, 'video')
        if abs(actual - total) > 0.12:
            raise RenderError('RENDER_DURATION_MISMATCH')
        return output.read_bytes()
