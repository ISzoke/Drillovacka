from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0028_anonymoussession_audio_threshold_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExampleReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('report_type', models.CharField(choices=[('wrong_answer', 'Wrong Answer'), ('wrong_grade', 'Wrong Grade'), ('unclear', 'Unclear'), ('other', 'Other')], max_length=32)),
                ('note', models.TextField(blank=True, default='')),
                ('input_type', models.CharField(blank=True, default='', max_length=32)),
                ('language', models.CharField(blank=True, default='', max_length=10)),
                ('example_text', models.CharField(blank=True, default='', max_length=255)),
                ('correct_answer', models.CharField(blank=True, default='', max_length=255)),
                ('practiced_skill_ids', models.JSONField(blank=True, default=list)),
                ('practiced_skill_names', models.JSONField(blank=True, default=list)),
                ('meta', models.JSONField(blank=True, default=dict)),
                ('anonymous_session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.anonymoussession')),
                ('example', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='api.example')),
                ('student', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.student')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='examplereport',
            index=models.Index(fields=['student', 'created_at'], name='api_example_student_d44995_idx'),
        ),
        migrations.AddIndex(
            model_name='examplereport',
            index=models.Index(fields=['anonymous_session', 'created_at'], name='api_example_anonymo_6f4d5e_idx'),
        ),
        migrations.AddIndex(
            model_name='examplereport',
            index=models.Index(fields=['example', 'created_at'], name='api_example_example_502d1d_idx'),
        ),
        migrations.AddConstraint(
            model_name='examplereport',
            constraint=models.CheckConstraint(check=Q(student__isnull=False) | Q(anonymous_session__isnull=False), name='report_student_or_session_required'),
        ),
    ]
