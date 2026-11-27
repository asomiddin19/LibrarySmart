from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('library', '0008_aimessage'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LoginEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_at_login', models.EmailField(blank=True, max_length=254)),
                ('device', models.CharField(max_length=50)),
                ('browser', models.CharField(max_length=50)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='login_events', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created']},
        ),
    ]
