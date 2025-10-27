"""
Context processors for user role and permissions
"""


def user_role(request):
    """
    Add user role information to template context
    """
    from .utils import get_user_role, get_doctor_for_user, get_accessible_doctors
    
    if not request.user or not request.user.is_authenticated:
        return {
            'user_role': None,
            'user_doctor': None,
            'accessible_doctors': [],
            'selected_doctor_id': None,
            'is_admin': False,
            'is_doctor': False,
            'is_secretary': False
        }
    
    role = get_user_role(request.user)
    doctor = get_doctor_for_user(request.user)
    accessible_doctors = list(get_accessible_doctors(request.user))
    
    # Get selected doctor ID from session (for admins)
    selected_doctor_id = request.session.get('selected_doctor_id') if hasattr(request, 'session') else None
    
    return {
        'user_role': role,
        'user_doctor': doctor,
        'accessible_doctors': accessible_doctors,
        'selected_doctor_id': selected_doctor_id,
        'is_admin': role == 'admin',
        'is_doctor': role == 'doctor',
        'is_secretary': role == 'secretary'
    }

