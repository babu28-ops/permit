# Generated by Django 5.2.3 on 2025-06-19 10:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('societies', '0002_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='factory',
            name='location',
        ),
        migrations.AddField(
            model_name='factory',
            name='county',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='county'),
        ),
        migrations.AddField(
            model_name='factory',
            name='date_updated',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='factory',
            name='sub_county',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='sub county'),
        ),
    ]
