from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0030_alter_anonymoussession_language'),
    ]

    operations = [
        migrations.CreateModel(
            name='SurveyFeedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('question_type', models.CharField(blank=True, default='', max_length=64)),
                ('question_text', models.TextField(blank=True, default='')),
                ('answer', models.TextField(blank=True, default='')),
                ('source', models.CharField(choices=[('text', 'Text'), ('voice', 'Voice')], default='text', max_length=16)),
                ('language', models.CharField(blank=True, default='', max_length=10)),
                ('practiced_skill_ids', models.JSONField(blank=True, default=list)),
                ('practiced_skill_names', models.JSONField(blank=True, default=list)),
                ('audio_file_path', models.CharField(blank=True, default='', max_length=500)),
                ('audio_format', models.CharField(blank=True, default='', max_length=50)),
                ('meta', models.JSONField(blank=True, default=dict)),
                ('anonymous_session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.anonymoussession')),
                ('student', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.student')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='surveyfeedback',
            index=models.Index(fields=['student', 'created_at'], name='api_surveyf_student_466689_idx'),
        ),
        migrations.AddIndex(
            model_name='surveyfeedback',
            index=models.Index(fields=['anonymous_session', 'created_at'], name='api_surveyf_anonymo_5944f8_idx'),
        ),
        migrations.AddIndex(
            model_name='surveyfeedback',
            index=models.Index(fields=['question_type', 'created_at'], name='api_surveyf_questio_11b2bb_idx'),
        ),
        migrations.AddConstraint(
            model_name='surveyfeedback',
            constraint=models.CheckConstraint(
                check=Q(student__isnull=False) | Q(anonymous_session__isnull=False),
                name='survey_feedback_student_or_session_required',
            ),
        ),
    ]
