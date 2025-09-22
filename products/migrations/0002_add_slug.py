# Generated manually to add missing slug field to Product model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),  # make sure 0001_initial.py exists
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="slug",
            field=models.SlugField(max_length=200, unique=True, blank=True),
        ),
    ]
