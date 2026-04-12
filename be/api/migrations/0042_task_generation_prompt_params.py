from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0041_teacher_classroom_task_owner_teacher_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='generation_prompt',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='task',
            name='generation_params',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
