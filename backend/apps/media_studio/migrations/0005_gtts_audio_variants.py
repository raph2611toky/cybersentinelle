"""French gTTS default and alternative narration tracks; non-destructive data upgrade."""
import uuid
from django.db import migrations, models
import django.db.models.deletion


def seed_defaults(apps, schema_editor):
    Langue = apps.get_model('core', 'Langue')
    VoiceProfile = apps.get_model('media_studio', 'VoiceProfile')
    SceneMedia = apps.get_model('media_studio', 'SceneMedia')
    Variant = apps.get_model('media_studio', 'SceneAudioVariant')
    fr = Langue.objects.filter(code='fr').first()
    if fr:
        VoiceProfile.objects.get_or_create(
            langue=fr, provider='GTTS', model_id='gtts-fr', voice_id='fr',
            defaults={'nom': 'gTTS français (défaut)', 'actif': True},
        )
    for scene in SceneMedia.objects.exclude(audio_id=None).iterator():
        Variant.objects.get_or_create(scene_id=scene.pk, audio_id=scene.audio_id,
            defaults={'titre': 'Piste conservée (avant migration)', 'origine': 'LEGACY',
                      'voix_id': scene.voix_id, 'texte': scene.narration_texte,
                      'selected': True, 'sync_mode': scene.sync_mode,
                      'audio_trim_start_ms': scene.audio_trim_start_ms,
                      'audio_trim_end_ms': scene.audio_trim_end_ms})


class Migration(migrations.Migration):
    dependencies = [('media_studio', '0004_freeze_last_sync')]
    operations = [
        migrations.AlterField(model_name='voiceprofile', name='provider',
            field=models.CharField(max_length=12, choices=[
                ('GTTS', 'gTTS (Google Traduction, français)'),
                ('GEMINI', 'Gemini Developer API'),
                ('ELEVENLABS', 'ElevenLabs'),
                ('GOOGLE_CLOUD', 'Google Cloud Text-to-Speech'),
            ])),
        migrations.CreateModel(name='SceneAudioVariant', fields=[
            ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('titre', models.CharField(max_length=160)),
            ('origine', models.CharField(max_length=10, choices=[('TTS','Synthèse vocale'),('FILE','Fichier audio'),('LEGACY','Piste préexistante')], default='FILE')),
            ('texte', models.TextField(blank=True)),
            ('selected', models.BooleanField(default=False)),
            ('activate_on_ready', models.BooleanField(default=True)),
            ('sync_mode', models.CharField(max_length=12, choices=[('FREEZE_LAST','Durées libres : figer la dernière image après la vidéo'),('SPEED','Vitesse pour ajuster la narration entière'),('TRIM','Découper un segment (vitesse normale)'),('TRIM_SPEED','Découper puis ajuster la vitesse')], default='FREEZE_LAST')),
            ('audio_trim_start_ms', models.PositiveIntegerField(default=0)),
            ('audio_trim_end_ms', models.PositiveIntegerField(null=True, blank=True)),
            ('scene', models.ForeignKey(to='media_studio.scenemedia', on_delete=django.db.models.deletion.CASCADE, related_name='variants')),
            ('audio', models.ForeignKey(to='media_studio.mediaasset', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='scene_variants')),
            ('voix', models.ForeignKey(to='media_studio.voiceprofile', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='audio_variants')),
        ], options={'db_table':'media_studio_variant','ordering':['-created_at']}),
        migrations.AddIndex(model_name='sceneaudiovariant', index=models.Index(fields=['scene','created_at'], name='studio_variant_scene_idx')),
        migrations.AddField(model_name='generationjob', name='variante',
            field=models.ForeignKey(to='media_studio.sceneaudiovariant', on_delete=django.db.models.deletion.SET_NULL,
                null=True, blank=True, related_name='jobs')),
        migrations.RunPython(seed_defaults, reverse_code=migrations.RunPython.noop),
    ]
