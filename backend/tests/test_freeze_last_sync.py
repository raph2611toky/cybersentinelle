"""Vérifie les clips vidéo avec narration de durée libre (aucun réseau)."""
from io import BytesIO
import shutil
import subprocess
from types import SimpleNamespace

import pytest
from PIL import Image, ImageChops, ImageStat

from apps.media_studio.models import SceneMedia
from apps.media_studio.services.video import render_scene, probe


class EmptyDialogues:
    def select_related(self, *args):
        return self

    def order_by(self, *args):
        return []


def make_audio(path, duration):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                    f'sine=frequency=480:duration={duration}', '-ar', '48000',
                    '-c:a', 'pcm_s16le', str(path)], check=True)


def make_video(path):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                    'testsrc2=size=160x90:rate=25:duration=1.2',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)], check=True)


def make_scene(video, audio, sync_mode):
    return SimpleNamespace(
        mode=SceneMedia.Mode.VIDEO_AUDIO, sync_mode=sync_mode,
        audio_trim_start_ms=0, audio_trim_end_ms=None,
        image_id=None, video_id='video', audio_id='audio',
        video=SimpleNamespace(fichier=SimpleNamespace(path=str(video))),
        audio=SimpleNamespace(fichier=SimpleNamespace(path=str(audio))),
        dialogues=EmptyDialogues(),
    )


def frame_at(video, seconds):
    proc = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(seconds),
                           '-i', str(video), '-frames:v', '1',
                           '-f', 'image2pipe', '-vcodec', 'png', '-'],
                          capture_output=True, check=True)
    return Image.open(BytesIO(proc.stdout)).convert('RGB')


@pytest.mark.skipif(not (shutil.which('ffmpeg') and shutil.which('ffprobe')),
                    reason='FFmpeg/FFprobe absent')
@pytest.mark.parametrize('audio_seconds,expected', [(2.4, 2.4), (0.6, 1.2)])
def test_freeze_last_preserves_audio_and_native_video_size(tmp_path, settings, audio_seconds, expected):
    settings.STUDIO_RENDER_TIMEOUT = 90
    settings.STUDIO_MAX_MEDIA_SECONDS = 20
    settings.STUDIO_MAX_OUTPUT_BYTES = 50_000_000
    video = tmp_path / 'src.mp4'
    audio = tmp_path / 'voice.wav'
    make_video(video)
    make_audio(audio, audio_seconds)
    scene = make_scene(video, audio, SceneMedia.SyncMode.FREEZE_LAST)
    output = tmp_path / 'combined.mp4'
    output.write_bytes(render_scene(scene))
    streams = probe(output)['streams']
    v = next(s for s in streams if s['codec_type'] == 'video')
    a = next(s for s in streams if s['codec_type'] == 'audio')
    assert (v['width'], v['height']) == (160, 90)  # Aucun upscale artificiel.
    assert abs(float(v['duration']) - expected) < 0.085
    assert abs(float(a['duration']) - expected) < 0.085
    if audio_seconds > 1.2:
        # Les P-frames H.264 peuvent présenter une différence infime lors du
        # décodage : comparaison visuelle plutôt que digest identique.
        diff = ImageChops.difference(frame_at(output, 1.60), frame_at(output, 2.20))
        assert max(ImageStat.Stat(diff).mean) < 1.5


def test_freeze_last_is_default_for_new_scene():
    assert SceneMedia._meta.get_field('sync_mode').default == 'FREEZE_LAST'
