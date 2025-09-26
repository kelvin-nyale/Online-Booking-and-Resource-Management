from django.urls import path
from . import views  # Import views from the same app
from .views import notifications_view, mark_notification_read
from django.conf import settings
from django.conf.urls.static import static

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
    
    path('tours/', views.tours, name='tours'),
    path('tours/add/', views.add_tour, name='add_tour'),
    path('tour/edit/<int:pk>/', views.edit_tour, name='edit_tour'),
    path('tour/deelete/<int:pk>/', views.delete_tour, name='delete_tour'),
    
    path('rooms/', views.list_rooms, name='list_rooms'),
    path('rooms/add/', views.add_room, name='add_room'),
    path('rooms/<int:room_id>/edit/', views.edit_room, name='edit_room'),
    path('rooms/<int:room_id>/delete/', views.delete_room, name='delete_room'),
    path('rooms/book/<int:pk>/', views.book_room, name='book_room'),
    
    path('room-types/', views.room_types, name='room_types'),
    path('room-type/add/', views.add_room_type, name='add_room_type'),
    path('room-type/edit/<int:pk>/', views.edit_room_type, name='edit_room_type'),
    path('room-type/delete/<int:pk>/', views.delete_room_type, name='delete_room_type'),
    
    path('food-list/', views.food_list, name='food_list'),
    path('food/add/', views.add_food, name='add_food'),
    path('food/edit/<int:pk>/', views.edit_food, name='edit_food'),
    path('food/delete/<int:pk>/', views.delete_food, name='delete_food'),
    
    # Bookings
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/edit/<int:pk>/', views.edit_booking, name='edit_booking'),
    path('bookings/delete/<int:pk>/', views.delete_booking, name='delete_booking'),
    path('bookings/new/', views.create_booking, name='create_booking'),
    path('bookings/new/for-user/', views.admin_create_booking, name='create_user_booking'),  # booking on behalf of user
    
    path('menu/', views.food_menu, name='food_menu'),
    path('order/place/', views.place_order, name='place_order'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('update-order/<int:order_id>/', views.update_order, name='update_order'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('manage-orders/', views.manage_orders, name='manage_orders'),
    path('update-order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    
    path('notifications/', notifications_view, name='notifications'),
    path('notifications/<int:pk>/read/', mark_notification_read, name='mark_notification_read'),
    
    path('explore/', views.explore, name='explore'),
    path('reports/', views.reports_analytics, name='reports_analytics'),
    
    path('duties/assign/', views.assign_duty, name='assign_duty'),
    path('duties/', views.duties, name='duties'),
    path('duty/<int:duty_id>/update/', views.update_duty_status, name='update_duty_status'),
    path('duties/staff/', views.staff_duties, name='staff_duties'),
    
    path('upcoming-bookings/', views.upcoming_bookings_list, name='upcoming_bookings'),
    
    path('backup/', views.backup_data, name='backup_data'),
    path("system-settings/", views.system_settings, name="system_settings"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)