# Generated by Django 2.1.2 on 2018-11-23 18:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0058_auto_20181122_2147'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='raceoverlaycontrolset',
            name='race',
        ),
        migrations.AlterField(
            model_name='newsarticle',
            name='mediaFile',
            field=models.ImageField(blank=True, default=None, upload_to='uploads/news/'),
        ),
        migrations.DeleteModel(
            name='RaceOverlayControlSet',
        ),
    ]
