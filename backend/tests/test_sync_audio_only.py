"""Les fichiers restent privés ; les durées audio/vidéo doivent être égales."""
import shutil
import subprocess
from types import SimpleNamespace
import pytest
from apps.media_studio.services.video import render_scene, render_audio_only, probe, RenderError
from apps.media_studio.models import SceneMedia


class EmptyDialogues:
    def select_related(self, *args): return self
    def order_by(self, *args): return []


@pytest.mark.skipif(not (shutil.which('ffmpeg') and shutil.which('ffprobe')), reason='FFmpeg absent')
def test_audio_only_and_three_sync_strategies(tmp_path, settings):
    settings.STUDIO_MAX_MEDIA_SECONDS = 20
    settings.STUDIO_RENDER_TIMEOUT = 90
    settings.STUDIO_MAX_OUTPUT_BYTES = 40_000_000
    video = tmp_path / 'video.mp4'
    audio = tmp_path / 'voice.wav'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=blue:s=160x90:r=25:d=3',
                    '-c:v','libx264','-pix_fmt','yuv420p', str(video)], check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','sine=frequency=400:duration=6',
                    '-c:a','pcm_s16le',str(audio)], check=True)
    scene = SimpleNamespace(
        mode=SceneMedia.Mode.VIDEO_AUDIO, sync_mode=SceneMedia.SyncMode.SPEED,
        audio_trim_start_ms=0, audio_trim_end_ms=None,
        image_id=None, video_id='video', audio_id='audio',
        video=SimpleNamespace(fichier=SimpleNamespace(path=str(video))),
        audio=SimpleNamespace(fichier=SimpleNamespace(path=str(audio))),
        dialogues=EmptyDialogues(),
    )
    for strategy, start, end in [('SPEED', 0, None), ('TRIM', 1000, 4000), ('TRIM_SPEED', 1000, 5500)]:
        scene.sync_mode = strategy
        scene.audio_trim_start_ms, scene.audio_trim_end_ms = start, end
        result = tmp_path / f'{strategy}.mp4'
        result.write_bytes(render_scene(scene))
        streams = probe(result)['streams']
        v = next(item for item in streams if item['codec_type']=='video')
        a = next(item for item in streams if item['codec_type']=='audio')
        assert abs(float(v['duration'])-float(a['duration'])) <= 0.085
        assert abs(float(a['duration'])-3) <= 0.085

    scene.sync_mode = SceneMedia.SyncMode.TRIM
    scene.audio_trim_start_ms, scene.audio_trim_end_ms = 1000, 2500
    with pytest.raises(RenderError, match='TRIM_LENGTH_MUST_MATCH_VIDEO'):
        render_scene(scene)

    scene.mode=SceneMedia.Mode.AUDIO_ONLY
    audio_result=tmp_path/'result.mp3'
    audio_result.write_bytes(render_audio_only(scene))
    assert 5.9 <= float(probe(audio_result)['format']['duration']) <= 6.1
