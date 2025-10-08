# Haven-Backend
In an emergency, seconds save lives. Haven notifies the nearest hospital before you arrive, so they can prioritize your care and prepare to act the moment you get there. Your safe passage to care.



# Haven Platform - App Architecture Notes

##  Accounts App
**Purpose**: User Management & Authentication
- User registration & profile management
- JWT authentication system
- Role-based access control (Patient, Hospital Admin, System Admin)
- Multi-factor authentication (SMS/Email)
- Emergency bypass for critical access
- Phone number verification

## Emergencies App  
**Purpose**: Core Emergency Response
- Emergency alert creation & lifecycle management
- Real-time location tracking
- Alert prioritization (Critical/High/Medium)
- WebSocket connections for live updates
- Emergency session coordination
- Duplicate alert prevention

## Hospitals App
**Purpose**: Hospital Discovery & Matching
- Hospital database with capabilities
- Real-time availability checking
- Intelligent matching algorithm:
  - Distance (40% weight)
  - Capacity (30% weight) 
  - Specialty match (30% weight)
- Multi-channel hospital communication
- Fallback hospital selection

## Medical App
**Purpose**: Secure Medical Data
- Medical profile storage (blood type, allergies, conditions)
- Current medications tracking
- Emergency contacts management
- Insurance information
- GDPR/HIPAA compliant data handling
- Consent management for emergency sharing

## Notifications App
**Purpose**: Multi-channel Alerts
- SMS notifications (Africa's Talking API)
- Push notifications for mobile apps
- Email alerts for non-critical comms
- Retry mechanisms with exponential backoff
- Delivery status tracking
- Async task processing

---

## Emergency Workflow
1. **Auth** → User authentication (Accounts)
2. **Alert** → Create emergency (Emergencies) 
3. **Match** → Find best hospital (Hospitals)
4. **Notify** → Alert hospital (Notifications)
5. **Share** → Provide medical data (Medical)

---

## Security Features
- JWT token authentication
- Role-based permissions
- Medical data encryption
- GDPR compliance (right to delete)
- Audit logging for all emergencies
- Secure API endpoints

---

## Scalability
- Database indexing for fast geospatial queries
- Caching for hospital availability
- Async task processing
- WebSocket connections for real-time
- Independent app scaling
- Load-balanced services