# Generated by Django 2.1 on 2018-10-06 20:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0025_auto_20181006_2013'),
    ]

    operations = [
        migrations.AddField(
            model_name='teamentry',
            name='vehicleImage',
            field=models.FileField(blank=True, default=None, null=True, upload_to='uploads/'),
        ),
    ]
