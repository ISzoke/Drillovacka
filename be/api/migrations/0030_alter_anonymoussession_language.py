from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0029_examplereport'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anonymoussession',
            name='language',
            field=models.CharField(
                choices=[('cs', 'Czech'), ('sk', 'Slovak'), ('en', 'English')],
                default='sk',
                max_length=2,
            ),
        ),
    ]
