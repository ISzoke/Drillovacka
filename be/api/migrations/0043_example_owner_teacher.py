import django.db.models.deletion
from django.db import migrations, models


def backfill_teacher_examples(apps, schema_editor):
    Task = apps.get_model('api', 'Task')
    for task in Task.objects.filter(owner_teacher__isnull=False):
        task.example_set.filter(owner_teacher__isnull=True).update(owner_teacher=task.owner_teacher_id)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0042_task_generation_prompt_params'),
    ]

    operations = [
        migrations.AddField(
            model_name='example',
            name='owner_teacher',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_examples', to='api.teacher'),
        ),
        migrations.AlterField(
            model_name='example',
            name='task',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.task'),
        ),
        migrations.RunPython(backfill_teacher_examples, migrations.RunPython.noop),
    ]
