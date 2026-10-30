from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("content_api", "0003_brouillongraphe")]

    operations = [
        migrations.AddField(
            model_name="tantara",
            name="image_cover",
            field=models.ImageField(upload_to="covers/%Y/%m/", null=True, blank=True),
        ),
    ]
