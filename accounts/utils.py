import random
import string
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.conf import settings

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    subject = "Your OTP Code"
    message = f"Your OTP code is: {otp}\nIt expires in 5 minutes."
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    send_mail(subject, message, from_email, recipient_list)


# accounts/utils.py
from datetime import datetime, timedelta
from django.utils import timezone  # ← Add this import

def is_otp_valid(otp_record, now=None):
    if now is None:
        now = timezone.now()  # ← Use timezone.now() for aware datetime
    return otp_record.created_at + timedelta(minutes=6) > now