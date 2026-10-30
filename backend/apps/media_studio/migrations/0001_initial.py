"""Initial studio schema. Compatible with Django 5.2 / SQLite & MySQL."""
import uuid
import django.db.models.deletion
from django.db import migrations, models
import apps.media_studio.models


def base_fields():
    return [
    ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
    ('created_at', models.DateTimeField(auto_now_add=True)),
    ('updated_at', models.DateTimeField(auto_now=True)),
    ]


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('core', '0001_initial'),
        ('content_api', '0002_visuel_fichier_alter_visuel_chemin_asset'),
    ]
    operations = [
        migrations.CreateModel(
            name='MediaAsset',
            fields=base_fields() + [
                ('titre', models.CharField(max_length=200)),
                ('type', models.CharField(max_length=10, choices=[('IMAGE', 'Image'), ('VIDEO', 'Vidéo'), ('AUDIO', 'Audio'), ('SUBTITLE', 'Sous-titres')])),
                ('fichier', models.FileField(storage=apps.media_studio.models.PrivateStorage, upload_to=apps.media_studio.models.studio_upload_path, max_length=250)),
                ('mime_type', models.CharField(max_length=100)),
                ('taille_octets', models.PositiveBigIntegerField(default=0)),
                ('duree_ms', models.PositiveIntegerField(null=True, blank=True)),
                ('largeur_px', models.PositiveIntegerField(null=True, blank=True)),
                ('hauteur_px', models.PositiveIntegerField(null=True, blank=True)),
                ('sha256', models.CharField(max_length=64, db_index=True)),
                ('origine', models.CharField(max_length=10, choices=[('UPLOAD', 'Import manuel'), ('TTS', 'Synthèse vocale'), ('RENDER', 'Assemblage FFmpeg')], default='UPLOAD')),
                ('provider', models.CharField(max_length=20, blank=True)),
                ('langue', models.ForeignKey(to='core.langue', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='media_assets')),
                ('licence', models.CharField(max_length=160)),
                ('droits_confirmes', models.BooleanField(default=False)),
            ],
            options={'db_table': 'media_studio_asset', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='VoiceProfile',
            fields=base_fields() + [
                ('nom', models.CharField(max_length=100)),
                ('langue', models.ForeignKey(to='core.langue', on_delete=django.db.models.deletion.PROTECT, related_name='voix_studio')),
                ('provider', models.CharField(max_length=12, choices=[('GEMINI', 'Gemini Developer API'), ('ELEVENLABS', 'ElevenLabs')])),
                ('model_id', models.CharField(max_length=100)),
                ('voice_id', models.CharField(max_length=120)),
                ('style', models.CharField(max_length=150, blank=True)),
                ('actif', models.BooleanField(default=True)),
            ],
            options={'db_table': 'media_studio_voice', 'ordering': ['langue__code', 'nom']},
        ),
        migrations.CreateModel(
            name='SceneMedia',
            fields=base_fields() + [
                ('noeud', models.ForeignKey(to='content_api.noeud', on_delete=django.db.models.deletion.CASCADE, related_name='scene_media')),
                ('langue', models.ForeignKey(to='core.langue', on_delete=django.db.models.deletion.PROTECT, related_name='scene_media')),
                ('mode', models.CharField(max_length=18, choices=[('VIDEO_ORIGINAL', 'Vidéo avec audio incorporé'), ('VIDEO_AUDIO', 'Vidéo et audio séparés'), ('IMAGE_AUDIO', 'Image et audio'), ('TEXT_ONLY', 'Texte uniquement')], default='TEXT_ONLY')),
                ('image', models.ForeignKey(to='media_studio.mediaasset', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='scene_images')),
                ('video', models.ForeignKey(to='media_studio.mediaasset', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='scene_videos')),
                ('audio', models.ForeignKey(to='media_studio.mediaasset', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='scene_audios')),
                ('sous_titres', models.ForeignKey(to='media_studio.mediaasset', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='scene_subtitles')),
                ('video_finale', models.ForeignKey(to='media_studio.mediaasset', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='scene_renders')),
                ('narration_texte', models.TextField(blank=True)),
                ('voix', models.ForeignKey(to='media_studio.voiceprofile', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='scenes')),
                ('statut', models.CharField(max_length=12, choices=[('DRAFT', 'Brouillon'), ('READY', 'Prêt à publier'), ('PROCESSING', 'Rendu en cours'), ('FAILED', 'Échec du rendu')], default='DRAFT')),
            ],
            options={'db_table': 'media_studio_scene', 'ordering': ['noeud__cle', 'langue__code']},
        ),
        migrations.CreateModel(
            name='DialogueLine',
            fields=base_fields() + [
                ('scene', models.ForeignKey(to='media_studio.scenemedia', on_delete=django.db.models.deletion.CASCADE, related_name='dialogues')),
                ('ordre', models.PositiveSmallIntegerField()),
                ('personnage', models.CharField(max_length=80, blank=True)),
                ('texte', models.TextField()),
                ('voix', models.ForeignKey(to='media_studio.voiceprofile', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='dialogues')),
                ('audio', models.ForeignKey(to='media_studio.mediaasset', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='dialogues')),
            ],
            options={'db_table': 'media_studio_dialogue', 'ordering': ['ordre']},
        ),
        migrations.CreateModel(
            name='GenerationJob',
            fields=base_fields() + [
                ('type', models.CharField(max_length=8, choices=[('TTS', 'Synthèse vocale'), ('RENDER', 'Rendu vidéo local')])),
                ('statut', models.CharField(max_length=8, choices=[('PENDING', 'En attente'), ('RUNNING', 'Exécution'), ('SUCCESS', 'Terminé'), ('FAILED', 'Échec')], default='PENDING')),
                ('scene', models.ForeignKey(to='media_studio.scenemedia', on_delete=django.db.models.deletion.CASCADE, related_name='jobs')),
                ('dialogue', models.ForeignKey(to='media_studio.dialogueline', on_delete=django.db.models.deletion.CASCADE, null=True, blank=True, related_name='jobs')),
                ('voix', models.ForeignKey(to='media_studio.voiceprofile', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True)),
                ('texte', models.TextField(blank=True)),
                ('resultat', models.ForeignKey(to='media_studio.mediaasset', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='jobs')),
                ('code_erreur', models.CharField(max_length=60, blank=True)),
                ('debut_le', models.DateTimeField(null=True, blank=True)),
                ('fin_le', models.DateTimeField(null=True, blank=True)),
            ],
            options={'db_table': 'media_studio_job', 'ordering': ['-created_at']},
        ),
        migrations.AddConstraint(model_name='voiceprofile', constraint=models.UniqueConstraint(fields=('langue', 'provider', 'model_id', 'voice_id'), name='studio_unique_voice')),
        migrations.AddConstraint(model_name='scenemedia', constraint=models.UniqueConstraint(fields=('noeud', 'langue'), name='studio_unique_node_lang')),
        migrations.AddConstraint(model_name='dialogueline', constraint=models.UniqueConstraint(fields=('scene', 'ordre'), name='studio_unique_line_order')),
        migrations.AddIndex(model_name='generationjob', index=models.Index(fields=['statut', 'created_at'], name='studio_job_status_idx')),
    ]
