from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Profile
from .models import Activity, Package, Room, Tour, Food, Booking, RoomType, RoomBooking
from django.utils.dateparse import parse_date

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

def logout_view(request):
    logout(request)  # Ends the user session
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')  # Redirect to the login page

@login_required
def admin_dashboard(request):
    return render(request, 'dashboard.admin.html')

@login_required
def staff_dashboard(request):   
    return render(request, 'dashboard.staff.html')

@login_required
def user_dashboard(request):
    return render(request, 'dashboard.user.html')

# Optional: Restrict access to admins only
def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin) 
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
@user_passes_test(is_admin)  # Remove this decorator if staff should also access
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
@user_passes_test(is_admin) 
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
@user_passes_test(is_admin) 
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"User '{username}' deleted successfully.")
        return redirect('users')

    return render(request, 'user.delete.html', {'user': user})

# Add new activity
# def add_activity(request):
#     if request.method == 'POST':
#         name = request.POST.get('name')
#         description = request.POST.get('description')
#         price_per_person = request.POST.get('price_per_person')
#         created_at = request.POST.get('created_at')

#         if not name or not price_per_person:
#             messages.error(request, "Name and Price are required.")
#             return redirect('add_activity')

#         Activity.objects.create(name=name, description=description, price_per_person=price_per_person, created_at=created_at)
#         messages.success(request, "Activity added successfully.")
#         return redirect('activity_list')

