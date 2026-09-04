# Hand-written (no local Django/DB available to autogenerate — see 0045 for
# the same precedent) — mirrors Django's usual CreateModel output exactly.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0048_studentinsight'),
    ]

    operations = [
        migrations.CreateModel(
            name='PrintEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('teacher', 'Teacher test'), ('parent', 'Parent/student sheet')], max_length=7)),
                ('item_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('teacher', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='print_events', to='api.teacher')),
            ],
        ),
    ]
