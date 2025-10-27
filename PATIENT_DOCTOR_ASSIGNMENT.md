# Patient-Doctor Assignment System

Patients are now linked to doctors. Each doctor can only see and manage their own patients.

## How It Works

### Patient Model
- Each patient has a `doctor` ForeignKey that links them to a specific doctor
- Doctors can only view and manage their own patients
- Secretaries can view patients of their assigned doctor
- Admins can view patients of all doctors they manage

### Usage

#### Creating a Patient with Doctor Assignment

When creating a patient, you must specify which doctor they belong to:

```python
from dashboard.models import Patient, Doctor

# Get the doctor
doctor = Doctor.objects.get(medical_license="ABC123")

# Create patient assigned to that doctor
patient = Patient.objects.create(
    doctor=doctor,  # Required
    first_name="John",
    last_name="Doe",
    date_of_birth="1990-01-01",
    gender="M",
    email="john@example.com",
    phone="+5511999999999"
)
```

#### Assigning Existing Patients to Doctors

If you have existing patients without a doctor assignment:

```bash
# Assign all patients to a specific doctor
python manage.py assign_patients_to_doctors --doctor-username doctor_user

# Assign patients evenly across all active doctors
python manage.py assign_patients_to_doctors --all-doctors
```

### Filtering Patients by Role

#### For Doctors
```python
from django.contrib.auth.decorators import login_required
from dashboard.models import Patient

@login_required
def my_patients_view(request):
    # Get current doctor
    doctor = request.user.doctor_profile
    
    # Get only this doctor's patients
    patients = Patient.objects.filter(doctor=doctor)
    
    return render(request, 'patients.html', {'patients': patients})
```

#### For Admins
```python
@login_required
def admin_patients_view(request):
    # Get current admin
    admin = request.user.admin_profile
    
    # Get patients of all doctors managed by this admin
    patients = Patient.objects.filter(doctor__in=admin.doctors.all())
    
    return render(request, 'patients.html', {'patients': patients})
```

#### For Secretaries
```python
@login_required
def secretary_patients_view(request):
    # Get current secretary
    secretary = request.user.secretary_profile
    
    # Get patients of the secretary's assigned doctor
    patients = Patient.objects.filter(doctor=secretary.doctor)
    
    return render(request, 'patients.html', {'patients': patients})
```

### Using Utility Functions

```python
from accounts.utils import get_accessible_patients, has_access_to_patient

# Get all patients a user can access
patients = get_accessible_patients(request.user)

# Check if user can access a specific patient
if has_access_to_patient(request.user, patient):
    # Show patient details
    pass
```

### Admin Interface

In the Django admin:
- Patients show their assigned doctor
- You can filter patients by doctor
- You must assign a doctor when creating a new patient
- Doctors can be assigned/removed from patients

### Database Schema

```sql
patient
├── doctor (FK -> Doctor)
├── first_name
├── last_name
├── email
├── phone
└── ... other fields
```

### API Endpoints

All patient-related API endpoints will automatically filter by doctor:

```python
# In your API views
@login_required
def api_patients(request):
    from accounts.utils import get_accessible_patients
    
    # Returns only patients the user can access
    patients = get_accessible_patients(request.user)
    
    # Serialize and return
    ...
```

