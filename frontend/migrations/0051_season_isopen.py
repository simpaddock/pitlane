# Generated by Django 2.1.2 on 2018-10-21 09:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0050_remove_registration_ignored'),
    ]

    operations = [
        migrations.AddField(
            model_name='season',
            name='isOpen',
            field=models.BooleanField(default=True),
        ),
    ]