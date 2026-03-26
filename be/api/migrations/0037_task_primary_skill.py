from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0036_generated_task_batch'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='primary_skill',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='task',
                to='api.skill',
            ),
        ),
    ]
