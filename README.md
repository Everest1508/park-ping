# ParkPing - QR Code Parking Contact System

ParkPing is a subscription-based QR code generation system that allows vehicle owners to create QR codes for their vehicles. When someone scans the QR code, they can contact the vehicle owner for various reasons like moving a blocking car, reporting damage, or other emergencies.

## Features

### 🔐 Authentication System
- Custom user model with phone number support
- User registration and login
- Profile management
- Multiple phone number support per user
- Phone number verification system

### 🚗 Vehicle Management
- Add, edit, and delete vehicles
- Vehicle details (make, model, year, color, license plate, VIN)
- Contact phone number association
- Visibility settings for contact information

### 📱 Subscription Plans
- **Free Plan**: 1 vehicle, no number masking
- **Basic Plan**: 3 vehicles, number masking, $9.99/month
- **Professional Plan**: 10 vehicles, custom QR design, analytics, $19.99/month
- **Enterprise Plan**: 50 vehicles, all features, custom branding, $49.99/month

### 🎯 QR Code Features
- Automatic QR code generation for each vehicle
- Customizable QR code appearance (based on plan)
- Unique QR codes for each vehicle
- QR code scanning tracking and analytics

### 📍 Parking Sessions
- Start and end parking sessions
- Location tracking
- Session history and duration calculation

### 📞 Contact System
- Public QR code scanning
- Contact form for vehicle owners
- Call and SMS options
- Reason-based contact requests

## Technology Stack

- **Backend**: Django 5.2.5
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Authentication**: Django's built-in authentication system
- **QR Code Generation**: qrcode library
- **Image Processing**: Pillow (PIL)
- **Frontend**: HTML, CSS, JavaScript (templates ready for styling)

## Installation & Setup

### Prerequisites
- Python 3.8+
- pip
- virtual environment (recommended)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd park-ping
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser
```bash
python manage.py createsuperuser
```

### 6. Setup Default Subscription Plans
```bash
python manage.py setup_plans
```

### 7. Run Development Server
```bash
python manage.py runserver
```

## Project Structure

```
park-ping/
├── core/                   # Main project settings
│   ├── settings.py        # Django settings
│   ├── urls.py           # Main URL configuration
│   └── wsgi.py           # WSGI configuration
├── accounts/              # User authentication app
│   ├── models.py         # Custom user and phone number models
│   ├── views.py          # Authentication views
│   ├── forms.py          # User forms
│   ├── admin.py          # Admin interface
│   └── urls.py           # Account URLs
├── parking/               # Main parking app
│   ├── models.py         # Vehicle, subscription, and parking models
│   ├── views.py          # Parking-related views
│   ├── forms.py          # Vehicle and parking forms
│   ├── admin.py          # Admin interface
│   ├── urls.py           # Parking URLs
│   └── management/       # Management commands
├── manage.py             # Django management script
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Models Overview

### CustomUser
- Extends Django's AbstractUser
- Phone number support
- Subscription plan association
- Profile information

### UserPhoneNumber
- Multiple phone numbers per user
- Primary number designation
- Verification status
- Labels (Work, Home, Mobile)

### SubscriptionPlan
- Plan types and pricing
- Feature limits (vehicles, phone numbers)
- Customization options
- Plan status management

### Vehicle
- Vehicle details and specifications
- QR code association
- Contact information visibility settings
- User ownership

### QRCodeScan
- Tracks QR code scans
- IP address and user agent logging
- Location tracking (optional)
- Timestamp recording

### ParkingSession
- Parking start/end times
- Location information
- Session status management
- Notes and additional information

## API Endpoints

### Authentication
- `POST /accounts/signup/` - User registration
- `POST /accounts/login/` - User login
- `POST /accounts/logout/` - User logout

### Vehicle Management
- `GET /parking/vehicles/` - List user vehicles
- `POST /parking/vehicles/add/` - Add new vehicle
- `GET /parking/vehicles/<id>/` - Vehicle details
- `PUT /parking/vehicles/<id>/edit/` - Edit vehicle
- `DELETE /parking/vehicles/<id>/delete/` - Delete vehicle

### QR Code
- `GET /parking/qr/<uuid>/` - Scan QR code (public)
- `POST /parking/qr/<uuid>/contact/` - Contact vehicle owner

### Subscription
- `GET /parking/plans/` - View subscription plans
- `POST /parking/plans/<id>/select/` - Select subscription plan

## Usage Examples

### Adding a Vehicle
1. User logs in to their account
2. Navigates to Vehicles section
3. Clicks "Add Vehicle"
4. Fills in vehicle details
5. Selects contact phone number
6. Sets visibility preferences
7. Vehicle is created with auto-generated QR code

### Scanning a QR Code
1. Someone scans the QR code on a parked vehicle
2. They see contact information based on owner's settings
3. They can choose to call or send a message
4. Contact request is sent to vehicle owner
5. Owner receives notification and can respond

### Managing Subscription
1. User views available plans
2. Selects desired plan
3. Completes payment (integration needed)
4. Plan features become available
5. User can upgrade/downgrade as needed

## Customization

### QR Code Appearance
- Primary and secondary colors
- Logo placement (premium plans)
- Custom branding (enterprise plans)
- Size options

### Contact Information Visibility
- Phone number display
- Name visibility
- Email visibility
- Vehicle details display

## Future Enhancements

- [ ] Payment gateway integration (Stripe, PayPal)
- [ ] SMS service integration (Twilio)
- [ ] Push notifications
- [ ] Mobile app development
- [ ] Advanced analytics dashboard
- [ ] Bulk QR code generation
- [ ] API rate limiting
- [ ] Webhook support
- [ ] Multi-language support
- [ ] Advanced reporting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please contact the development team or create an issue in the repository.

---

**Note**: This is a development version. For production use, additional security measures, payment processing, and SMS service integration should be implemented.
