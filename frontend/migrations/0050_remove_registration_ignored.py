# Generated by Django 2.1.2 on 2018-10-21 09:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0049_auto_20181021_1057'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='registration',
            name='ignored',
        ),
    ]