# Generated by Django 2.1 on 2018-09-09 17:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0017_auto_20180909_1923'),
    ]

    operations = [
        migrations.AlterField(
            model_name='season',
            name='name',
            field=models.CharField(max_length=100),
        ),
    ]
