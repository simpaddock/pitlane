# Generated by Django 2.1 on 2018-08-25 10:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0004_newsarticle'),
    ]

    operations = [
        migrations.AddField(
            model_name='track',
            name='lat',
            field=models.FloatField(default=None),
        ),
        migrations.AddField(
            model_name='track',
            name='long',
            field=models.FloatField(default=None),
        ),
    ]
