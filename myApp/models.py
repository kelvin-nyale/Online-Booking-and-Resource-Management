from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal

# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile - {self.phone}"


# # --- Activity Model ---
class Activity(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price_per_person = models.DecimalField(  # Updated field name
        max_digits=8, decimal_places=2, help_text="Price per person"
    )
    image = models.ImageField(upload_to='room_images/', blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.price_per_person}"


# --- Package Model ---
class Package(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    activities = models.ManyToManyField(Activity, related_name='packages')
    price_per_person = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price per person"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Join activity names into a comma-separated string
        activity_names = ", ".join(a.name for a in self.activities.all()) or "No Activities"
        return f"{self.name} - [{activity_names}] - {self.price_per_person}"


class RoomType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(help_text="Maximum number of guests")
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)
    total_rooms = models.PositiveIntegerField(default=1, help_text="Total rooms available for this type")
    available = models.BooleanField(default=True)

    def available_rooms(self):
        """Calculate how many rooms are free right now."""
        today = timezone.now().date()
        # Count all bookings that overlap today
        booked = RoomBooking.objects.filter(
            room_type=self,
            check_in__lte=today,
            check_out__gte=today
        ).count()
        return self.total_rooms - booked

    def __str__(self):
        return f"{self.name} ({self.available_rooms()} available)"
    
class Room(models.Model):
    name = models.CharField(max_length=100)
    room_type = models.ForeignKey('RoomType', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='room_images/', blank=True, null=True)  # New field

    def __str__(self):
        return f"{self.name} {self.room_type}"

class RoomBooking(models.Model):
    # room = models.ForeignKey(Room, on_delete=models.CASCADE)
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=150)
    customer_email = models.EmailField()
    check_in = models.DateField()
    check_out = models.DateField()
    guests = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        nights = (self.check_out - self.check_in).days
        return nights * self.room_type.price_per_night * self.room

    def overlaps(self, check_in, check_out):
        """Check if this booking overlaps a given date range."""
        return not (check_out <= self.check_in or check_in >= self.check_out)

    def __str__(self):
        return f"{self.customer_name} - {self.room_type.name} - ({self.check_in} - {self.check_out})"


class Food(models.Model):
    name = models.CharField(max_length=100)
    price_per_person = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name


class Tour(models.Model):
    name = models.CharField(max_length=100)
    destination = models.CharField(max_length=100, null=True)
    description = models.TextField()
    price_per_person = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='room_images/', blank=True, null=True)  

    def __str__(self):
        return f"{self.name} - {self.destination}"


# class Booking(models.Model):
#     user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
#     customer_name = models.CharField(max_length=100, blank=True, null=True)
#     customer_email = models.EmailField(blank=True, null=True)

#     activities = models.ManyToManyField(Activity, blank=True)
#     packages = models.ManyToManyField(Package, blank=True)
#     rooms = models.ManyToManyField(Room, blank=True)
#     food = models.ManyToManyField(Food, blank=True)
#     tours = models.ManyToManyField(Tour, blank=True)

#     check_in = models.DateField(blank=True, null=True)
#     check_out = models.DateField(blank=True, null=True)
#     pax = models.PositiveIntegerField(default=1)
#     created_at = models.DateTimeField(auto_now_add=True)

#     paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

#     @property
#     def nights_spent(self):
#         if self.check_in and self.check_out:
#             nights = (self.check_out - self.check_in).days
#             return nights if nights > 0 else 1  # Minimum of 1 night for same-day bookings
#         return 1

#     @property
#     def amount_required(self):
#         """
#         Dynamically calculate total cost:
#         - Rooms: price × pax × nights
#         - Activities/Packages/Food/Tours: price × pax
#         """
#         pax = self.pax or 1

#         # Rooms: price × guests × nights
#         room_cost = sum(room.room_type.price_per_night * pax * self.nights_spent for room in self.rooms.all())

#         # Activities, Packages, Food, Tours: price × guests
#         activity_cost = sum(a.price_per_person * pax for a in self.activities.all())
#         package_cost = sum(p.price_per_person * pax for p in self.packages.all())
#         food_cost = sum(f.price_per_person * pax for f in self.food.all())
#         tour_cost = sum(t.price_per_person * pax for t in self.tours.all())

#         return room_cost + activity_cost + package_cost + food_cost + tour_cost

#     @property
#     def balance(self):
#         return self.amount_required - self.paid
    
#     @property
#     def display_customer(self):
#         if self.customer_name:
#             return self.customer_name
#         if self.user:
#             return self.user.username
#         return "Anonymous"


#     def __str__(self):
#         return f"Booking #{self.id} - {self.customer_name or self.user.username} - {self.check_in} - {self.amount_required} - {self.pax}"

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)

    activities = models.ManyToManyField('Activity', blank=True)
    packages = models.ManyToManyField('Package', blank=True)
    rooms = models.ManyToManyField('Room', blank=True)
    food = models.ManyToManyField('Food', blank=True)
    tours = models.ManyToManyField('Tour', blank=True)

    check_in = models.DateField(blank=True, null=True)
    check_out = models.DateField(blank=True, null=True)
    pax = models.PositiveIntegerField(default=1)

    # New field to store pax details for each selection
    pax_details = models.JSONField(blank=True, null=True)  # Works with Django 3.1+

    created_at = models.DateTimeField(auto_now_add=True)
    paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def nights_spent(self):
        if self.check_in and self.check_out:
            nights = (self.check_out - self.check_in).days
            return nights if nights > 0 else 1  # Minimum of 1 night for same-day bookings
        return 1

    @property
    def amount_required(self):
        """
        Dynamically calculate total cost:
        - Rooms: price × pax × nights
        - Activities/Packages/Food/Tours: price × pax
        """
        pax = self.pax or 1

        # Use pax_details if available for more accurate pricing
        def get_pax_value(category):
            if self.pax_details and category in self.pax_details:
                return self.pax_details[category].get('pax', pax)
            return pax

        room_cost = sum(
            room.room_type.price_per_night * get_pax_value('rooms') * self.nights_spent
            for room in self.rooms.all()
        )
        activity_cost = sum(
            a.price_per_person * get_pax_value('activities') for a in self.activities.all()
        )
        package_cost = sum(
            p.price_per_person * get_pax_value('packages') for p in self.packages.all()
        )
        food_cost = sum(
            f.price_per_person * get_pax_value('food') for f in self.food.all()
        )
        tour_cost = sum(
            t.price_per_person * get_pax_value('tours') for t in self.tours.all()
        )

        return room_cost + activity_cost + package_cost + food_cost + tour_cost

    @property
    def balance(self):
        return self.amount_required - self.paid

    @property
    def display_customer(self):
        if self.customer_name:
            return self.customer_name
        if self.user:
            return self.user.username
        return "Anonymous"

    def __str__(self):
        return f"Booking #{self.id} - {self.display_customer} - {self.check_in} - {self.amount_required} - {self.pax}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('booking', 'Booking'),
        ('registration', 'Registration'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='booking')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.message} ({'Read' if self.is_read else 'Unread'})"


class SystemSetting(models.Model):
    site_name = models.CharField(max_length=100, default="Epic Trail Adventure Park")
    support_email = models.EmailField(default="support@example.com")
    maintenance_mode = models.BooleanField(default=False)
    enable_mpesa = models.BooleanField(default=True)  # Toggle M-Pesa payments
    enable_stripe = models.BooleanField(default=False)  # Toggle Stripe payments
    max_daily_bookings = models.PositiveIntegerField(default=100)  # Limit per day
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Global discount %

    def __str__(self):
        return "System Settings"
