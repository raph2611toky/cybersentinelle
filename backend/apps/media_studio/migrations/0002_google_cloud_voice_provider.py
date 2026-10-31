from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('media_studio', '0001_initial')]
    operations = [migrations.AlterField(
        model_name='voiceprofile', name='provider',
        field=models.CharField(max_length=12, choices=[
            ('GEMINI', 'Gemini Developer API'),
            ('ELEVENLABS', 'ElevenLabs'),
            ('GOOGLE_CLOUD', 'Google Cloud Text-to-Speech'),
        ]),
    )]
