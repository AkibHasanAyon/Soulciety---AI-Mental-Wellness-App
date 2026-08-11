# notifications/utils.py
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import os
import json

# Initialize Firebase safely
if not firebase_admin._apps:
    credentials_json = os.getenv('FIREBASE_CREDENTIALS')
    if credentials_json:
        cred = credentials.Certificate(json.loads(credentials_json))
    else:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)

def send_push_to_user(user, title, body, data=None):
    """Send push to all active devices of a user"""
    from .models import DeviceToken  # Local import

    devices = DeviceToken.objects.filter(user=user, is_active=True)
    if not devices.exists():
        return False

    tokens = list(devices.values_list('token', flat=True))

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        tokens=tokens,
    )

    try:
        response = messaging.send_each_for_multicast(message)
        print(f"FCM: {response.success_count} success, {response.failure_count} failed")

        # Cleanup invalid tokens
        for idx, resp in enumerate(response.responses):
            if not resp.success:
                exception_msg = str(resp.exception or "")
                if any(code in exception_msg for code in ['NotRegistered', 'InvalidRegistration']):
                    devices[idx].is_active = False
                    devices[idx].save()

        return response.success_count > 0
    except Exception as e:
        print(f"FCM send error: {e}")
        return False