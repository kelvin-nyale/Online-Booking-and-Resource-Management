from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Profile
from .models import Activity, Package, Tour, Food, Room, RoomType, RoomBooking, Booking, Notification, Duty, FoodOrder
from django.utils.dateparse import parse_date
# from django.db.models import Count, Sum
from django.db.models import F, Sum, Count, ExpressionWrapper, DecimalField
import csv, io
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.db.models.functions import ExtractMonth
from datetime import datetime
from django.utils.timezone import now
from django.utils import timezone
import calendar
import requests, base64
from django.conf import settings
from django.core import management
from .models import SystemSetting

# Create your views here.

def index(request):
    return render(request, 'index.html')

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Validate passwords match
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html')

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return render(request, 'register.html')
        
        # Check if email already exists (optional)
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already in use.")
            return render(request, 'register.html')

        # Create user
        user = User.objects.create_user(username=username, email=email, password=password1)
        # Store phone number in first_name temporarily (or use a profile model)
        user.first_name = phone
        user.save()

        # Log in the user
        login(request, user)
        messages.success(request, "Registration successful!")
        return redirect('login')

    return render(request, 'register.html')

# Login with username or email, then redirect based on user role:
    #   - Admin (is_superuser) → admin_dashboard
    #   - Staff (is_staff) → staff_dashboard
    #   - Others → user_dashboard
def login_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=identifier, password=password)

        # Try email if direct username authentication fails
        if user is None:
            try:
                user_obj = User.objects.get(email__iexact=identifier)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user:
            if not user.is_active:
                messages.error(request, "Your account is inactive. Contact admin.")
                return redirect('login')

            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")

            # Role-based redirection
            if user.is_superuser:
                return redirect('admin_dashboard')
            elif user.is_staff:
                return redirect('staff_dashboard')
            else:
                return redirect('user_dashboard')
        else:
            messages.error(request, "Invalid username/email or password.")

    return render(request, 'login.html')


# Optional: Restrict access to admins only
def is_admin(user):
    return user.is_superuser

# Helper to check if user is admin
def admin_required(user):
    return user.is_authenticated and user.is_superuser

def logout_view(request):
    logout(request)  # Ends the user session
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')  # Redirect to the login page

@login_required
@user_passes_test(admin_required)
def admin_dashboard(request):

    # 5 most recent users
    recent_users = User.objects.order_by('-date_joined')[:5]

    return render(
        request,
        'dashboard.admin.html',
        {
            'recent_users': recent_users,
        }
    )

# @login_required
# def staff_dashboard(request):
#     # Count duties/resources assigned to the logged-in staff member
#     assigned_count = Duty.objects.filter(staff=request.user).count()

#     return render(request, "dashboard.staff.html", {
#         "assigned_count": assigned_count,
#     })
@login_required
def staff_dashboard(request):
    # Count only pending duties/resources assigned to this staff member
    assigned_count = Duty.objects.filter(
        staff=request.user, completed=False
    ).count()
    
    # Count bookings where date is in the future or today
    upcoming_bookings_count = Booking.objects.filter(check_in__gte=timezone.now()).count()

    return render(request, "dashboard.staff.html", {
        "assigned_count": assigned_count,
        "upcoming_bookings_count": upcoming_bookings_count,
    })

@login_required
def user_dashboard(request):
    return render(request, 'dashboard.user.html')


@login_required
@user_passes_test(admin_required) 
def add_user(request):
    if request.method == 'POST':
        username = request.POST.get('username').strip()
        email = request.POST.get('email').strip()
        phone = request.POST.get('phone').strip()
        password = request.POST.get('password').strip()
        role = request.POST.get('role')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('add_user')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('add_user')

        user = User.objects.create_user(username=username, email=email, password=password)

        # Assign role
        if role == 'admin':
            user.is_superuser = True
            user.is_staff = True
        elif role == 'staff':
            user.is_staff = True
        # Normal users remain without extra flags
        user.save()
        
        # Create profile for phone
        Profile.objects.create(user=user, phone=phone)

        messages.success(request, f"User '{username}' created successfully as {role}.")
        return redirect('users')

    return render(request, 'user.add.html')

@login_required
@user_passes_test(admin_required)  # Remove this decorator if staff should also access
def view_users(request):
    query = request.GET.get('q', '').strip()

    # Fetch users and apply search
    users_list = User.objects.all().order_by('-date_joined')
    if query:
        users_list = users_list.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )

    # Paginate results (10 per page)
    paginator = Paginator(users_list, 10)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    return render(request, 'users.list.html', {'users': users})

@login_required
@user_passes_test(admin_required) 
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        username = request.POST.get('username').strip()
        email = request.POST.get('email').strip()
        phone = request.POST.get('phone').strip()  # optional: store in a profile model
        role = request.POST.get('role')

        # Check if username/email is unique (excluding current user)
        if User.objects.exclude(id=user_id).filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('edit_user', user_id=user_id)

        if User.objects.exclude(id=user_id).filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('edit_user', user_id=user_id)

        # Update user info
        user.username = username
        user.email = email
        user.phone = phone

        # Reset roles
        user.is_superuser = False
        user.is_staff = False

        # Apply new role
        if role == 'admin':
            user.is_superuser = True
            user.is_staff = True
        elif role == 'staff':
            user.is_staff = True

        user.save()

        messages.success(request, f"User '{username}' updated successfully.")
        return redirect('users')

    return render(request, 'user.edit.html', {'user': user})

@login_required
@user_passes_test(admin_required) 
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"User '{username}' deleted successfully.")
        return redirect('users')

    return render(request, 'user.delete.html', {'user': user})

