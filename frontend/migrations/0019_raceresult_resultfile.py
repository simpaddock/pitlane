# Generated by Django 2.1 on 2018-09-09 17:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0018_auto_20180909_1924'),
    ]

    operations = [
        migrations.AddField(
            model_name='raceresult',
            name='resultFile',
            field=models.CharField(choices=[('rFactor 2', 'rFactor 2')], default='rFactor 2', max_length=30),
        ),
    ]
