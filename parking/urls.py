from django.urls import path
from . import views

app_name = 'parking'

urlpatterns = [
    # Vehicle Management
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/add/', views.add_vehicle, name='add_vehicle'),
    path('vehicles/<int:pk>/', views.vehicle_detail, name='vehicle_detail'),
    path('vehicles/<int:pk>/edit/', views.edit_vehicle, name='edit_vehicle'),
    path('vehicles/<int:pk>/delete/', views.delete_vehicle, name='delete_vehicle'),
    path('vehicles/<int:pk>/regenerate-qr/', views.regenerate_qr_code, name='regenerate_qr_code'),
    path('vehicles/<int:pk>/toggle-qr/', views.toggle_qr_code, name='toggle_qr_code'),
    path('vehicles/<int:pk>/customize-qr/', views.customize_qr, name='customize_qr'),
    
    # QR Code Management
    path('qr-codes/', views.qr_codes, name='qr_codes'),
    
    # Parking Sessions
    path('parking-sessions/', views.parking_sessions, name='parking_sessions'),
    path('vehicles/<int:vehicle_id>/start-parking/', views.start_parking_session, name='start_parking_session'),
    path('parking-sessions/<int:session_id>/end/', views.end_parking_session, name='end_parking_session'),
    
    # Subscription Plans
    path('plans/', views.subscription_plans, name='subscription_plans'),
    path('plans/<int:plan_id>/select/', views.select_plan, name='select_plan'),
    
    # QR Code and Public Access
    path('qr/<uuid:qr_id>/', views.scan_qr_code, name='scan_qr_code'),
    path('qr/<uuid:qr_id>/contact/', views.contact_owner_api, name='contact_owner_api'),
    path('qr/<uuid:qr_id>/masked-number/', views.get_masked_number_api, name='get_masked_number_api'),
    path('qr/<uuid:qr_id>/terminate-masking/', views.terminate_masking_session_api, name='terminate_masking_session_api'),
    path('qr/<uuid:qr_id>/initiate-call/', views.initiate_twilio_call, name='initiate_twilio_call'),
    path('qr/<uuid:qr_id>/twilio-connect/', views.twilio_connect_twiml, name='twilio_connect_twiml'),
    path('qr/<uuid:qr_id>/twilio-status/', views.twilio_status_callback, name='twilio_status_callback'),
    path('search/', views.search_vehicle, name='search_vehicle'),
    
    # Chatbot
    path('chatbot/', views.chatbot_api, name='chatbot_api'),
]
