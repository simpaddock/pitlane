# Generated by Django 2.1.2 on 2019-01-13 08:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0072_auto_20190113_0945'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vehicleclass',
            name='displayName',
            field=models.CharField(max_length=300, verbose_name='Vehicle display name'),
        ),
        migrations.AlterField(
            model_name='vehicleclass',
            name='vehicleClass',
            field=models.CharField(max_length=300, verbose_name='Internal name'),
        ),
    ]