#     return render(request, 'activity.add.html')
@login_required
@user_passes_test(is_admin) 
def add_activity(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price_per_person = request.POST.get('price_per_person')

        if name and description and price_per_person:
            activity = Activity(
                name=name,
                description=description,
                price_per_person=price_per_person
            )
            activity.save()  # Save to DB
            messages.success(request, 'Activity added successfully!')
            return redirect('activity_list')
        else:
            messages.error(request, 'All fields are required.')

    return render(request, 'activity.add.html')


# View all activities

# def activity_list(request):
#     query = request.GET.get('q', '').strip()

#     # Fetch activities and apply search
#     activity_list = Activity.objects.all().order_by('-created_at')
#     if query:
#         activity_list = activity_list.filter(
#             Q(name__icontains=query) |
#             Q(description__icontains=query)
#         )

#     # Paginate results (10 per page)
#     paginator = Paginator(activity_list, 10)
#     page_number = request.GET.get('page')
#     activities = paginator.get_page(page_number)
#     activities = Activity.objects.all()
#     return render(request, 'activity.list.html', {'activities': activities})
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

# Edit activity
@login_required
@user_passes_test(is_admin) 
def edit_activity(request, pk):
    activity = get_object_or_404(Activity, pk=pk)

    if request.method == 'POST':
        activity.name = request.POST.get('name')
        activity.description = request.POST.get('description')
        activity.price_per_person = request.POST.get('price_per_person')

        if not activity.name or not activity.price_per_person:
            messages.error(request, "Name and Price are required.")
            return redirect('edit_activity', pk=pk)

        activity.save()
        messages.success(request, "Activity updated successfully.")
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

# Helper to check if user is admin
def admin_required(user):
    return user.is_authenticated and user.is_superuser

# @login_required
# @user_passes_test(admin_required)
# def add_package(request):
#     activities = Activity.objects.all()
#     if request.method == 'POST':
#         name = request.POST.get('name')
#         description = request.POST.get('description')
#         price_per_person = request.POST.get('price_per_person')
#         activity_ids = request.POST.getlist('activities')
#         package = Package.objects.create(name=name, description=description, price_per_person=price_per_person)
#         package.activities.set(activity_ids)
#         messages.success(request, "Package added successfully!")
#         return redirect('list_packages')
#     return render(request, 'package.add.html', {'activities': activities})

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
@user_passes_test(admin_required)
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

# @login_required
# @user_passes_test(admin_required)
# def edit_package(request, pk):
#     package = get_object_or_404(Package, pk=pk)
#     activities = Activity.objects.all()
#     if request.method == 'POST':
#         package.name = request.POST.get('name')
#         package.description = request.POST.get('description')
#         package.price_per_person = request.POST.get('price_per_person')
#         activity_ids = request.POST.getlist('activities')
#         package.activities.set(activity_ids)
#         package.save()
#         messages.success(request, "Package updated successfully!")
#         return redirect('list_packages')
#     return render(request, 'package.update.html', {'package': package, 'activities': activities})
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
@user_passes_test(is_admin) 
def add_room(request):
    if request.method == 'POST':
        RoomType.objects.create(
            name=request.POST['name'],
            description=request.POST['description'],
            capacity=request.POST['capacity'],
            price_per_night=request.POST['price_per_night'],
            available=bool(request.POST.get('available'))
        )
        messages.success(request, "Room added successfully!")
        return redirect('list_rooms')
    return render(request, 'room_add.html')

def list_rooms(request):
    rooms = RoomType.objects.all().order_by('price_per_night')
    return render(request, 'rooms_list.html', {'rooms': rooms})

@login_required
@user_passes_test(is_admin) 
def edit_room(request, pk):
    room = get_object_or_404(RoomType, pk=pk)
    if request.method == 'POST':
        room.name = request.POST['name']
        room.description = request.POST['description']
        room.capacity = request.POST['capacity']
        room.price_per_night = request.POST['price_per_night']
        room.available = bool(request.POST.get('available'))
        room.save()
        messages.success(request, "Room updated successfully!")
        return redirect('list_rooms')
    return render(request, 'room_edit.html', {'room': room})

@login_required
@user_passes_test(is_admin) 
def delete_room(request, pk):
    room = get_object_or_404(RoomType, pk=pk)
    room.delete()
    messages.warning(request, "Room deleted.")
    return redirect('list_rooms')

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



# def create_booking(request):
#     """
#     Create a booking dynamically:
#     - Validate dates (allow same-day check-in/check-out)
#     - Validate room availability
#     - Allow any combination of activities, packages, rooms, food, and tours
#     """
#     if request.method == "POST":
#         # Use logged-in user details if available
#         customer_name = request.user.username if request.user.is_authenticated else request.POST.get("customer_name")
#         customer_email = request.user.email if request.user.is_authenticated else request.POST.get("customer_email")

#         check_in = request.POST.get("check_in")
#         check_out = request.POST.get("check_out")
#         guests = int(request.POST.get("guests", 1))
#         selected_room_ids = request.POST.getlist("rooms")

#         # Validate dates: allow same-day booking
#         if not check_in or not check_out:
#             messages.error(request, "Please select both check-in and check-out dates.")
#             return redirect("create_booking")

#         if check_out < check_in:
#             messages.error(request, "Check-out date cannot be before check-in.")
#             return redirect("create_booking")

#         # Validate room availability
#         for room_id in selected_room_ids:
#             room = get_object_or_404(Room, id=room_id)

#             # Count overlapping bookings
#             overlapping = Booking.objects.filter(
#                 rooms=room,
#                 check_in__lt=check_out,
#                 check_out__gt=check_in
#             ).count()

#             if overlapping >= room.total_rooms:
#                 messages.error(
#                     request,
#                     f"Room '{room.name}' is fully booked for the selected dates."
#                 )
#                 return redirect("create_booking")

#         # Create booking
#         booking = Booking.objects.create(
#             user=request.user if request.user.is_authenticated else None,
#             customer_name=customer_name,
#             customer_email=customer_email,
#             check_in=check_in,
#             check_out=check_out,
#             guests=guests,
#         )

#         # Add selected related objects
#         booking.activities.set(request.POST.getlist("activities"))
#         booking.packages.set(request.POST.getlist("packages"))
#         booking.rooms.set(selected_room_ids)
#         booking.food.set(request.POST.getlist("food"))
#         booking.tours.set(request.POST.getlist("tours"))

#         booking.save()
#         messages.success(request, "Booking created successfully!")
#         return redirect("booking_list")

#     # Context for form rendering
#     context = {
#         "activities": Activity.objects.all(),
#         "packages": Package.objects.all(),
#         "rooms": Room.objects.all(),
#         "food": Food.objects.all(),
#         "tours": Tour.objects.all(),
#     }
#     return render(request, "booking_create.html", context)
def create_booking(request):
    """
    Create a booking dynamically:
    - Validate dates (allow same-day check-in/check-out)
    - Validate room availability
    - Handle pax for activities, packages, rooms, food, tours
    - Role-based: Admin/Staff can select everything; normal users limited to Rooms & Packages
    - Render correct base template depending on user role
    """
    if request.method == "POST":
        # 1. Handle user details
        customer_name = request.user.username if request.user.is_authenticated else request.POST.get("customer_name")
        customer_email = request.user.email if request.user.is_authenticated else request.POST.get("customer_email")

        check_in = request.POST.get("check_in")
        check_out = request.POST.get("check_out")
        guests = int(request.POST.get("guests", 1))

        selected_room_ids = request.POST.getlist("rooms")
        selected_package_ids = request.POST.getlist("packages")
        selected_activity_ids = request.POST.getlist("activities")
        selected_food_ids = request.POST.getlist("food")
        selected_tour_ids = request.POST.getlist("tours")

        # Pax fields
        pax_data = {
            "activities_pax": request.POST.get("activities_pax"),
            "packages_pax": request.POST.get("packages_pax"),
            "rooms_pax": request.POST.get("rooms_pax"),
            "food_pax": request.POST.get("food_pax"),
            "tours_pax": request.POST.get("tours_pax"),
        }

        # 2. Validate dates
        if not check_in or not check_out:
            messages.error(request, "Please select both check-in and check-out dates.")
            return redirect("create_booking")
        if check_out < check_in:  # allow same-day
            messages.error(request, "Check-out date cannot be before check-in.")
            return redirect("create_booking")

        # 3. Validate room availability
        for room_id in selected_room_ids:
            room = get_object_or_404(Room, id=room_id)
            overlapping = Booking.objects.filter(
                rooms=room,
                check_in__lt=check_out,
                check_out__gt=check_in
            ).count()
            if overlapping >= room.total_rooms:
                messages.error(
                    request,
                    f"Room '{room.name}' is fully booked for the selected dates."
                )
                return redirect("create_booking")

        # 4. Role-based restrictions (limit non-staff users)
        if not (request.user.is_staff or request.user.is_superuser):
            selected_activity_ids = []
            selected_food_ids = []
            selected_tour_ids = []

        # 5. Create booking
        booking = Booking.objects.create(
            user=request.user if request.user.is_authenticated else None,
            customer_name=customer_name,
            customer_email=customer_email,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
        )
        booking.activities.set(selected_activity_ids)
        booking.packages.set(selected_package_ids)
        booking.rooms.set(selected_room_ids)
        booking.food.set(selected_food_ids)
        booking.tours.set(selected_tour_ids)

        # Optional: store pax info
        # booking.extra_data = pax_data
        # booking.save()

        messages.success(request, "Booking created successfully!")
        return redirect("booking_list")

    # Decide which base template to use based on user role
    base_template = (
    "base.admin.html" if request.user.is_authenticated and request.user.is_superuser
    else "base.staff.html" if request.user.is_authenticated and request.user.is_staff
    else "base.user.html" if request.user.is_authenticated
    else "base.html"
)

    # Context for form rendering
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

        # ✅ Validate dates
        if check_in > check_out:
            messages.error(request, "Check-out date must be after check-in.")
            return redirect("edit_booking", pk=booking.pk)

        # ✅ Validate room availability
        for room_id in selected_room_ids:
            room = get_object_or_404(Room, id=room_id)
            overlapping = Booking.objects.filter(
                rooms=room,
                check_in__lt=check_out,
                check_out__gt=check_in
            ).exclude(id=booking.id).count()

            if overlapping >= room.total_rooms:
                messages.error(
                    request,
                    f"Room '{room.name}' is fully booked for the selected dates."
                )
                return redirect("edit_booking", pk=booking.pk)

        # ✅ Update booking details
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

    # ✅ Role-based base template selection
    if request.user.is_superuser:
        base_template = "base.admin.html"
    elif request.user.groups.filter(name="Staff").exists():
        base_template = "base.staff.html"
    else:
        base_template = "base.user.html"

    # ✅ Pass all required data
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