# Generated by Django 5.0.2 on 2025-02-28 14:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0012_fix_answer_option_trigger_after"),
    ]

    operations = [
        migrations.AddField(
            model_name="answeroption",
            name="has_custom_input",
            field=models.BooleanField(
                default=False,
                help_text="Allow custom text input for this option",
                verbose_name="Has Custom Input",
            ),
        ),
    ]