# Add new activity
@login_required
@user_passes_test(is_admin)
def add_activity(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price_per_person = request.POST.get('price_per_person')

        # Handle image upload if provided
        image = request.FILES.get('image')

        if name and description and price_per_person and image:
            activity = Activity(
                name=name,
                description=description,
                price_per_person=price_per_person,  
                image=image  
            )
            activity.save()  # Save to DB
            messages.success(request, 'Activity added successfully!')
            return redirect('activity_list')
        else:
            messages.error(request, 'All fields are required.')

    return render(request, 'activity.add.html')



# View all activities
# pagination
@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def activity_list(request):
    query = request.GET.get('q', '').strip()

    # Fetch activities and apply search
    activity_list = Activity.objects.all().order_by('-created_at')
    if query:
        activity_list = activity_list.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    # Paginate results (10 per page)
    paginator = Paginator(activity_list, 10)
    page_number = request.GET.get('page')
    activities = paginator.get_page(page_number)

    # Pass both activities and query to the template (for search box persistence)
    return render(
        request,
        'activity.list.html',
        {'activities': activities, 'query': query}
    )



@login_required
@user_passes_test(is_admin)
def edit_activity(request, pk):
    activity = get_object_or_404(Activity, pk=pk)

    if request.method == 'POST':
        activity.name = request.POST.get('name')
        activity.description = request.POST.get('description')
        activity.price_per_person = request.POST.get('price_per_person')

        # Handle new image upload if provided
        if request.FILES.get('image'):
            activity.image = request.FILES['image']

        activity.save()
        messages.success(request, 'Activity updated successfully!')
        return redirect('activity_list')

    return render(request, 'activity_edit.html', {'activity': activity})


# Delete activity
@login_required
@user_passes_test(is_admin) 
def delete_activity(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    if request.method == 'POST':
        activity.delete()
        messages.success(request, "Activity deleted successfully.")
        return redirect('activity_list')

    return render(request, 'activity.delete.html', {'activity': activity})



@login_required
@user_passes_test(admin_required)
def add_package(request):
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        price_per_person = request.POST.get("price_per_person")

        # Safely fetch valid activities
        selected_ids = request.POST.getlist("activities")
        selected_activities = get_list_or_404(Activity, id__in=selected_ids)

        package = Package.objects.create(
            name=name,
            description=description,
            price_per_person=price_per_person
        )
        package.activities.set(selected_activities)  # Link only valid activities
        package.save()

        return redirect("list_packages")

    activities = Activity.objects.all()
    return render(request, "package.add.html", {"activities": activities})


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def list_packages(request):
    query = request.GET.get('q', '').strip()

    # Fetch activities and apply search
    list_packages = Package.objects.all().order_by('-created_at')
    if query:
        list_packages = list_packages.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    # Paginate results (10 per page)
    paginator = Paginator(list_packages, 10)
    page_number = request.GET.get('page')
    packages = paginator.get_page(page_number)

    # Pass both activities and query to the template (for search box persistence)
    return render(
        request,
        'package.list.html',
        {'packages': packages, 'query': query}
    )

# edit package
@login_required
@user_passes_test(is_admin) 
def edit_package(request, pk):
    package = get_object_or_404(Package, pk=pk)

    if request.method == "POST":
        # Basic fields
        package.name = request.POST.get("name")
        package.description = request.POST.get("description")

        # Convert price safely
        price_input = request.POST.get("price_per_person")
        try:
            package.price_per_person = Decimal(price_input)
        except (InvalidOperation, TypeError):
            messages.error(request, "Enter a valid price.")
            return redirect("edit_package", pk=pk)

        # Update activities
        selected_ids = request.POST.getlist("activities")
        activities = Activity.objects.filter(id__in=selected_ids)
        package.activities.set(activities)

        package.save()
        messages.success(request, "Package updated successfully.")
        return redirect("list_packages")

    # Data for the form
    activities = Activity.objects.all()
    selected_activities = package.activities.values_list("id", flat=True)

    return render(
        request,
        "package.update.html",
        {
            "package": package,
            "activities": activities,
            "selected_activities": selected_activities,
        },
    )

@login_required
@user_passes_test(admin_required)
def delete_package(request, pk):
    package = get_object_or_404(Package, pk=pk)
    package.delete()
    messages.success(request, "Package deleted successfully!")
    return redirect('list_packages')

@login_required
@user_passes_test(admin_required)
def add_room_type(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        capacity = request.POST.get('capacity')
        price_per_night = request.POST.get('price_per_night')
        total_rooms = request.POST.get('total_rooms')
        
        RoomType.objects.create(
            name=name,
            description=description,
            capacity=capacity,
            price_per_night=price_per_night,
            total_rooms=total_rooms
        )
        
        messages.success(request, 'Room Type added successfully!')
        return redirect('room_types')
    return render(request, 'room.type.add.html')

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def room_types(request):
    room_types = RoomType.objects.all().order_by('price_per_night')
    return render(request, 'room_type.html', {'room_types': room_types})

@login_required
@user_passes_test(admin_required)
def edit_room_type(request, pk):
    room_type = get_object_or_404(RoomType, pk=pk)

    if request.method == 'POST':
        room_type.name = request.POST.get('name')
        room_type.description = request.POST.get('description')
        room_type.capacity = request.POST.get('capacity')
        price = request.POST.get('price_per_night')
        total_rooms = request.POST.get('total_rooms')

        if not price:
            messages.error(request, "Price per night is required.")
            return render(request, 'room.type.edit.html', {'room_type': room_type})

        try:
            room_type.price_per_night = float(price)
        except ValueError:
            messages.error(request, "Please enter a valid price.")
            return render(request, 'room.type.edit.html', {'room_type': room_type})

        room_type.total_rooms = total_rooms
        room_type.save()
        messages.success(request, "Room type updated successfully!")
        return redirect('room_types')

    return render(request, 'room.type.edit.html', {'room_type': room_type})

@login_required
@user_passes_test(admin_required)
def delete_room_type(request, pk):
    if request.method == 'POST':
        room_type = get_object_or_404(RoomType, pk=pk)
        room_type.delete()
        messages.success(request, "Room type deleted successfully!")
    return redirect('room_types', {'room_type': room_type})

@login_required
@user_passes_test(is_admin) 
def add_room(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        room_type_id = request.POST.get('room_type')
        room_type = get_object_or_404(RoomType, id=room_type_id)

        # Handle image upload if provided
        image = request.FILES.get('image')

        Room.objects.create(
            name=name,
            room_type=room_type,
            image=image  # Save the image
        )

        messages.success(request, "Room added successfully!")
        return redirect('list_rooms')

    # Pass available room types to the template
    room_types = RoomType.objects.all()
    return render(request, 'room_add.html', {'room_types': room_types})

# @login_required
@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def list_rooms(request):
    rooms = Room.objects.select_related('room_type').all() # Fetch rooms with related room types
    return render(request, 'rooms_list.html', {'rooms': rooms})


@login_required
@user_passes_test(is_admin)
def edit_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    room_types = RoomType.objects.all()

    if request.method == 'POST':
        room.name = request.POST.get('name')
        room_type_id = request.POST.get('room_type')
        room.room_type = RoomType.objects.get(id=room_type_id)

        # Handle image upload if provided
        if request.FILES.get('image'):
            room.image = request.FILES['image']

        room.save()
        messages.success(request, f"Room '{room.name}' updated successfully!")
        return redirect('list_rooms')

    return render(request, 'room_edit.html', {'room': room, 'room_types': room_types})

@login_required
@user_passes_test(is_admin)
def delete_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    if request.method == 'POST':
        room.delete()
        messages.success(request, f"Room '{room.name}' deleted successfully!")
        return redirect('list_rooms')

    return render(request, 'room_delete.html', {'room': room})

@login_required
@user_passes_test(is_admin)
def add_tour(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        destination = request.POST.get('destination')
        description = request.POST.get('description')
        price_per_person = request.POST.get('price_per_person')
        # Handle image upload if provided
        image = request.FILES.get('image')
        
        Tour.objects.create(
            name=name,
            destination=destination,
            description=description,
            price_per_person=price_per_person,
            image=image
        )
        messages.success(request, "Room added successfully!")
        return redirect('tours')
    return render(request, 'tour.add.html')

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def tours(request):
    tours = Tour.objects.all()
    return render(request, 'tours.html', {'tours': tours})

@login_required
@user_passes_test(is_admin)
def edit_tour(request, pk):
    tour = get_object_or_404(Tour, pk=pk)
    
    if request.method == 'POST':
        tour.name = request.POST.get('name')
        tour.destination = request.POST.get('destination')
        tour.description = request.POST.get('description')
        tour.price_per_person = request.POST.get('price_per_person')
        
        # Handle image upload if provided
        if request.FILES.get('image'):
            tour.image = request.FILES['image']
        
        tour.save()
        return redirect('tours')
    return render(request, 'tour.edit.html', {'tour': tour})

def delete_tour(request, pk):
    tour = get_object_or_404(Tour, pk=pk)
    if request.method == 'POST':
        tour.delete()
        messages.success(request, "Tour deleted successfully!")
    return redirect('tours')

@login_required
@user_passes_test(admin_required)
def add_food(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        price_per_person = request.POST.get('price_per_person')

        Food.objects.create(
            name=name,
            price_per_person=price_per_person
        )
        messages.success(request, "Food item added successfully!")
        return redirect('food_list')
    return render(request, 'food.add.html')

@login_required
@user_passes_test(admin_required)
def food_list(request):
    foods = Food.objects.all()
    return render(request, 'food.list.html', {'foods': foods})

@login_required
@user_passes_test(admin_required)
def edit_food(request, pk):
    food = get_object_or_404(Food, pk=pk)

    if request.method == 'POST':
        food.name = request.POST.get('name')
        food.price_per_person = request.POST.get('price_per_person')
        food.save()
        messages.success(request, "Food item updated successfully!")
        return redirect('food_list')

    return render(request, 'food.edit.html', {'food': food})

@login_required
@user_passes_test(admin_required)
def delete_food(request, pk):
    food = get_object_or_404(Food, pk=pk)
    if request.method == 'POST':
        food.delete()
        messages.success(request, "Food item deleted successfully!")
    return redirect('food_list')

def book_room(request, pk):
    room = get_object_or_404(RoomType, pk=pk)
    if request.method == 'POST':
        check_in = parse_date(request.POST['check_in'])
        check_out = parse_date(request.POST['check_out'])

        # Count existing overlapping bookings
        overlapping = RoomBooking.objects.filter(
            room_type=room,
            check_in__lt=check_out,
            check_out__gt=check_in
        ).count()

        if overlapping >= room.total_rooms:
            messages.error(request, "Sorry, no available rooms for the selected dates.")
            return redirect('list_rooms')

        RoomBooking.objects.create(
            room_type=room,
            customer_name=request.POST['customer_name'],
            customer_email=request.POST['customer_email'],
            check_in=check_in,
            check_out=check_out,
            guests=request.POST['guests'],
        )
        messages.success(request, "Room booked successfully!")
        return redirect('list_rooms')
    return render(request, 'room_book.html', {'room': room})


def create_booking(request):
    """
    Create a booking dynamically:
    - Validate dates (allow same-day check-in/check-out)
    - Validate room availability
    - Store exact pax values for activities, packages, rooms, food, tours
    - Role-based: Admin/Staff can select everything; normal users limited to Rooms & Packages
    - Render correct base template depending on user role
    """
    if request.method == "POST":
        # --- Handle customer details ---
        customer_name = request.user.username if request.user.is_authenticated else request.POST.get("customer_name")
        customer_email = request.user.email if request.user.is_authenticated else request.POST.get("customer_email")

        check_in = request.POST.get("check_in")
        check_out = request.POST.get("check_out")
        pax = int(request.POST.get("pax", 1))

        selected_room_ids = request.POST.getlist("rooms")
        selected_package_ids = request.POST.getlist("packages")
        selected_activity_ids = request.POST.getlist("activities")
        selected_food_ids = request.POST.getlist("food")
        selected_tour_ids = request.POST.getlist("tours")

        # --- Validate dates ---
        if not check_in or not check_out:
            messages.error(request, "Please select both check-in and check-out dates.")
            return redirect("create_booking")

        if check_out < check_in:  # allow same-day but not before
            messages.error(request, "Check-out date cannot be before check-in.")
            return redirect("create_booking")

        # --- Validate room availability ---
        for room_id in selected_room_ids:
            room = get_object_or_404(Room, id=room_id)
            overlapping = Booking.objects.filter(
                rooms=room,
                check_in__lt=check_out,
                check_out__gt=check_in
            ).count()
            if overlapping >= room.room_type.total_rooms:
                messages.error(request, f"Room '{room.name}' is fully booked for the selected dates.")
                return redirect("create_booking")

        # --- Role-based restrictions ---
        if not (request.user.is_staff or request.user.is_superuser):
            selected_activity_ids = []
            selected_food_ids = []
            selected_tour_ids = []

        # --- Collect per-item pax values ---
        pax_details = {}

        activities_pax = int(request.POST.get("activities_pax", 1))
        if selected_activity_ids:
            pax_details['activities'] = {'ids': selected_activity_ids, 'pax': activities_pax}

        packages_pax = int(request.POST.get("packages_pax", 1))
        if selected_package_ids:
            pax_details['packages'] = {'ids': selected_package_ids, 'pax': packages_pax}

        rooms_pax = int(request.POST.get("rooms_pax", 1))
        if selected_room_ids:
            pax_details['rooms'] = {'ids': selected_room_ids, 'pax': rooms_pax}

        food_pax = int(request.POST.get("food_pax", 1))
        if selected_food_ids:
            pax_details['food'] = {'ids': selected_food_ids, 'pax': food_pax}

        tours_pax = int(request.POST.get("tours_pax", 1))
        if selected_tour_ids:
            pax_details['tours'] = {'ids': selected_tour_ids, 'pax': tours_pax}

        # --- Create booking ---
        booking = Booking.objects.create(
            user=request.user if request.user.is_authenticated else None,
            customer_name=customer_name,
            customer_email=customer_email,
            check_in=check_in,
            check_out=check_out,
            pax=pax,
            pax_details=pax_details
        )

        booking.activities.set(selected_activity_ids)
        booking.packages.set(selected_package_ids)
        booking.rooms.set(selected_room_ids)
        booking.food.set(selected_food_ids)
        booking.tours.set(selected_tour_ids)

        messages.success(request, "Booking created successfully!")
        return redirect("booking_list")

    # --- Choose base template based on role ---
    base_template = (
        "base.admin.html" if request.user.is_authenticated and request.user.is_superuser
        else "base.staff.html" if request.user.is_authenticated and request.user.is_staff
        else "base.user.html" if request.user.is_authenticated
        else "base.html"
    )

    # --- Context for form rendering ---
    context = {
        "base_template": base_template,
        "activities": Activity.objects.all(),
        "packages": Package.objects.all(),
        "rooms": Room.objects.all(),
        "food": Food.objects.all(),
        "tours": Tour.objects.all(),
    }
    return render(request, "booking_create.html", context)

@login_required
def booking_list(request):
    bookings = (
        Booking.objects
        .select_related('user')
        .prefetch_related('activities', 'packages', 'rooms', 'food', 'tours')
        .order_by('-created_at')
    )

    if request.user.is_superuser:
        editable_ids = bookings.values_list('id', flat=True)
        base_template = 'base.admin.html'
        template_name = 'bookings.html'  # Table for superusers
    elif request.user.is_staff:
        editable_ids = bookings.filter(user=request.user).values_list('id', flat=True)
        base_template = 'base.staff.html'
        template_name = 'bookings.html'  # Table for staff
    else:
        bookings = bookings.filter(user=request.user)
        editable_ids = bookings.values_list('id', flat=True)
        base_template = 'base.user.html'
        template_name = 'bookings.user.html'  # Cards for normal users

    return render(request, template_name, {
        'bookings': bookings,
        'editable_ids': set(editable_ids),
        'base_template': base_template,
    })


# Edit booking with validations
@login_required(login_url='login')
def edit_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk)

    # Restrict: Only superusers or the booking owner can edit
    if not request.user.is_superuser and booking.user != request.user:
        messages.error(request, "You do not have permission to edit this booking.")
        return redirect('booking_list')

    if request.method == "POST":
        check_in = request.POST.get("check_in")
        check_out = request.POST.get("check_out")
        guests = int(request.POST.get("guests", 1))
        selected_room_ids = request.POST.getlist("rooms")

        # Validate dates
        if check_in > check_out:
            messages.error(request, "Check-out date must be after check-in.")
            return redirect("edit_booking", pk=booking.pk)

        # Validate room availability
        for room_id in selected_room_ids:
            room = get_object_or_404(Room, id=room_id)
            overlapping = Booking.objects.filter(
                rooms=room,
                check_in__lt=check_out,
                check_out__gt=check_in
            ).exclude(id=booking.id).count()

            if overlapping >= room.room_type.total_rooms:
                messages.error(
                    request,
                    f"Room '{room.name}' is fully booked for the selected dates."
                )
                return redirect("edit_booking", pk=booking.pk)

        # Update booking details
        booking.check_in = check_in
        booking.check_out = check_out
        booking.guests = guests
        booking.activities.set(request.POST.getlist("activities"))
        booking.packages.set(request.POST.getlist("packages"))
        booking.rooms.set(selected_room_ids)
        booking.food.set(request.POST.getlist("food"))
        booking.tours.set(request.POST.getlist("tours"))
        booking.save()

        messages.success(request, "Booking updated successfully!")
        return redirect("booking_list")

    # Role-based base template selection
    if request.user.is_superuser:
        base_template = "base.admin.html"
    elif request.user.groups.filter(name="Staff").exists():
        base_template = "base.staff.html"
    else:
        base_template = "base.user.html"

    # Pass all required data
    context = {
        "booking": booking,
        "activities": Activity.objects.all(),
        "packages": Package.objects.all(),
        "rooms": Room.objects.all(),
        "food": Food.objects.all(),
        "tours": Tour.objects.all(),
        "base_template": base_template,  # 🔑 Fix: Add base_template
    }
    return render(request, "booking_edit.html", context)


@login_required(login_url='login')
def delete_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk)

    # Restrict: Only superusers or the booking owner can delete
    if not request.user.is_superuser and booking.user != request.user:
        messages.error(request, "You do not have permission to delete this booking.")
        return redirect('booking_list')

    booking.delete()
    messages.success(request, "Booking deleted successfully!")
    return redirect('booking_list')

@login_required
@user_passes_test(admin_required)
def notifications_view(request):
    if request.user.is_staff:
        notifications = Notification.objects.all().order_by('-created_at')
    else:
        notifications = request.user.notifications.all().order_by('-created_at')

    # Filtering
    notif_type = request.GET.get('type')
    unread = request.GET.get('unread')
    if notif_type:
        notifications = notifications.filter(type=notif_type)
    if unread:
        notifications = notifications.filter(is_read=False)

    return render(request, 'notifications.html', {'notifications': notifications})

@login_required
@user_passes_test(admin_required)
def mark_notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk)
    if notif.user == request.user or request.user.is_staff:
        notif.is_read = True
        notif.save()
    return redirect('notifications')

def explore(request):
    activities = Activity.objects.all()
    rooms = Room.objects.all()
    tours = Tour.objects.all()

    # Decide base template based on user authentication
    base_template = 'base.user.html' if request.user.is_authenticated else 'base.html'

    return render(request, 'explore.html', {
        'activities': activities,
        'rooms': rooms,
        'tours': tours,
        'base_template': base_template,
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)  # Only admin
def reports_analytics(request):
    from .models import Booking, Activity, Package, Room, Tour, FoodOrder

    # --- Bookings ---
    bookings = Booking.objects.all()
    total_bookings = bookings.count()
    total_revenue = sum(b.amount_required for b in bookings)

    # --- Food Orders ---
    orders = FoodOrder.objects.all()
    total_orders = orders.count()

    # Calculate revenue: food price * quantity
    orders_with_total = orders.annotate(
        order_total=ExpressionWrapper(
            F("food__price_per_person") * F("quantity"),
            output_field=DecimalField()
        )
    )
    total_order_revenue = orders_with_total.aggregate(total=Sum("order_total"))["total"] or 0

    # --- Revenue by category (bookings) ---
    revenue_activities = sum(
        sum(a.price_per_person * b.pax for a in b.activities.all()) for b in bookings
    )
    revenue_packages = sum(
        sum(p.price_per_person * b.pax for p in b.packages.all()) for b in bookings
    )
    revenue_rooms = sum(
        sum(r.room_type.price_per_night * b.pax * b.nights_spent for r in b.rooms.all()) for b in bookings
    )
    revenue_tours = sum(
        sum(t.price_per_person * b.pax for t in b.tours.all()) for b in bookings
    )

    # --- Monthly performance (bookings only) ---
    monthly_data = (
        bookings.annotate(month=ExtractMonth('created_at'))
        .values('month')
        .annotate(total=Count('id'), revenue=Sum('paid'))
    )

    months = [calendar.month_abbr[i] for i in range(1, 13)]
    monthly_bookings = [0] * 12
    monthly_revenue = [0] * 12
    for entry in monthly_data:
        idx = entry['month'] - 1
        monthly_bookings[idx] = entry['total']
        monthly_revenue[idx] = float(entry['revenue'] or 0)

    # --- Pie chart (bookings + food orders) ---
    pie_labels = ["Activities", "Packages", "Rooms", "Tours", "Food Orders"]
    pie_data = [revenue_activities, revenue_packages, revenue_rooms, revenue_tours, total_order_revenue]

    # --- Top booked items ---
    popular_activities = Activity.objects.annotate(num_bookings=Count('booking')).order_by('-num_bookings')[:5]
    popular_packages = Package.objects.annotate(num_bookings=Count('booking')).order_by('-num_bookings')[:5]
    popular_rooms = Room.objects.annotate(num_bookings=Count('booking')).order_by('-num_bookings')[:5]
    popular_tours = Tour.objects.annotate(num_bookings=Count('booking')).order_by('-num_bookings')[:5]

    # ---------------- CSV Export ----------------
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="EpicTrail-Report_{datetime.now().strftime("%Y%m%d")}.csv"'
        writer = csv.writer(response)

        # --- Bookings Report ---
        writer.writerow(["--- BOOKINGS REPORT ---"])
        writer.writerow(["Customer", "Booking Date", "Guests", "Revenue (KSh)"])
        bookings_total = 0
        for b in bookings:
            customer = getattr(b, "display_customer", str(b.customer_name))
            booking_date = b.created_at.strftime('%Y-%m-%d')
            revenue = round(b.amount_required, 2)
            bookings_total += revenue
            writer.writerow([customer, booking_date, b.pax, revenue])

        writer.writerow(["", "", "Total Bookings Revenue", bookings_total])
        writer.writerow([])

        # --- Food Orders Report ---
        writer.writerow(["--- FOOD ORDERS REPORT ---"])
        writer.writerow(["Customer", "Order Date", "Food Item", "Quantity", "Revenue (KSh)"])
        food_total = 0
        for o in orders_with_total:
            customer = str(o.user) if o.user else "Guest"
            order_date = o.created_at.strftime('%Y-%m-%d')
            food_name = o.food.name
            revenue = round(o.order_total, 2)
            food_total += revenue
            writer.writerow([customer, order_date, food_name, o.quantity, revenue])

        writer.writerow(["", "", "", "Total Food Revenue", food_total])

        return response

    # ---------------- PDF Export ----------------
    if request.GET.get("export") == "pdf":
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="EpicTrail-Report_{datetime.now().strftime("%Y%m%d")}.pdf"'

        p = canvas.Canvas(response, pagesize=A4)
        width, height = A4

        # Title
        p.setFont("Helvetica-Bold", 18)
        p.drawString(50, height - 50, "EpicTrail Adventures - Analytics Report")
        p.setFont("Helvetica", 10)
        p.drawString(50, height - 70, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # --- Bookings Section ---
        y = height - 110
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y, "Bookings Report")
        y -= 30
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Customer")
        p.drawString(200, y, "Booking Date")
        p.drawString(350, y, "Revenue (KSh)")
        p.setFont("Helvetica", 10)

        bookings_total = 0
        for b in bookings:
            y -= 20
            if y < 80:
                p.showPage()
                y = height - 50
            customer = getattr(b, "display_customer", str(b.customer_name))
            booking_date = b.created_at.strftime('%Y-%m-%d')
            revenue = round(b.amount_required, 2)
            bookings_total += revenue
            p.drawString(50, y, customer)
            p.drawString(200, y, booking_date)
            p.drawString(350, y, f"KSh {revenue:,.2f}")

        y -= 30
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, f"Total Bookings Revenue: KSh {bookings_total:,.2f}")

        # --- Food Orders Section ---
        y -= 60
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y, "Food Orders Report")
        y -= 30
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Customer")
        p.drawString(200, y, "Order Date")
        p.drawString(300, y, "Food Item")
        p.drawString(450, y, "Revenue (KSh)")
        p.setFont("Helvetica", 10)

        food_total = 0
        for o in orders_with_total:
            y -= 20
            if y < 80:
                p.showPage()
                y = height - 50
            customer = str(o.user) if o.user else "Guest"
            order_date = o.created_at.strftime('%Y-%m-%d')
            food_name = o.food.name
            revenue = round(o.order_total, 2)
            food_total += revenue
            p.drawString(50, y, customer)
            p.drawString(200, y, order_date)
            p.drawString(300, y, food_name)
            p.drawString(450, y, f"KSh {revenue:,.2f}")

        y -= 30
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, f"Total Food Revenue: KSh {food_total:,.2f}")

        p.showPage()
        p.save()
        return response

    # ---------------- Web Render ----------------
    return render(request, "reports_analytics.html", {
        "bookings": bookings,
        "total_bookings": total_bookings,
        "total_revenue": total_revenue,
        "revenue_activities": revenue_activities,
        "revenue_packages": revenue_packages,
        "revenue_rooms": revenue_rooms,
        "revenue_tours": revenue_tours,
        "total_orders": total_orders,
        "total_order_revenue": total_order_revenue,
        "months": months,
        "monthly_bookings": monthly_bookings,
        "monthly_revenue": monthly_revenue,
        "pie_labels": pie_labels,
        "pie_data": pie_data,
        "popular_activities": popular_activities,
        "popular_packages": popular_packages,
        "popular_rooms": popular_rooms,
        "popular_tours": popular_tours,
    })
# def reports_analytics(request):
#     from .models import Booking, Activity, Package, Room, Tour #, FoodOrder

#     bookings = Booking.objects.all()
#     total_bookings = bookings.count()
#     total_revenue = sum(b.amount_required for b in bookings)
    
#     # orders = FoodOrder.objects.all()
#     # total_orders = orders.count()
#     # total_order_revenue = sum(o.total_price for o in orders)

#     # Revenue by category
#     revenue_activities = sum(
#         sum(a.price_per_person * b.pax for a in b.activities.all()) for b in bookings
#     )
#     revenue_packages = sum(
#         sum(p.price_per_person * b.pax for p in b.packages.all()) for b in bookings
#     )
#     revenue_rooms = sum(
#         sum(r.room_type.price_per_night * b.pax * b.nights_spent for r in b.rooms.all()) for b in bookings
#     )
#     revenue_tours = sum(
#         sum(t.price_per_person * b.pax for t in b.tours.all()) for b in bookings
#     )
#     # revenue_orders = sum(o.total_price for o in orders.all())

#     # --- Monthly performance ---
#     # Aggregate bookings by month
#     monthly_data = (
#         bookings.annotate(month=ExtractMonth('created_at'))
#         .values('month')
#         .annotate(total=Count('id'), revenue=Sum('paid'))
#     )
    
#     # Prepare arrays for all 12 months
#     months = [calendar.month_abbr[i] for i in range(1, 13)]
#     monthly_bookings = [0] * 12
#     monthly_revenue = [0] * 12
#     for entry in monthly_data:
#         idx = entry['month'] - 1
#         monthly_bookings[idx] = entry['total']
#         monthly_revenue[idx] = float(entry['revenue'] or 0)

#     # Pie chart data
#     pie_labels = ["Activities", "Packages", "Rooms", "Tours"]
#     pie_data = [revenue_activities, revenue_packages, revenue_rooms, revenue_tours]

#     # Top items
#     popular_activities = Activity.objects.annotate(num_bookings=Count('booking')).order_by('-num_bookings')[:5]
#     popular_packages = Package.objects.annotate(num_bookings=Count('booking')).order_by('-num_bookings')[:5]
#     popular_rooms = Room.objects.annotate(num_bookings=Count('booking')).order_by('-num_bookings')[:5]
#     popular_tours = Tour.objects.annotate(num_bookings=Count('booking')).order_by('-num_bookings')[:5]
    
#     if request.GET.get("export") == "csv":

#         bookings = Booking.objects.all()

#         # Create HTTP response for CSV
#         response = HttpResponse(content_type="text/csv")
#         response["Content-Disposition"] = f'attachment; filename="EpicTrail-Adventures-Booking-Report_{datetime.now().strftime("%Y%m%d")}.csv"'

#         writer = csv.writer(response)
#         # Header row
#         writer.writerow(["Customer", "Booking Date", "Guests", "Revenue (KSh)"])

#         total_revenue = 0
#         for b in bookings:
#             customer = b.display_customer if hasattr(b, "display_customer") else str(b.customer_name)
#             booking_date = b.created_at.strftime('%Y-%m-%d')
#             revenue = round(b.amount_required, 2)
#             total_revenue += revenue
#             writer.writerow([customer, booking_date, b.pax, revenue])

#         # Summary row for total revenue
#         writer.writerow([])
#         writer.writerow(["", "", "Total Revenue", total_revenue])

#         return response

    
#     if request.GET.get("export") == "pdf":

#         bookings = Booking.objects.all()

#         # Create response for PDF download
#         response = HttpResponse(content_type="application/pdf")
#         response["Content-Disposition"] = f'attachment; filename="EpicTrail-Adventures-Booking-Report_{datetime.now().strftime("%Y%m%d")}.pdf"'

#         # Create PDF canvas
#         p = canvas.Canvas(response, pagesize=A4)
#         width, height = A4

#         # Title and date
#         p.setFont("Helvetica-Bold", 18)
#         p.drawString(50, height - 50, "EpicTrail Adventures - Booking Report")
#         p.setFont("Helvetica", 10)
#         p.drawString(50, height - 70, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

#         # Table header
#         p.setFont("Helvetica-Bold", 12)
#         y = height - 110
#         p.drawString(50, y, "Customer")
#         p.drawString(200, y, "Booking Date")
#         p.drawString(350, y, "Revenue (KSh)")

#         # Table content
#         p.setFont("Helvetica", 10)
#         total_revenue = 0
#         for b in bookings:
#             y -= 20
#             if y < 50:  # Add a new page if space runs out
#                 p.showPage()
#                 y = height - 50
#                 p.setFont("Helvetica-Bold", 12)
#                 p.drawString(50, y, "Customer")
#                 p.drawString(200, y, "Booking Date")
#                 p.drawString(350, y, "Revenue (KSh)")
#                 p.setFont("Helvetica", 10)
#                 y -= 30

#             customer = b.display_customer if hasattr(b, "display_customer") else str(b.customer)
#             booking_date = b.created_at.strftime('%Y-%m-%d')
#             revenue = round(b.amount_required, 2)
#             total_revenue += revenue

#             p.drawString(50, y, customer)
#             p.drawString(200, y, booking_date)
#             p.drawString(350, y, f"KSh {revenue:,.2f}")

#         # Total revenue summary
#         y -= 40
#         p.setFont("Helvetica-Bold", 12)
#         p.drawString(50, y, f"Total Revenue: KSh {total_revenue:,.2f}")

#         # Finalize and return
#         p.showPage()
#         p.save()
#         return response


#     return render(request, "reports_analytics.html", {
#         "bookings": bookings,
#         "total_bookings": total_bookings,
#         "total_revenue": total_revenue,
#         "revenue_activities": revenue_activities,
#         "revenue_packages": revenue_packages,
#         "revenue_rooms": revenue_rooms,
#         "revenue_tours": revenue_tours,
#         # "revenue_orders": revenue_orders,
#         # "total_orders": total_orders,
#         # "total_order_revenue": total_order_revenue,
#         "months": months,
#         "monthly_bookings": monthly_bookings,
#         "monthly_revenue": monthly_revenue,
#         "pie_labels": pie_labels,
#         "pie_data": pie_data,
#         "popular_activities": popular_activities,
#         "popular_packages": popular_packages,
#         "popular_rooms": popular_rooms,
#         "popular_tours": popular_tours,
#     })

# --- USERS ---

@login_required
def place_order(request):
    foods = Food.objects.all()

    if request.method == "POST":
        food_id = request.POST.get("food")
        quantity = int(request.POST.get("quantity"))
        check_in = request.POST.get("check_in")

        food = get_object_or_404(Food, id=food_id)

        FoodOrder.objects.create(
            user=request.user,
            food=food,
            quantity=quantity,
            check_in=check_in,
            status="Pending"
        )
        return redirect("my_orders")  # user is redirected to their orders list

    return render(request, "place_order.html", {"foods": foods})

@login_required
def food_menu(request):
    foods = Food.objects.all()
    return render(request, 'food_menu.html', {'foods': foods})

@login_required
def my_orders(request):
    orders = FoodOrder.objects.filter(user=request.user)
    return render(request, 'my_orders.html', {'orders': orders})


@login_required
def update_order(request, order_id):
    order = get_object_or_404(FoodOrder, id=order_id, user=request.user, status='pending')
    if request.method == 'POST':
        order.quantity = int(request.POST.get('quantity', order.quantity))
        order.save()
        messages.info(request, "Order updated.")
        return redirect('my_orders')
    return render(request, 'update_order.html', {'order': order})

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(FoodOrder, id=order_id, user=request.user, status='pending')
    order.status = 'cancelled'
    order.save()
    messages.warning(request, "Order cancelled.")
    return redirect('my_orders')

@login_required
@user_passes_test(is_admin)
def manage_orders(request):
    orders = FoodOrder.objects.all().order_by('-created_at')

    if request.method == "POST":
        order_id = request.POST.get("order_id")
        action = request.POST.get("action")
        order = get_object_or_404(FoodOrder, id=order_id)

        if action == "approve":
            order.status = "Approved"
        elif action == "cancel":
            order.status = "Cancelled"
        elif action == "completed":
            order.status = "Completed"
        order.save()
        return redirect("manage_orders")

    return render(request, "manage_orders.html", {"orders": orders})


from django.views.decorators.http import require_POST

@login_required
@user_passes_test(is_admin)
@require_POST
def update_order_status(request, order_id):
    order = get_object_or_404(FoodOrder, id=order_id)
    new_status = request.POST.get('status')
    if new_status in dict(FoodOrder.STATUS_CHOICES).keys():
        order.status = new_status
        order.save()
        messages.success(request, f"Order #{order.id} updated to {new_status.capitalize()}.")
    else:
        messages.error(request, "Invalid status.")
    return redirect('manage_orders')

def initiate_stk_push(phone, amount, account_reference="EpicTrail Adventures", transaction_desc="Booking Payment"):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(
        f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode('utf-8')
    ).decode('utf-8')

    # Get OAuth token
    token_url = f"https://{settings.MPESA_ENVIRONMENT}.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(token_url, auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET))
    access_token = response.json()['access_token']

    # STK Push URL
    stk_url = f"https://{settings.MPESA_ENVIRONMENT}.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": settings.CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_desc,
    }

    res = requests.post(stk_url, json=payload, headers=headers)
    return res.json()

