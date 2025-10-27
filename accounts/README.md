# User Role System

This application implements a three-tier user role system: **Admin**, **Doctor**, and **Secretary**.

## Roles

### Admin
- Full access to all doctors and their secretaries
- Can manage all data in the system
- Usually has `is_superuser=True` and `is_staff=True`

### Doctor
- Access to their own data only
- Can manage their own appointments, patients, prescriptions, etc.
- Has a one-to-one relationship with the User model through the `doctor_profile`
- Can access all their assigned secretaries

### Secretary
- Access to data for the doctor they work for
- Assigned to one doctor through a foreign key relationship
- Helps manage their doctor's appointments and patients

## Models

### Secretary Model
Located in `accounts/models.py`:
- `user`: OneToOne relationship with Django User
- `doctor`: ForeignKey to Doctor
- `phone`: Contact phone number
- `is_active`: Whether the secretary is active
- `created_at`, `updated_at`: Timestamps

## Usage

### Creating Users with Roles

Use the management command to create users with specific roles:

#### Create an Admin:
```bash
python manage.py create_user_with_role admin --role admin --email admin@example.com --first-name Admin --last-name User
```

#### Create a Doctor:
```bash
python manage.py create_user_with_role doctor_name --role doctor --email doctor@example.com --first-name John --last-name Doe --medical-license ABC123 --specialization "Cardiology" --phone "+5511999999999"
```

#### Create a Secretary:
```bash
python manage.py create_user_with_role secretary_name --role secretary --email secretary@example.com --first-name Jane --last-name Smith --doctor-username doctor_name --phone "+5511888888888"
```

### Using Role Functions in Views

Import the utility functions in your views:

```python
from accounts.utils import (
    get_user_role,
    get_doctor_for_user,
    can_access_doctor,
    get_accessible_doctors
)

def my_view(request):
    # Get user's role
    role = get_user_role(request.user)
    
    # Get the doctor for the current user
    doctor = get_doctor_for_user(request.user)
    
    # Check if user can access a specific doctor
    can_access = can_access_doctor(request.user, target_doctor)
    
    # Get all doctors the user can access
    doctors = get_accessible_doctors(request.user)
```

### Using Role Information in Templates

The `user_role` context processor provides role information to all templates:

```html
{% if is_admin %}
    <!-- Admin-only content -->
    <p>You have full access to all doctors.</p>
{% elif is_doctor %}
    <!-- Doctor content -->
    <p>You are a doctor.</p>
{% elif is_secretary %}
    <!-- Secretary content -->
    <p>You are working for Dr. {{ user_doctor.user.get_full_name }}</p>
{% endif %}

<!-- Show user's role -->
<p>Your role: {{ user_role|title }}</p>

<!-- Show accessible doctors -->
{% for doctor in accessible_doctors %}
    <p>{{ doctor }}</p>
{% endfor %}
```

### Filtering Data by Role

In your views, filter data based on the user's role:

```python
from dashboard.models import Appointment
from accounts.utils import get_doctor_for_user, get_user_role

def appointments_view(request):
    role = get_user_role(request.user)
    doctor = get_doctor_for_user(request.user)
    
    if role == 'admin':
        # Admin sees all appointments
        appointments = Appointment.objects.all()
    elif role in ['doctor', 'secretary']:
        # Doctor and secretary see only their doctor's appointments
        appointments = Appointment.objects.filter(doctor=doctor)
    else:
        appointments = Appointment.objects.none()
    
    return render(request, 'appointments.html', {'appointments': appointments})
```

### Permissions

Use the utility functions to check permissions:

```python
from accounts.utils import can_access_doctor, has_access_to_patient

def patient_detail_view(request, patient_id):
    from dashboard.models import Patient
    
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        raise Http404
    
    # Check if user can access this patient
    if not has_access_to_patient(request.user, patient):
        return HttpResponseForbidden("You don't have access to this patient.")
    
    # Show patient details
    return render(request, 'patient_detail.html', {'patient': patient})
```

## Database Structure

```
User (Django built-in)
├── Doctor (one-to-one)
│   ├── Medical License
│   ├── Specialization
│   └── ...
└── Secretary (one-to-one)
    ├── Doctor (foreign key)
    └── ...
```

## Examples

### Example 1: Check if user is admin
```python
from accounts.utils import get_user_role

if get_user_role(request.user) == 'admin':
    # Do admin stuff
    pass
```

### Example 2: Get all secretaries for a doctor
```python
from accounts.utils import get_secretaries_for_doctor

doctor = request.user.doctor_profile
secretaries = get_secretaries_for_doctor(doctor)
```

### Example 3: Check access before showing data
```python
from accounts.utils import can_access_doctor

if not can_access_doctor(request.user, target_doctor):
    return HttpResponseForbidden("Access denied")
```

## Context Processor

The `user_role` context processor automatically adds these variables to all templates:

- `user_role`: Current user's role ('admin', 'doctor', 'secretary', or None)
- `user_doctor`: The doctor object for the current user
- `accessible_doctors`: List of doctors the user can access
- `is_admin`: Boolean indicating if user is admin
- `is_doctor`: Boolean indicating if user is doctor
- `is_secretary`: Boolean indicating if user is secretary

