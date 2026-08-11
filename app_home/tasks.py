# app_home/tasks.py
import logging
from celery import shared_task
from django.apps import apps
from notifications.helpers import create_notification

logger = logging.getLogger(__name__)

@shared_task
def send_bulk_product_notification(product_id):
    # Use apps.get_model to avoid circular imports
    Product = apps.get_model('app_home', 'Product')
    CustomUser = apps.get_model('accounts', 'CustomUser')

    try:
        product = Product.objects.get(id=product_id)
        
        # 1. Fetch all active users (only IDs and emails to save memory)
        users = CustomUser.objects.filter(is_active=True)
        user_count = users.count()
        
        logger.info(f"Starting bulk notification for {product.name} to {user_count} users.")

        # 2. Loop through users and create notifications
        for user in users:
            create_notification(
                user=user,
                title="✨ New Spiritual Tool",
                message=f"Check out our new {product.name} in the store!",
                notif_type='store_update',
                data={"type": "product", "product_id": str(product.id)}
            )
            
        return f"Successfully notified {user_count} users about {product.name}."

    except Product.DoesNotExist:
        return f"Product {product_id} no longer exists."
    except Exception as e:
        logger.error(f"Bulk notification error: {str(e)}")
        return f"Failed: {str(e)}"


@shared_task
def send_daily_inspiration_reminder():
    """
    Sends a daily inspiration (random quote) to all active users.
    Scheduled in settings.py via CELERY_BEAT_SCHEDULE.
    """
    Quote = apps.get_model('app_home', 'Quote')
    CustomUser = apps.get_model('accounts', 'CustomUser')

    try:
        # 1. Get a random active quote
        quote = Quote.objects.filter(is_active=True).order_by('?').first()
        if not quote:
            logger.warning("No active quotes found for daily inspiration.")
            return "No active quotes found."

        # 2. Fetch all active users
        users = CustomUser.objects.filter(is_active=True)
        user_count = users.count()

        logger.info(f"Sending daily inspiration: '{quote.text[:30]}...' to {user_count} users.")

        # 3. Send notifications
        for user in users:
            create_notification(
                user=user,
                title="Daily Inspiration",
                message=f"\"{quote.text}\" - {quote.author or 'Unknown'}",
                notif_type='daily_inspiration',
                data={"type": "quote", "quote_id": str(quote.id)}
            )

        return f"Successfully sent daily inspiration to {user_count} users."

    except Exception as e:
        logger.error(f"Daily inspiration task error: {str(e)}")
        return f"Failed: {str(e)}"