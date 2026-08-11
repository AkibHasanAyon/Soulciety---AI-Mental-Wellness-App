# from celery import shared_task
# from firebase_admin import messaging
# from .models import Notification
# from .utils import get_firebase_app  # if you need custom init

# @shared_task
# def send_push_notification_task(notification_id):
#     try:
#         notification = Notification.objects.get(id=notification_id)
#         devices = notification.user.device_tokens.filter(is_active=True)
#         if not devices.exists():
#             return

#         tokens = [device.token for device in devices]

#         message = messaging.MulticastMessage(
#             notification=messaging.Notification(
#                 title=notification.title,
#                 body=notification.body,
#             ),
#             data=notification.data,
#             tokens=tokens,
#         )

#         response = messaging.send_multicast(message)
#         # Cleanup invalid tokens
#         for idx, resp in enumerate(response.responses):
#             if not resp.success and 'NotRegistered' in str(resp.exception or ''):
#                 devices[idx].is_active = False
#                 devices[idx].save()

#         print(f"Notification {notification_id} sent to {response.success_count} devices")
#     except Notification.DoesNotExist:
#         print(f"Notification {notification_id} not found")
#     except Exception as e:
#         print(f"Failed to send notification {notification_id}: {e}")
        




# # notifications/tasks.py
# from celery import shared_task
# from django.utils import timezone
# from .models import Notification
# from .utils import send_push_to_user

# @shared_task
# def send_push_notification_task(notification_id):
#     """
#     Celery task to send push notification after creating in-app notification
#     """
#     try:
#         notification = Notification.objects.get(id=notification_id)
#         user = notification.user

#         success = send_push_to_user(
#             user=user,
#             title=notification.title,
#             body=notification.body,
#             data=notification.data
#         )

#         # Optional: mark as sent or log
#         if success:
#             print(f"Push sent for notification {notification_id}")
#         else:
#             print(f"No active devices or push failed for notification {notification_id}")

#     except Notification.DoesNotExist:
#         print(f"Notification {notification_id} not found")
#     except Exception as e:
#         print(f"Error in push task: {e}")


# notifications/tasks.py
from celery import shared_task
from .utils import send_push_to_user
from .models import Notification

@shared_task
def send_push_notification_task(notification_id):
    try:
        notification = Notification.objects.get(id=notification_id)
        user = notification.user

        success = send_push_to_user(
            user=user,
            title=notification.title,
            body=notification.message,
            data=notification.data
        )

        if success:
            print(f"Push sent for notification {notification_id}")
        else:
            print(f"Push failed or no devices for notification {notification_id}")

    except Notification.DoesNotExist:
        print(f"Notification {notification_id} not found")
    except Exception as e:
        print(f"Push task error: {e}")



        
# from celery.schedules import crontab

# @shared_task
# def send_daily_affirmation():
#     from accounts.models import CustomUser
#     users = CustomUser.objects.filter(profile__notifications_enabled=True)
#     for user in users:
#         create_notification(
#             user,
#             "Today's Affirmation",
#             "I release what no longer serves me and welcome miracles into my life.",
#             'daily_affirmation'
#         )

# # In settings.py
# CELERY_BEAT_SCHEDULE = {
#     'send-daily-affirmation': {
#         'task': 'notifications.tasks.send_daily_affirmation',
#         'schedule': crontab(hour=8, minute=0),  # 8:00 AM UTC
#     },
# }