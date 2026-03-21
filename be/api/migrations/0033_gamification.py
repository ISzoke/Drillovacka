import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0032_task_grade_levels'),
    ]

    operations = [
        # Add gamification fields to Student
        migrations.AddField(
            model_name='student',
            name='total_xp',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='student',
            name='level',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='student',
            name='current_streak',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='student',
            name='longest_streak',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='student',
            name='last_practice_date',
            field=models.DateField(blank=True, null=True),
        ),
        # Create Badge model
        migrations.CreateModel(
            name='Badge',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=64, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.CharField(max_length=512)),
                ('icon', models.CharField(max_length=64)),
                ('category', models.CharField(
                    max_length=32,
                    choices=[
                        ('activity', 'Activity'),
                        ('accuracy', 'Accuracy'),
                        ('speed', 'Speed'),
                        ('streak', 'Streak'),
                        ('milestone', 'Milestone'),
                    ],
                )),
                ('xp_reward', models.IntegerField(default=0)),
            ],
        ),
        # Create StudentBadge model
        migrations.CreateModel(
            name='StudentBadge',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('earned_at', models.DateTimeField(auto_now_add=True)),
                ('student', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='earned_badges',
                    to='api.student',
                )),
                ('badge', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='student_badges',
                    to='api.badge',
                )),
            ],
            options={
                'unique_together': {('student', 'badge')},
            },
        ),
    ]
