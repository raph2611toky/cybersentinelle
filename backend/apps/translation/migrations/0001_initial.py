import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name='TranslationJob', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('target_type', models.CharField(max_length=80, db_index=True)),
            ('target_id', models.CharField(max_length=50, db_index=True)),
            ('path', models.JSONField()),
            ('source_text', models.TextField()),
            ('source_sha256', models.CharField(max_length=64)),
            ('state', models.CharField(default='PENDING', max_length=10, choices=[('PENDING','En attente'),('RUNNING','En cours'),('DONE','Traduction à relire'),('FAILED','Erreur'),('STALE','Remplacée')])),
            ('attempts', models.PositiveSmallIntegerField(default=0)),
            ('last_error', models.CharField(max_length=250, blank=True)),
        ],options={'db_table':'translation_job','ordering':['-created_at']}),
        migrations.AddIndex(model_name='translationjob', index=models.Index(fields=['target_type','target_id','state'], name='trans_target_state_idx')),
    ]
