from django.contrib import admin
from .models import Activity, Package, Booking, Room, Food, Tour, RoomType, RoomBooking, Notification

# Register your models here.
admin.site.register(Activity),
admin.site.register(Package),
admin.site.register(Booking),
admin.site.register(Room),
admin.site.register(Food),
admin.site.register(Tour),
admin.site.register(RoomType),
admin.site.register(RoomBooking),
admin.site.register(Notification),