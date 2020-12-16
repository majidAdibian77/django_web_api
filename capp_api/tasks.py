from celery.task import task
from celery.utils.log import get_task_logger

from capp_api.models import User


@task(name="send_feedback_email_task")
def check_user_otp(pk):
    """This task gets a user pk and check if his phone number is not verified, deletes it"""
    try:
        user = User.objects.get(pk=pk)
        if not user.phone_verified:
            user.delete()
    except:
        pass