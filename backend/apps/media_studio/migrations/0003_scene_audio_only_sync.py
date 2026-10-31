from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('media_studio', '0002_google_cloud_voice_provider')]

    operations = [
        migrations.AlterField(model_name='scenemedia', name='mode', field=models.CharField(max_length=18, default='TEXT_ONLY', choices=[('VIDEO_ORIGINAL', 'Vidéo avec audio incorporé'), ('VIDEO_AUDIO', 'Vidéo et audio séparés'), ('IMAGE_AUDIO', 'Image et audio'), ('AUDIO_ONLY', 'Audio seul'), ('TEXT_ONLY', 'Texte uniquement')])),
        migrations.AddField(model_name='scenemedia', name='audio_finale', field=models.ForeignKey(to='media_studio.mediaasset', related_name='scene_audio_renders', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True)),
        migrations.AddField(model_name='scenemedia', name='sync_mode', field=models.CharField(max_length=12, default='SPEED', choices=[('SPEED','Vitesse pour ajuster la narration entière'), ('TRIM','Découper un segment (vitesse normale)'), ('TRIM_SPEED','Découper puis ajuster la vitesse')])),
        migrations.AddField(model_name='scenemedia', name='audio_trim_start_ms', field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='scenemedia', name='audio_trim_end_ms', field=models.PositiveIntegerField(null=True, blank=True)),
    ]
