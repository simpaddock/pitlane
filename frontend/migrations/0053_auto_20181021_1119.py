# Generated by Django 2.1.2 on 2018-10-21 09:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0052_registration_teamname'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registration',
            name='teamName',
            field=models.CharField(default='', max_length=200),
        ),
    ]
