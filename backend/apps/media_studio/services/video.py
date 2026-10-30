"""FFprobe et assemblage vidéo : aucun shell et chemins issus du stockage local uniquement."""
import json
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
        proc = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(filepath)],
            capture_output=True, check=True, timeout=12)
        if len(proc.stdout) > 100_000:
            raise RenderError('INVALID_MEDIA')
        return json.loads(proc.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError):
        raise RenderError('INVALID_MEDIA') from None


def render_scene(scene):
    """Retourne des octets MP4, avec narration unique ou répliques concaténées."""
    from ..models import SceneMedia
    mode = scene.mode
    if mode == SceneMedia.Mode.TEXT_ONLY:
        raise RenderError('TEXT_ONLY_NO_VIDEO')
    if mode in {SceneMedia.Mode.VIDEO_ORIGINAL, SceneMedia.Mode.VIDEO_AUDIO} and not scene.video_id:
        raise RenderError('MISSING_VIDEO')
    dialogue_lines = list(scene.dialogues.select_related('audio').order_by('ordre'))
    if mode in {SceneMedia.Mode.VIDEO_AUDIO, SceneMedia.Mode.IMAGE_AUDIO}:
        if scene.audio_id:
            audio_paths = [scene.audio.fichier.path]
        elif dialogue_lines and all(line.audio_id for line in dialogue_lines):
            audio_paths = [line.audio.fichier.path for line in dialogue_lines]
        else:
            raise RenderError('MISSING_AUDIO')
    else:
        audio_paths = []
    with tempfile.TemporaryDirectory(prefix='safidiko-render-') as tmp:
        output = Path(tmp) / 'output.mp4'
        if mode == SceneMedia.Mode.IMAGE_AUDIO:
            if not scene.image_id:
                raise RenderError('MISSING_IMAGE')
            inputs = ['-loop', '1', '-framerate', '25', '-i', scene.image.fichier.path]
        else:
            inputs = ['-i', scene.video.fichier.path]
        for audio_path in audio_paths:
            inputs += ['-i', audio_path]
        if mode == SceneMedia.Mode.VIDEO_ORIGINAL:
            filters = []
            mapping = ['-map', '0:v:0', '-map', '0:a:0?']
        elif len(audio_paths) == 1:
            filters = []
            mapping = ['-map', '0:v:0', '-map', '1:a:0']
        else:
            filters = ['-filter_complex',
                ''.join(f'[{i}:a:0]' for i in range(1, len(audio_paths) + 1))
                + f'concat=n={len(audio_paths)}:v=0:a=1[aout]']
            mapping = ['-map', '0:v:0', '-map', '[aout]']
        command = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', *inputs, *filters, *mapping,
            '-t', str(settings.STUDIO_MAX_MEDIA_SECONDS), '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-preset', 'veryfast', '-crf', '26', '-vf', 'scale=w=1280:h=720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2',
            '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', '-shortest', str(output)]
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
        return output.read_bytes()
