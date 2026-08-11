# notifications/helpers.py (or utils.py)
import logging
from .models import Notification
from .tasks import send_push_notification_task

logger = logging.getLogger(__name__)

def create_notification(user, title, message, notif_type, data=None):
    """
    Create in-app notification and trigger async push
    """
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notif_type,
        data=data or {}
    )

    # Trigger async push via Celery (gracefully handle if Redis/Celery is unavailable)
    try:
        send_push_notification_task.delay(notification.id)
    except Exception as e:
        logger.warning(
            "Failed to queue push notification task for notification %s: %s",
            notification.id,
            str(e)
        )

    return notification



