# Generated by Django 2.1.2 on 2018-11-03 07:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0054_remove_newsarticle_teaser'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='raceresult',
            name='commentatorInfo',
        ),
        migrations.RemoveField(
            model_name='raceresult',
            name='streamLink',
        ),
        migrations.AddField(
            model_name='race',
            name='commentatorInfo',
            field=models.CharField(blank=True, default=None, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='race',
            name='streamLink',
            field=models.CharField(blank=True, default=None, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='textblock',
            name='context',
            field=models.CharField(choices=[('about', 'About page'), ('rule', 'Reglement'), ('landing', 'Landing page'), ('signup', 'SignUp')], default=('about', 'About page'), max_length=30),
        ),
    ]