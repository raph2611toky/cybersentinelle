"""Nouveau mode par défaut pour les scènes créées après migration.
Les scènes existantes conservent SPEED, TRIM ou TRIM_SPEED.
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('media_studio', '0003_scene_audio_only_sync')]

    operations = [
        migrations.AlterField(
            model_name='scenemedia',
            name='sync_mode',
            field=models.CharField(
                max_length=12,
                default='FREEZE_LAST',
                choices=[
                    ('FREEZE_LAST', 'Durées libres : figer la dernière image après la vidéo'),
                    ('SPEED', 'Vitesse pour ajuster la narration entière'),
                    ('TRIM', 'Découper un segment (vitesse normale)'),
                    ('TRIM_SPEED', 'Découper puis ajuster la vitesse'),
                ],
            ),
        ),
    ]
