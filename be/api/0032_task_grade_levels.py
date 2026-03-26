from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0031_surveyfeedback'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='grade_levels',
            field=models.ManyToManyField(blank=True, related_name='tasks', to='api.gradelevel'),
        ),
    ]
