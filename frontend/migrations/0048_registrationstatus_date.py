# Generated by Django 2.1.2 on 2018-10-21 08:44

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0047_auto_20181021_1036'),
    ]

    operations = [
        migrations.AddField(
            model_name='registrationstatus',
            name='date',
            field=models.DateTimeField(default=datetime.datetime.now),
        ),
    ]