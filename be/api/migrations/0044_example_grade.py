from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0043_example_owner_teacher'),
    ]

    operations = [
        migrations.AddField(
            model_name='example',
            name='grade',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
