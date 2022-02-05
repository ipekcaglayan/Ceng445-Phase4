# Generated by Django 4.0.1 on 2022-01-15 15:26

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('shared_photo_library', '0007_collection_cover'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='created_date',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='collection',
            name='photos',
            field=models.ManyToManyField(related_name='col_photos', to='shared_photo_library.Photo'),
        ),
    ]