@login_required
@user_passes_test(admin_required)
def backup_data(request):
    """
    Creates a downloadable JSON backup of the database.
    """
    # Create an in-memory file
    buffer = io.StringIO()

    # Dump all data into the buffer
    management.call_command('dumpdata', format='json', indent=2, stdout=buffer)

    # Prepare HTTP response
    filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    response = HttpResponse(buffer.getvalue(), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@login_required
@user_passes_test(admin_required)
def system_settings(request):
    settings = SystemSetting.objects.first()
    if not settings:
        settings = SystemSetting.objects.create()

    if request.method == "POST":
        settings.site_name = request.POST.get("site_name")
        settings.support_email = request.POST.get("support_email")
        settings.maintenance_mode = "maintenance_mode" in request.POST
        settings.enable_mpesa = "enable_mpesa" in request.POST
        settings.enable_stripe = "enable_stripe" in request.POST
        settings.max_daily_bookings = int(request.POST.get("max_daily_bookings", 100))
        settings.discount_rate = request.POST.get("discount_rate", 0)
        settings.save()
        return redirect("admin_dashboard")

    return render(request, "system_settings.html", {"settings": settings})

# view for booking on behalf of another user
@login_required
@user_passes_test(admin_required)
def admin_create_booking(request):
    users = User.objects.all().order_by('username')
    activities = Activity.objects.all()
    packages = Package.objects.all()
    rooms = Room.objects.all()
    # food_items = Food.objects.all()
    tours = Tour.objects.all()

    if request.method == "POST":
        selected_user_id = request.POST.get('user')
        check_in = request.POST.get('check_in')
        check_out = request.POST.get('check_out')
        pax = request.POST.get('pax', 1)

        # Create the booking linked to a user
        booking = Booking.objects.create(
            user=User.objects.get(id=selected_user_id) if selected_user_id else None,
            check_in=check_in,
            check_out=check_out,
            pax=pax,
        )

        # Set ManyToMany relationships
        booking.activities.set(request.POST.getlist('activities'))
        booking.packages.set(request.POST.getlist('packages'))
        booking.rooms.set(request.POST.getlist('rooms'))
        # booking.food.set(request.POST.getlist('food'))
        booking.tours.set(request.POST.getlist('tours'))

        messages.success(request, "Booking created successfully on behalf of user.")
        return redirect('booking_list')

    return render(request, 'booking.create_for_user.html', {
        'users': users,
        'activities': activities,
        'packages': packages,
        'rooms': rooms,
        # 'food_items': food_items,
        'tours': tours,
    })

@login_required
def upcoming_bookings_list(request):
    upcoming_bookings = Booking.objects.filter(
        check_in__gte=timezone.now()
    ).order_by('check_in')
    return render(request, "bookings.upcoming.html", {
        "upcoming_bookings": upcoming_bookings
    })


@login_required
@user_passes_test(admin_required)
def assign_duty(request):
    staff_members = User.objects.filter(is_staff=True)
    if request.method == 'POST':
        staff_id = request.POST.get('staff')
        title = request.POST.get('title')
        description = request.POST.get('description')
        due_date = request.POST.get('due_date')

        Duty.objects.create(
            staff=User.objects.get(id=staff_id),
            title=title,
            description=description,
            due_date=due_date
        )
        messages.success(request, "Duty assigned successfully.")
        return redirect('duties')

    duties = Duty.objects.all().order_by('-assigned_on')
    return render(request, 'duty.assign.html', {
        'staff_members': staff_members,
        'duties': duties
    })

@login_required
@user_passes_test(admin_required)
def duties(request):
    duties = Duty.objects.all()
    return render(request, 'duties.html', {'duties': duties})

@login_required
def update_duty_status(request, duty_id):
    duty = get_object_or_404(Duty, id=duty_id)

    # Only the staff assigned to this duty OR an admin can update
    if request.user != duty.staff and not request.user.is_superuser:
        return HttpResponseForbidden("You are not allowed to update this duty.")

    if request.method == 'POST':
        duty.completed = not duty.completed  # Toggle status
        duty.save()
        messages.success(request, f"Duty '{duty.title}' marked as {'Completed' if duty.completed else 'Pending'}.")
        return redirect('assign_duty')

    return render(request, 'duty.update.html', {'duty': duty})

@login_required
def staff_duties(request):
    """
    Show all duties assigned to the logged-in staff member.
    Allows staff to mark duties as completed or pending.
    """
    duties = Duty.objects.filter(staff=request.user).order_by('due_date')

    if request.method == "POST":
        duty_id = request.POST.get("duty_id")
        duty = get_object_or_404(Duty, id=duty_id, staff=request.user)
        duty.completed = not duty.completed  # Toggle status
        duty.save()
        messages.success(request, f"Duty '{duty.title}' marked as {'Completed' if duty.completed else 'Pending'}.")
        return redirect('staff_duties')

    return render(request, "duties.staff.html", {"duties": duties})