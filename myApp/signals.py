from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Booking, Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@receiver(post_save, sender=Booking)
def notify_booking(sender, instance, created, **kwargs):
    if created:
        # Notify booking user
        Notification.objects.create(
            user=instance.user,
            message=f"Your booking #{instance.id} has been created.",
            type='booking'
        )
        # Notify all staff/admins
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            Notification.objects.create(
                user=admin,
                message=f"New booking #{instance.id} by {instance.user.username}",
                type='booking'
            )
        # Push to WebSocket group
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "notifications",
            {"type": "send_notification", "message": f"New booking #{instance.id}"}
        )

@receiver(post_save, sender=User)
def notify_registration(sender, instance, created, **kwargs):
    if created:
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            Notification.objects.create(
                user=admin,
                message=f"New user registered: {instance.username}",
                type='registration'
            )
        # WebSocket push
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "notifications",
            {"type": "send_notification", "message": f"New user registered: {instance.username}"}
        )
