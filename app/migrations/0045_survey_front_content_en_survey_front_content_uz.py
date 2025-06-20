# Generated by Django 5.0.2 on 2025-06-12 17:09

import app.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0044_survey_front_content"),
    ]

    operations = [
        migrations.AddField(
            model_name="survey",
            name="front_content_en",
            field=app.fields.FrontContentField(
                blank=True,
                default=dict,
                help_text='JSON object with "front_title" and "front_subtitle". Use &lt;span&gt; for styling.',
                null=True,
                verbose_name="Frontend Content",
            ),
        ),
        migrations.AddField(
            model_name="survey",
            name="front_content_uz",
            field=app.fields.FrontContentField(
                blank=True,
                default=dict,
                help_text='JSON object with "front_title" and "front_subtitle". Use &lt;span&gt; for styling.',
                null=True,
                verbose_name="Frontend Content",
            ),
        ),
    ]
