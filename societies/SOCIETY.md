# Coffee Movement Permit System - Society Management

## Overview
The Coffee Movement Permit System is designed to handle coffee movement permit applications for the County Government of Muranga. The system manages the relationship between society managers and the county administration, facilitating the permit application process for coffee movement.

## User Roles

### 1. Admin (County Director)
- Approves society registrations
- Reviews and approves permit applications
- Manages system-wide settings
- Generates reports and analytics

### 2. Society Manager
- Manages society information
- Handles factory operations
- Sets coffee prices
- Applies for movement permits
- Downloads and distributes permits to farmers

## System Flow

### 1. Registration Process

#### Step 1: Primary Information
- Email
- Phone Number
- Password
- Confirm Password

#### Step 2: Society Information
- First Name
- Last Name
- Society Name
- County
- Sub County

#### Registration Submission
1. System creates:
   - CustomUser with is_active=False
   - Society with is_approved=False
2. System sends:
   - Verification email to user
   - Notification to admin about new registration

### 2. Admin Approval Process

#### Step 1: Admin Notification
- Receives notification of new registration
- Can view registration details
- Verifies society information
- Checks manager's credentials

#### Step 2: Approval Actions
1. Review society information
2. Approve/Reject registration
3. If approved:
   - Society.is_approved = True
   - Manager.is_active = True
   - System sends approval email to manager
4. If rejected:
   - System sends rejection email with reasons

### 3. Post-Approval Setup

#### Factory Management
1. Add factory information:
   - Factory name
   - Location
   - Processing capacity
2. Add multiple factories if needed

#### Coffee Price Management
1. Set coffee grades and prices:
   - Grade (P1, P2, etc.)
   - Price per kilogram
   - Effective date
2. Update prices as needed

### 4. Permit Application Process

#### Step 1: Application Submission
1. Select factory
2. Enter permit details:
   - Coffee quantity
   - Destination
   - Transport details
   - Farmer details
3. Submit application

#### Step 2: Admin Review
1. Receive permit application notification
2. Review application details
3. Approve/Reject permit
4. If approved:
   - Generate permit document
   - Notify manager

#### Step 3: Permit Download
1. Receive permit approval notification
2. Access permit in dashboard
3. Download permit document
4. Print or share with farmers

## Dashboard Views

### Society Manager Dashboard
1. Overview:
   - Society information
   - Factory list
   - Current coffee prices
   - Recent permit applications

2. Actions:
   - Apply for new permit
   - Manage factories
   - Update coffee prices
   - Download permits

### Admin Dashboard
1. Overview:
   - Pending registrations
   - Active societies
   - Recent permit applications
   - System statistics

2. Actions:
   - Approve/reject registrations
   - Review permit applications
   - Generate reports
   - Manage system settings

## API Endpoints

### Registration

POST /api/auth/register/step1/ # Primary information
POST /api/auth/register/step2/ # Society information

### Society Management
GET    /api/societies/          # List societies
POST   /api/societies/          # Create society
GET    /api/societies/{id}/     # Get society details
PUT    /api/societies/{id}/     # Update society
POST   /api/societies/{id}/approve/  # Admin approval

### Factory Management
GET    /api/factories/          # List factories
POST   /api/factories/          # Add factory
PUT    /api/factories/{id}/     # Update factory
DELETE /api/factories/{id}/     # Delete factory

### Coffee Prices
GET    /api/coffee-prices/      # List prices
POST   /api/coffee-prices/      # Set new price
PUT    /api/coffee-prices/{id}/ # Update price

### Permits
GET    /api/permits/            # List permits
POST   /api/permits/            # Apply for permit
GET    /api/permits/{id}/       # Get permit details
GET    /api/permits/{id}/download/  # Download permit

## Security Considerations

### 1. Authentication
- JWT-based authentication
- Secure password handling
- Email verification

### 2. Authorization
- Role-based access control
- Permission checks for all operations
- API endpoint protection

### 3. Data Validation
- Input validation at all steps
- Business rule validation
- Data integrity checks

### 4. Audit Trail
- Log all important actions
- Track changes to critical data
- Maintain history of approvals

## Database Models

### Society
- name
- manager (OneToOneField to CustomUser)
- county
- sub_county
- registration_number
- is_approved
- date_registered
- date_approved
- approved_by

### Factory
- society (ForeignKey to Society)
- name
- location
- capacity
- is_active
- date_added

### CoffeePrice
- society (ForeignKey to Society)
- grade
- price_per_kg
- effective_date
- is_active
- date_set

## Future Enhancements
1. Mobile application support
2. Real-time notifications
3. Advanced reporting and analytics
4. Integration with other county systems
5. Automated permit generation
6. Payment integration for permit fees

GET /api/societies/ # List societies
POST /api/societies/ # Create society
GET /api/societies/{id}/ # Get society details
PUT /api/societies/{id}/ # Update society
POST /api/societies/{id}/approve/ # Admin approval


### Factory Management
GET /api/factories/ # List factories
POST /api/factories/ # Add factory
PUT /api/factories/{id}/ # Update factory
DELETE /api/factories/{id}/ # Delete factory

