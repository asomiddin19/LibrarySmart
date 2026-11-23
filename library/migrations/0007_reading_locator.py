from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('library', '0006_book_epub')]
    operations = [
        migrations.AddField(
            model_name='reading', name='locator',
            field=models.CharField(blank=True, max_length=1024),
        ),
    ]
