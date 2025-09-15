
from django.contrib.auth.models import User
from .models import Booking

def total_users(request):
    return {'total_users': User.objects.count()}

def total_bookings(request):
    return {'total_bookings': Booking.objects.count()}

def total_amount(request):
    """
    Returns the total amount payable for the authenticated user's bookings.
    Sums Booking.amount_required for all their bookings.
    """
    total = 0
    if request.user.is_authenticated:
        # Filter bookings for the current user
        bookings = Booking.objects.filter(user=request.user)
        # Sum the dynamic amount_required property
        total = sum(booking.amount_required for booking in bookings)
    return {'total_amount': total}

# all user bookings and their total amount per user all bookings
def total_cost(request):
    """
    Provides all bookings and related totals for the logged-in user.
    Includes activities, packages, rooms, food, tours, and amount calculations.
    """
    if not request.user.is_authenticated:
        return {
            'user_bookings': [],
            'user_total_amount': 0,
        }

    # Fetch all bookings for the logged-in user with related data
    bookings = Booking.objects.filter(user=request.user).prefetch_related(
        'activities', 'packages', 'rooms', 'food', 'tours'
    )

    # Calculate total payable amount for all bookings
    total_amount = sum(b.amount_required for b in bookings)

    return {
        'user_bookings': bookings,
        'user_total_amount': total_amount,
    }
    
