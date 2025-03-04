"""Signal handlers for app models."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from app.models import SurveySubmission
from app.utils.telegram import notify_new_submission


@receiver(post_save, sender=SurveySubmission)
def notify_on_submission_create(sender, instance, created, **kwargs):
    """
    Send notification when a new survey submission is created.
    
    Args:
        sender: The model class
        instance: The actual instance being saved
        created: Boolean; True if a new record was created
        **kwargs: Additional keyword arguments
    """
    try:
        if created and instance.status == SurveySubmission.Status.NEW:
            notify_new_submission(submission_id=instance.id)
    except:
        pass
