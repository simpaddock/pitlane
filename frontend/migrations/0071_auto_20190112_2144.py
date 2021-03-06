# Generated by Django 2.1.2 on 2019-01-12 20:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0070_auto_20181223_1033'),
    ]

    operations = [
        migrations.AddField(
            model_name='registration',
            name='firstName',
            field=models.CharField(default='', max_length=200),
        ),
        migrations.AddField(
            model_name='registration',
            name='lastName',
            field=models.CharField(default='', max_length=200),
        ),
        migrations.AlterField(
            model_name='textblock',
            name='context',
            field=models.CharField(choices=[('about', 'About page'), ('rule', 'Rules'), ('landing', 'Landing page'), ('signup', 'SignUp'), ('dstandings', 'Driver standings (Preseason)'), ('tstandings', 'Team standings (Preseason)')], default=('about', 'About page'), max_length=30),
        ),
        migrations.AlterField(
            model_name='textblock',
            name='options',
            field=models.CharField(choices=[('left-image', 'Image left'), ('right-image', 'Image right'), ('top-image', 'Image top'), ('bottom-image', 'Image bottom')], default=('left-image', 'Image left'), max_length=30),
        ),
    ]
