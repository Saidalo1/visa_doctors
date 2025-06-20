# Generated by Django 5.0.2 on 2025-06-15 09:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0049_alter_result_image_alter_universitylogo_logo"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="is_title",
            field=models.BooleanField(
                default=False,
                help_text="If True, this question's answer will be used as a title in the mobile application's submission list. Only one question per survey can be marked as title.",
                verbose_name="Is Title for Mobile List",
            ),
        ),
        migrations.AddConstraint(
            model_name="question",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_title", True)),
                fields=("survey", "is_title"),
                name="unique_is_title_true_per_survey",
            ),
        ),
    ]
