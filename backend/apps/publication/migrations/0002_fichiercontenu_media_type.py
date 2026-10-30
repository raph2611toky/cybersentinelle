from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('publication', '0001_initial')]
    operations = [
        migrations.AlterField('fichiercontenu', 'type', models.CharField(max_length=16, choices=[
            ('STORY', 'Histoire'), ('QUESTIONS', 'Questions'), ('RESOURCES', 'Ressources'), ('MEDIA', 'Média audiovisuel public')
        ])),
    ]
