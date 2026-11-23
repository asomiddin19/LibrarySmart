from django.db import migrations, models
import library.models


class Migration(migrations.Migration):
    dependencies = [('library', '0005_googleidentity')]
    operations = [
        migrations.AddField(
            model_name='book',
            name='epub',
            field=models.FileField(blank=True, upload_to=library.models.epub_path, verbose_name='EPUB fayl'),
        ),
    ]
