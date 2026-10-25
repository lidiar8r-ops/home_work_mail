from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache import bump_stats_cache
from .models import Mailing, MailingAttempt, Recipient


@receiver(post_save, sender=Recipient)
@receiver(post_delete, sender=Recipient)
@receiver(post_save, sender=Mailing)
@receiver(post_delete, sender=Mailing)
@receiver(post_save, sender=MailingAttempt)
@receiver(post_delete, sender=MailingAttempt)
def invalidate_stats_cache(**kwargs):
    bump_stats_cache()
