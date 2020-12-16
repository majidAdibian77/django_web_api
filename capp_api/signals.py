import time

from django.db.models.signals import post_save
from django.dispatch import receiver
from capp_api.models import User


@receiver(post_save, sender=User)
def check_key(sender, instance, **kwargs):
    """
    This checks key of user that send his number
    If he just send his number and doesn't verify key this fun remove it 200s after creation
    """
    if not instance.phone_verified:
        time.sleep(20)
        if not instance.phone_verified:
            instance.delete()
