# Generated by Django 2.1 on 2018-09-23 16:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0022_auto_20180915_0828'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='email',
            field=models.EmailField(default=None, max_length=254, null=True),
        ),
    ]