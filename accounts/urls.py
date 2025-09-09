from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Profile and Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password_view, name='change_password'),
    
    # Phone Number Management
    path('phone-numbers/', views.phone_numbers_view, name='phone_numbers'),
    path('phone-numbers/add/', views.phone_numbers_view, name='add_phone_number'),
    path('phone-numbers/<int:pk>/edit/', views.edit_phone_number, name='edit_phone_number'),
    path('phone-numbers/<int:pk>/delete/', views.delete_phone_number, name='delete_phone_number'),
    path('phone-numbers/<int:pk>/set-primary/', views.set_primary_phone, name='set_primary_phone'),
    path('phone-numbers/<int:pk>/verify/', views.verify_phone_number, name='verify_phone_number'),
    
    # API endpoints
    path('api/send-verification-code/', views.send_verification_code, name='send_verification_code'),
]
