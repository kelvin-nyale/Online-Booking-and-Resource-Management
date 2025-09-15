from django.urls import path
from . import views  # Import views from the same app

urlpatterns = [
    path('', views.index, name='home'),  # Landing page
    
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('staff-dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),
    
    path('users/', views.view_users, name='users'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('users/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    
    path('activities/', views.activity_list, name='activity_list'),
    path('activities/add/', views.add_activity, name='add_activity'),
    path('activities/edit/<int:pk>/', views.edit_activity, name='edit_activity'),
    path('activities/delete/<int:pk>/', views.delete_activity, name='delete_activity'),
    
    path('packages/', views.list_packages, name='list_packages'),
    path('packages/add/', views.add_package, name='add_package'),
    path('packages/edit/<int:pk>/', views.edit_package, name='edit_package'),
    path('packages/delete/<int:pk>/', views.delete_package, name='delete_package'),
    
    path('rooms/', views.list_rooms, name='list_rooms'),
    path('rooms/add/', views.add_room, name='add_room'),
    path('rooms/edit/<int:pk>/', views.edit_room, name='edit_room'),
    path('rooms/delete/<int:pk>/', views.delete_room, name='delete_room'),
    path('rooms/book/<int:pk>/', views.book_room, name='book_room'),
    
    # Bookings
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/edit/<int:pk>/', views.edit_booking, name='edit_booking'),
    path('bookings/delete/<int:pk>/', views.delete_booking, name='delete_booking'),
    path('bookings/new/', views.create_booking, name='create_booking'),

]