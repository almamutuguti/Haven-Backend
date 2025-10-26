# Haven Emergency Response Platform - Backend System

##  Overview
A scalable, mission-critical backend architecture for the Haven emergency response platform, designed to be the most reliable and efficient emergency hospital integration system in Kenya. Provides comprehensive emergency response features with 99.99% uptime for critical alerting pathways.

## System Architecture

### Tech Stack
- **Language**: Python 3.11+
- **Framework**: Django 5.x with Django REST Framework
- **Database**: PostgreSQL 15+ (primary)
- **Authentication**: JWT with djangorestframework-simplejwt
- **Real-Time Communication**: Django Channels with WebSockets
- **Geolocation**: Google Maps API integration

## Core App Modules

### 1. Emergency Alert Management (`emergencies`)
**Features:**
- One-tap emergency activation
- Real-time location tracking
- Alert prioritization (critical, high, medium)
- Duplicate alert prevention
- Emergency session management

**Key Endpoints:**
- `POST /api/emergency/alert` - Trigger emergency response
- `GET /api/emergency/{alert_id}/status` - Get alert status
- `PUT /api/emergency/{alert_id}/location` - Update patient location
- `POST /api/emergency/{alert_id}/cancel` - Cancel emergency alert

### 2. Hospital Discovery & Matching (`hospitals`)
**Features:**
- Real-time hospital availability checking
- Proximity-based hospital ranking
- Specialty matching (trauma, cardiac, pediatric)
- Capacity-based routing
- Fallback hospital selection
- Hospital performance metrics

**Key Endpoints:**
- `GET /api/hospitals/nearby` - Discover nearby hospitals
- `POST /api/hospitals/{id}/availability` - Check hospital capacity
- `GET /api/hospitals/{id}/capabilities` - Get hospital specialties

### 3. Medical Profile Management (`medical`)
**Features:**
- Secure medical data storage (GDPR/HIPAA compliant)
- Blood type, allergies, conditions tracking
- Current medications management
- Emergency contacts storage
- Medical insurance information

**Key Endpoints:**
- `POST /api/medical-profile` - Create medical profile
- `GET /api/medical-profile` - Retrieve medical profile
- `PUT /api/medical-profile` - Update medical profile
- `DELETE /api/medical-profile` - Delete medical profile (GDPR compliance)

### 4. Hospital Communication Service (`hospital_comms`)
**Features:**
- Multi-channel hospital notification (API, SMS, Webhook)
- First-aider victim assessment at scene
- Hospital preparation status tracking
- Retry mechanism with exponential backoff
- Delivery status tracking
- Emergency data packet formatting

**Key Models:**
- `EmergencyHospitalCommunication` - Core communication tracking
- `FirstAiderAssessment` - Detailed victim assessment data
- `HospitalPreparationChecklist` - Hospital readiness tracking
- `CommunicationLog` - All communication attempts

### 5. Real-time Tracking & ETA (`geolocation`)
**Features:**
- Live GPS tracking for patients and first-aiders
- Dynamic ETA calculations
- Traffic-aware routing
- Route optimization
- Hospital proximity caching

**Key Models:**
- `Location` - Coordinate and address storage
- `EmergencyTracking` - Emergency movement updates
- `RouteCalculation` - Pre-calculated routes
- `TrafficUpdate` - Real-time traffic conditions

### 6. Authentication & Authorization (`accounts`)
**Features:**
- JWT-based authentication
- Role-based access control (Patient, First-Aider, Hospital Admin, System Admin)
- Emergency bypass authentication
- Session management

**Key Endpoints:**
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Token refresh
- `POST /api/auth/emergency-bypass` - Emergency access

### 7. Notifications System (`notifications`)
**Features:**
- Multi-channel delivery (SMS, Push, Email, Voice)
- Template-based messaging system
- User notification preferences
- Delivery status tracking
- Bulk notification sending
- Africa's Talking SMS integration

**Key Models:**
- `Notification` - Central notification system
- `NotificationTemplate` - Reusable message templates
- `UserNotificationPreference` - User channel preferences
- Delivery logs for all channels

##  Emergency Response Workflow

### Complete Lifecycle:
1. **Emergency Alert** → System activates and notifies nearby first-aiders
2. **First-Aider Dispatch** → Nearest available first-aiders dispatched to scene
3. **Victim Assessment** → First-aiders assess victim and input medical data
4. **Hospital Communication** → Data sent to nearest appropriate hospital
5. **Hospital Preparation** → Hospital prepares team, equipment, and facilities
6. **Status Updates** → Real-time tracking and ETA provided to all parties
7. **Patient Handover** → Seamless transfer from first-aiders to hospital staff

##  Project Structure



## Installation & Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis (for caching and channels)

### Installation Steps
```bash
# Clone repository
git clone <repository-url>
cd Haven-Backend

# Create virtual environment
python -m venv virtual
source virtual/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Environment configuration
cp .env.example .env
# Edit .env with your database and API credentials

# Database setup
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver




