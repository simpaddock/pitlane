# Generated by Django 2.1.2 on 2018-10-12 20:35

import ckeditor.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0035_auto_20181009_2151'),
    ]

    operations = [
        migrations.AddField(
            model_name='rule',
            name='season',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.Season'),
        ),
        migrations.AlterField(
            model_name='rule',
            name='text',
            field=ckeditor.fields.RichTextField(),
        ),
    ]
