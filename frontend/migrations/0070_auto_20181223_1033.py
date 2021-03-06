# Generated by Django 2.1.2 on 2018-12-23 09:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0069_textblock_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='textblock',
            name='mediaFileThumbnail',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='textblock',
            name='options',
            field=models.CharField(choices=[('left-image', 'Image left'), ('right-image', 'Image right'), ('top-image', 'Top right'), ('bottom-image', 'Bottom right')], default=('left-image', 'Image left'), max_length=30),
        ),
    ]
