# Generated by Django 2.1.2 on 2018-10-17 19:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0043_auto_20181017_2101'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='raceresult',
            name='season',
        ),
    ]
