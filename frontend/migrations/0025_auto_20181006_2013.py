# Generated by Django 2.1 on 2018-10-06 18:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0024_team_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='raceresult',
            name='commentatorInfo',
            field=models.CharField(blank=True, default=None, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='raceresult',
            name='streamLink',
            field=models.CharField(blank=True, default=None, max_length=200, null=True),
        ),
    ]
