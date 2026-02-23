// FullCalendar Integration
let calendar;
let calendarInitialized = false;

// Load settings early so colors are available
function ensureSettingsLoaded() {
    if (typeof appointmentSettings === 'undefined' || !appointmentSettings) {
        // Try to load settings if not already loaded
        if (typeof loadSettings === 'function') {
            loadSettings();
        }
    }
}

// Initialize FullCalendar when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Load settings first
    ensureSettingsLoaded();
    
    // Check if agenda tab is already active
    const agendaTab = document.getElementById('agenda-tab');
    if (agendaTab && agendaTab.classList.contains('active')) {
        setTimeout(initializeFullCalendar, 100);
    }
});

function isMobileDevice() {
    return window.matchMedia('(max-width: 768px)').matches ||
        (typeof navigator !== 'undefined' && /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));
}

function initializeFullCalendar() {
    if (calendarInitialized) {
        return;
    }
    
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) {
        return;
    }
    
    calendarInitialized = true;

    // On cellphone/mobile: show day view; on desktop: show week view
    const initialView = isMobileDevice() ? 'timeGridDay' : 'timeGridWeek';

    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: initialView,
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        locale: 'pt-br',
        timeZone: 'local', // Use local timezone - ensures ISO strings are interpreted in local time
        // This makes the time slots and events align perfectly
        firstDay: 1, // Monday
        weekends: false, // Hide weekends
        nowIndicator: true,
        editable: true,
        selectable: true,
        selectMirror: true,
        dayMaxEvents: true,
        moreLinkText: function(num) {
            return num + '+ mais';
        },
        height: 650,
        slotMinTime: '06:00:00',
        slotMaxTime: '20:00:00',
        slotDuration: '00:15:00',
        slotLabelFormat: {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        },
        allDaySlot: false, // Remove all-day row
        businessHours: {
            daysOfWeek: [1, 2, 3, 4, 5], // Monday - Friday
            startTime: '08:00',
            endTime: '18:00',
        },
        buttonText: {
            today: 'Hoje',
            month: 'Mês',
            week: 'Semana',
            day: 'Dia',
        },
        events: function(info, successCallback, failureCallback) {
            // Load appointments for the current view
            loadAppointmentsForCalendar(info.start, info.end, successCallback, failureCallback);
        },
        eventContent: function(arg) {
            // Calendar blocks: show title only
            if (arg.event.extendedProps.isBlock) {
                const viewType = arg.view.type;
                const title = arg.event.title;
                if (viewType === 'timeGridWeek' || viewType === 'timeGridDay') {
                    return { html: title };
                }
                return { html: title };
            }
            // Custom event content to show dollar symbol for particular appointments and NOVO badge for first appointments
            const paymentType = arg.event.extendedProps.paymentType;
            const isFirstAppointment = !!arg.event.extendedProps.isFirstAppointment;
            const patientName = arg.event.title;
            const viewType = arg.view.type;
            
            // For week view, use HTML string as it's more reliable
            // For month view, use domNodes
            if (viewType === 'timeGridWeek' || viewType === 'timeGridDay') {
                // Week view: use HTML string
                let content = patientName;
                if (isFirstAppointment) {
                    content += ' <span class="novo-badge">NOVO</span>';
                }
                if (paymentType === 'Particular') {
                    content += ' <span class="particular-dollar">$</span>';
                }
                return { html: content };
            } else {
                // Month view: use domNodes
                const fragment = document.createDocumentFragment();
                const nameText = document.createTextNode(patientName);
                fragment.appendChild(nameText);
                
                if (isFirstAppointment) {
                    const novoBadge = document.createElement('span');
                    novoBadge.className = 'novo-badge';
                    novoBadge.textContent = 'NOVO';
                    fragment.appendChild(novoBadge);
                }
                
                if (paymentType === 'Particular') {
                    const dollarSymbol = document.createElement('span');
                    dollarSymbol.className = 'particular-dollar';
                    dollarSymbol.textContent = '$';
                    fragment.appendChild(dollarSymbol);
                }
                
                const nodes = Array.from(fragment.childNodes);
                return { domNodes: nodes };
            }
        },
        eventDidMount: function(info) {
            // Calendar blocks: only set block styling, no appointment badges
            if (info.event.extendedProps.isBlock) {
                info.el.setAttribute('data-block', 'true');
                info.el.style.setProperty('background-color', '#6c757d', 'important');
                info.el.style.setProperty('border-color', '#6c757d', 'important');
                return;
            }
            // Add appointment type as description below the event
            const appointmentType = info.event.extendedProps.appointmentType;
            const status = info.event.extendedProps.status;
            const isFirstAppointment = !!info.event.extendedProps.isFirstAppointment;
            const paymentType = info.event.extendedProps.paymentType;
            
            // Add status data attribute for CSS targeting
            info.el.setAttribute('data-status', status);
            
            // Apply custom color from settings (override CSS with inline style using !important)
            const eventColor = getEventColor(status);
            if (eventColor) {
                // Use setProperty with 'important' flag to override CSS !important rules
                info.el.style.setProperty('background-color', eventColor, 'important');
                info.el.style.setProperty('border-color', eventColor, 'important');
            }
            
            // Add NOVO badge and dollar symbol after a small delay to ensure DOM is ready
            // This is especially important when events are re-rendered via refetchEvents
            // Use a slightly longer delay for week view which has different DOM structure
            const delay = info.view.type === 'timeGridWeek' ? 10 : 0;
            setTimeout(() => {
                // Add NOVO badge for first appointments
                if (isFirstAppointment) {
                    // Check if badge already exists (from eventContent or previous render)
                    const existingBadge = info.el.querySelector('.novo-badge');
                    if (!existingBadge) {
                        const novoBadge = document.createElement('span');
                        novoBadge.className = 'novo-badge';
                        novoBadge.textContent = 'NOVO';
                        
                        // For week view (timeGrid), events have different structure
                        // Try to find the main content container
                        let targetElement = null;
                        
                        if (info.view.type === 'timeGridWeek' || info.view.type === 'timeGridDay') {
                            // Week view: look for fc-event-main or fc-event-title-container
                            targetElement = info.el.querySelector('.fc-event-main') ||
                                          info.el.querySelector('.fc-event-title-container') ||
                                          info.el.querySelector('.fc-event-title') ||
                                          info.el;
                        } else {
                            // Month view: look for standard elements
                            targetElement = info.el.querySelector('.fc-event-title') || 
                                          info.el.querySelector('.fc-event-title-container') ||
                                          info.el.querySelector('.fc-event-main') ||
                                          info.el;
                        }
                        
                        // Append badge to the target element
                        if (targetElement) {
                            // Check if there's text content we should append after
                            const textNodes = Array.from(targetElement.childNodes).filter(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim());
                            if (textNodes.length > 0) {
                                // Insert after the last text node
                                const lastTextNode = textNodes[textNodes.length - 1];
                                lastTextNode.parentNode.insertBefore(novoBadge, lastTextNode.nextSibling);
                            } else {
                                // Append to the end
                                targetElement.appendChild(novoBadge);
                            }
                        }
                    }
                }
                
                // Add dollar symbol for particular appointments
                if (paymentType === 'Particular') {
                    // Check if dollar symbol already exists (from eventContent or previous render)
                    const existingDollar = info.el.querySelector('.particular-dollar');
                    if (!existingDollar) {
                        const dollarSymbol = document.createElement('span');
                        dollarSymbol.className = 'particular-dollar';
                        dollarSymbol.textContent = '$';
                        
                        // For week view (timeGrid), events have different structure
                        let targetElement = null;
                        
                        if (info.view.type === 'timeGridWeek' || info.view.type === 'timeGridDay') {
                            // Week view: look for fc-event-main or fc-event-title-container
                            targetElement = info.el.querySelector('.fc-event-main') ||
                                          info.el.querySelector('.fc-event-title-container') ||
                                          info.el.querySelector('.fc-event-title') ||
                                          info.el;
                        } else {
                            // Month view: look for standard elements
                            targetElement = info.el.querySelector('.fc-event-title') || 
                                          info.el.querySelector('.fc-event-title-container') ||
                                          info.el.querySelector('.fc-event-main') ||
                                          info.el;
                        }
                        
                        // Append dollar symbol to the target element
                        if (targetElement) {
                            const textNodes = Array.from(targetElement.childNodes).filter(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim());
                            if (textNodes.length > 0) {
                                const lastTextNode = textNodes[textNodes.length - 1];
                                lastTextNode.parentNode.insertBefore(dollarSymbol, lastTextNode.nextSibling);
                            } else {
                                targetElement.appendChild(dollarSymbol);
                            }
                        }
                    }
                }
            }, delay);
            
            // Map appointment types to Portuguese
            const typeMap = {
                'consultation': 'Consulta',
                'follow_up': 'Retorno',
                'checkup': 'Check-up',
                'emergency': 'Emergência',
                'procedure': 'Procedimento',
                'therapy': 'Terapia',
                'other': 'Outro'
            };
            
            const typeDisplay = typeMap[appointmentType] || appointmentType;
            
            // Add the appointment type as a small description below the event
            const description = document.createElement('div');
            description.className = 'fc-event-description';
            description.textContent = typeDisplay;
            
            info.el.appendChild(description);
        },
        eventClick: function(info) {
            if (info.event.extendedProps.isBlock) {
                showBlockDetailsModal(info.event);
                return;
            }
            // Handle event click - show appointment details
            showAppointmentDetailsFromCalendar(info.event);
        },
        select: function(info) {
            // Handle date/time selection for new appointments
            showNewAppointmentModalForTime(info.start, info.end);
        },
        eventDrop: function(info) {
            // Check for conflicts before allowing the drop
            const newStart = info.event.start;
            const newEnd = info.event.end;
            const appointmentId = info.event.id;
            
            // Get all other events on the same day
            const events = calendar.getEvents();
            const conflictingEvents = events.filter(event => {
                return event.id !== appointmentId && 
                       event.start.toDateString() === newStart.toDateString() &&
                       ((newStart < event.end && newEnd > event.start));
            });
            
            if (conflictingEvents.length > 0) {
                // Revert the event to its original position
                info.revert();
                return;
            }
            
            // If no conflicts, proceed with the update
            updateAppointmentTime(info.event);
        },
        eventResize: function(info) {
            // Check for conflicts before allowing the resize
            const newStart = info.event.start;
            const newEnd = info.event.end;
            const appointmentId = info.event.id;
            
            // Get all other events on the same day
            const events = calendar.getEvents();
            const conflictingEvents = events.filter(event => {
                return event.id !== appointmentId && 
                       event.start.toDateString() === newStart.toDateString() &&
                       ((newStart < event.end && newEnd > event.start));
            });
            
            if (conflictingEvents.length > 0) {
                // Revert the event to its original size
                info.revert();
                return;
            }
            
            // If no conflicts, proceed with the update
            updateAppointmentDuration(info.event);
        }
    });

    calendar.render();
}

function loadAppointmentsForCalendar(start, end, successCallback, failureCallback) {
    // Get both start and end dates to support month view
    const startDate = start.toISOString().split('T')[0];
    const endDate = end.toISOString().split('T')[0];
    
    // Use start and end parameters to support both week and month views
    fetch(`/dashboard/api/week-appointments/?start=${startDate}&end=${endDate}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const events = data.appointments.map(appointment => {
                    // Create Date objects that represent the exact time shown in the left column
                    // The time slots show local time, so we create dates in local time
                    const startDate = createDateFromComponents(appointment.appointment_date, appointment.appointment_time);
                    const endDate = addMinutesToDate(startDate, appointment.duration_minutes);
                    
                    return {
                        id: appointment.id,
                        title: appointment.patient_name,
                        start: startDate, // Date object in local time - matches left column times
                        end: endDate, // Date object in local time
                        backgroundColor: getEventColor(appointment.status),
                        borderColor: getEventColor(appointment.status),
                        extendedProps: {
                            patientId: appointment.patient_id,
                            patientName: appointment.patient_name,
                            doctorName: appointment.doctor_name,
                            appointmentType: appointment.appointment_type,
                            paymentType: appointment.payment_type,
                            status: appointment.status,
                            value: appointment.value,
                            reason: appointment.reason,
                            notes: appointment.notes,
                            location: appointment.location,
                            isFirstAppointment: !!appointment.is_first_appointment,
                            isBlock: false
                        }
                    };
                });
                // Add calendar blocks (unavailable periods)
                const blocks = data.blocks || [];
                const blockColor = '#6c757d';
                blocks.forEach(function(block) {
                    events.push({
                        id: block.id,
                        title: block.reason ? 'Bloqueio: ' + block.reason : 'Bloqueio',
                        start: block.start,
                        end: block.end,
                        backgroundColor: blockColor,
                        borderColor: blockColor,
                        editable: false,
                        extendedProps: {
                            isBlock: true,
                            reason: block.reason || ''
                        }
                    });
                });
                successCallback(events);
            } else {
                failureCallback(data.error);
            }
        })
        .catch(error => {
            failureCallback(error);
        });
}

/**
 * Create a Date object from date and time components
 * This creates the date in the browser's local timezone
 * The time will match exactly what's shown in the left column time slots
 */
function createDateFromComponents(dateStr, timeStr) {
    // Parse date: YYYY-MM-DD
    const [year, month, day] = dateStr.split('-').map(Number);
    
    // Parse time: HH:MM
    const [hours, minutes] = timeStr.split(':').map(Number);
    
    // Create Date object using local time components
    // new Date(year, month, day, hours, minutes) creates date in local timezone
    // This matches the time slots which also show local time
    return new Date(year, month - 1, day, hours || 0, minutes || 0, 0, 0);
}

/**
 * Add minutes to a Date object
 */
function addMinutesToDate(date, minutes) {
    return new Date(date.getTime() + (minutes * 60000));
}

// Status value to display name mapping (from models.py STATUS_CHOICES)
const statusValueToDisplay = {
    'scheduled': 'Agendada',
    'confirmed': 'Confirmada',
    'in_progress': 'Em Andamento',
    'completed': 'Concluída',
    'cancelled': 'Cancelada',
    'no_show': 'Não Compareceu',
    'rescheduled': 'Reagendada'
};

// Default colors (fallback if settings not loaded)
const defaultStatusColors = {
    'Agendada': '#ad0202',
    'Confirmada': '#007bff',
    'Em Andamento': '#ffc107',
    'Concluída': '#28a745',
    'Cancelada': '#dc3545',
    'Não Compareceu': '#6c757d',
    'Reagendada': '#17a2b8'
};

function getEventColor(status) {
    // Get status display name from status value
    const statusDisplay = statusValueToDisplay[status] || status;
    
    // Try to get color from settings if available
    if (typeof appointmentSettings !== 'undefined' && appointmentSettings && appointmentSettings.status_colors) {
        const customColor = appointmentSettings.status_colors[statusDisplay];
        if (customColor) {
            return customColor;
        }
    }
    
    // Fallback to default colors
    const defaultColor = defaultStatusColors[statusDisplay];
    if (defaultColor) {
        return defaultColor;
    }
    
    // Final fallback - should not reach here for valid statuses
    console.warn('Unknown status color for:', status, '->', statusDisplay);
    return '#6c757d';
}

// Store patient data for modal actions
let appointmentModalPatientId = null;
let appointmentModalPatientName = null;
let currentAppointmentId = null;

function showAppointmentDetailsFromCalendar(event) {
    const props = event.extendedProps;
    
    // Store appointment and patient data for actions
    currentAppointmentId = event.id;
    appointmentModalPatientId = props.patientId;
    appointmentModalPatientName = props.patientName;
    
    // Populate the appointment details modal
    const patientNameElement = document.getElementById('modal-patient-name-text');
    const patientBadgeElement = document.getElementById('modal-patient-badge');
    const prontuarioIconBtn = document.getElementById('modal-prontuario-icon-btn');
    const prescricaoIconBtn = document.getElementById('modal-prescricao-icon-btn');
    
    // Set patient name
    if (patientNameElement) {
        patientNameElement.textContent = props.patientName;
    }
    
    // Set payment badge
    if (patientBadgeElement) {
        if (props.paymentType === 'Particular') {
            patientBadgeElement.innerHTML = '<span class="badge bg-warning text-dark ms-1">$</span>';
        } else {
            patientBadgeElement.innerHTML = '';
        }
    }
    
    // Show/hide action icons based on whether patient ID is available
    if (prontuarioIconBtn && prescricaoIconBtn) {
        if (appointmentModalPatientId) {
            prontuarioIconBtn.style.display = 'inline-block';
            prescricaoIconBtn.style.display = 'inline-block';
        } else {
            prontuarioIconBtn.style.display = 'none';
            prescricaoIconBtn.style.display = 'none';
        }
    }
    document.getElementById('modal-doctor-name').textContent = props.doctorName;
    document.getElementById('modal-appointment-date').textContent = event.start.toLocaleDateString('pt-BR');
    document.getElementById('modal-appointment-time').textContent = event.start.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'});
    document.getElementById('modal-appointment-duration').textContent = Math.round((event.end - event.start) / (1000 * 60)) + ' minutos';
    document.getElementById('modal-appointment-type').textContent = props.appointmentType;
    document.getElementById('modal-payment-type').textContent = props.paymentType || '-';
    document.getElementById('modal-appointment-value').textContent = props.value ? `R$ ${props.value}` : '-';
    document.getElementById('modal-appointment-location').textContent = props.location || 'Consultório';
    document.getElementById('modal-appointment-reason').textContent = props.reason || 'Consulta médica';
    document.getElementById('modal-appointment-notes').textContent = props.notes || 'Nenhuma observação';
    
    // Update status badge and store current status
    const statusBadge = document.getElementById('modal-status-badge');
    statusBadge.textContent = getStatusDisplay(props.status);
    statusBadge.className = 'badge ' + getStatusBadgeClass(props.status);
    
    // Set up status select with current status and populate options
    const statusSelect = document.getElementById('modal-status-select');
    if (statusSelect) {
        // Populate status options from settings if available, otherwise use defaults
        if (typeof appointmentSettings !== 'undefined' && appointmentSettings && appointmentSettings.status_choices) {
            statusSelect.innerHTML = '';
            const statusValueMap = {
                'Agendada': 'scheduled',
                'Confirmada': 'confirmed',
                'Em Andamento': 'in_progress',
                'Concluída': 'completed',
                'Cancelada': 'cancelled',
                'Não Compareceu': 'no_show',
                'Reagendada': 'rescheduled'
            };
            
            const normalizedStatuses = appointmentSettings.status_choices.map(choice => {
                if (Array.isArray(choice) && choice.length >= 2) {
                    return { display: choice[1], value: choice[0] };
                }
                const displayName = String(choice);
                return { display: displayName, value: statusValueMap[displayName] || displayName.toLowerCase().replace(/\s+/g, '_') };
            });
            
            normalizedStatuses.forEach(status => {
                const option = document.createElement('option');
                option.value = status.value;
                option.textContent = status.display;
                statusSelect.appendChild(option);
            });
        }
        statusSelect.value = props.status;
    }
    
    // Reset status edit UI
    resetStatusEditUI();
    
    // Show/hide action buttons based on status
    const confirmBtn = document.getElementById('confirm-attendance-btn');
    const completeBtn = document.getElementById('complete-appointment-btn');
    const cancelBtn = document.getElementById('cancel-appointment-btn');
    
    // Reset button visibility
    confirmBtn.style.display = 'none';
    completeBtn.style.display = 'none';
    cancelBtn.style.display = 'none';
    
    // Show appropriate buttons based on status
    if (props.status === 'scheduled') {
        confirmBtn.style.display = 'inline-block';
        cancelBtn.style.display = 'inline-block';
    } else if (props.status === 'confirmed') {
        completeBtn.style.display = 'inline-block';
        cancelBtn.style.display = 'inline-block';
    } else if (props.status === 'completed') {
        // No action buttons for completed appointments
    } else if (props.status === 'cancelled') {
        // No action buttons for cancelled appointments
    }
    
    // Set up button click handlers
    confirmBtn.onclick = () => confirmAppointmentAttendance(event.id);
    completeBtn.onclick = () => completeAppointment(event.id);
    cancelBtn.onclick = () => cancelAppointment(event.id);
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('appointmentDetailsModal'));
    modal.show();
}

// Function to access patient prontuario from appointment modal
function accessProntuarioFromAppointmentModal() {
    if (appointmentModalPatientId && appointmentModalPatientName) {
        // Close the appointment modal first
        const modal = bootstrap.Modal.getInstance(document.getElementById('appointmentDetailsModal'));
        if (modal) {
            modal.hide();
        }
        
        // Then access prontuario using the existing function
        if (typeof accessPatientProntuario === 'function') {
            accessPatientProntuario(appointmentModalPatientId, appointmentModalPatientName);
        } else if (typeof selectPatient === 'function') {
            // Fallback: use selectPatient with pendingTabSwitch
            if (typeof window !== 'undefined') {
                window.pendingTabSwitch = 'prontuarios';
            }
            selectPatient(appointmentModalPatientName, appointmentModalPatientId);
        }
    }
}

// Function to access patient prescription from appointment modal
function accessPrescricaoFromAppointmentModal() {
    if (appointmentModalPatientId && appointmentModalPatientName) {
        // Close the appointment modal first
        const modal = bootstrap.Modal.getInstance(document.getElementById('appointmentDetailsModal'));
        if (modal) {
            modal.hide();
        }
        
        // Then access prescription using the existing function
        if (typeof accessPatientPrescription === 'function') {
            accessPatientPrescription(appointmentModalPatientId, appointmentModalPatientName);
        } else if (typeof selectPatient === 'function') {
            // Fallback: use selectPatient with pendingTabSwitch
            if (typeof window !== 'undefined') {
                window.pendingTabSwitch = 'prescricao';
            }
            selectPatient(appointmentModalPatientName, appointmentModalPatientId);
        }
    }
}

function getStatusDisplay(status) {
    const statusMap = {
        'scheduled': 'Agendada',
        'confirmed': 'Confirmada',
        'in_progress': 'Em Andamento',
        'completed': 'Concluída',
        'cancelled': 'Cancelada',
        'no_show': 'Não Compareceu',
        'rescheduled': 'Reagendada'
    };
    return statusMap[status] || status;
}

function getStatusBadgeClass(status) {
    const badgeClasses = {
        'scheduled': 'bg-info',
        'confirmed': 'bg-primary',
        'in_progress': 'bg-warning',
        'completed': 'bg-success',
        'cancelled': 'bg-danger',
        'no_show': 'bg-secondary',
        'rescheduled': 'bg-info'
    };
    return badgeClasses[status] || 'bg-secondary';
}

function confirmAppointmentAttendance(appointmentId) {
    fetch('/dashboard/api/appointments/confirm-attendance/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `appointment_id=${appointmentId}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('appointmentDetailsModal'));
            modal.hide();
            refreshCalendar();
            // Refresh agenda stats after confirming attendance
            if (typeof refreshAgendaStats === 'function') {
                refreshAgendaStats();
            }
        } else {
            showNotification('Erro ao confirmar presença: ' + data.error, 'error');
        }
    })
    .catch(error => {
        showNotification('Erro ao confirmar presença', 'error');
    });
}

function completeAppointment(appointmentId) {
    fetch('/dashboard/api/appointments/complete/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `appointment_id=${appointmentId}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('appointmentDetailsModal'));
            modal.hide();
            refreshCalendar();
            // Refresh agenda stats after completing appointment
            if (typeof refreshAgendaStats === 'function') {
                refreshAgendaStats();
            }
        } else {
            showNotification('Erro ao concluir consulta: ' + data.error, 'error');
        }
    })
    .catch(error => {
        showNotification('Erro ao concluir consulta', 'error');
    });
}

function cancelAppointment(appointmentId) {
    // Set appointment ID in the cancellation modal
    document.getElementById('cancel-appointment-id').value = appointmentId;
    
    // Load cancellation reasons from settings
    loadCancellationReasons();
    
    // Show cancellation modal
    const cancelModal = new bootstrap.Modal(document.getElementById('cancelAppointmentModal'));
    cancelModal.show();
}

function loadCancellationReasons() {
    const select = document.getElementById('cancellation-reason-select');
    if (!select) return;
    
    // Clear existing options except the first one
    select.innerHTML = '<option value="">Selecione um motivo...</option>';
    
    // Try to get reasons from settings if available
    if (typeof appointmentSettings !== 'undefined' && appointmentSettings && appointmentSettings.cancellation_reasons) {
        appointmentSettings.cancellation_reasons.forEach(reason => {
            const option = document.createElement('option');
            option.value = reason;
            option.textContent = reason;
            select.appendChild(option);
        });
    } else {
        // Fallback: fetch from API
        fetch('/dashboard/api/appointment-settings/')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.settings.cancellation_reasons) {
                    data.settings.cancellation_reasons.forEach(reason => {
                        const option = document.createElement('option');
                        option.value = reason;
                        option.textContent = reason;
                        select.appendChild(option);
                    });
                }
            })
            .catch(error => {
                console.error('Error loading cancellation reasons:', error);
            });
    }
}

// Handle cancellation form submission
document.addEventListener('DOMContentLoaded', function() {
    const cancelForm = document.getElementById('cancelAppointmentForm');
    const cancelModalEl = document.getElementById('cancelAppointmentModal');
    
    if (cancelForm) {
        cancelForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const appointmentId = document.getElementById('cancel-appointment-id').value;
            const reason = document.getElementById('cancellation-reason-select').value;
            const customReason = document.getElementById('cancellation-reason-custom').value.trim();
            
            if (!reason) {
                showNotification('Por favor, selecione um motivo de cancelamento', 'error');
                return;
            }
            
            // Combine selected reason with custom notes if provided
            let fullReason = reason;
            if (customReason) {
                fullReason = reason + ' - ' + customReason;
            }
            
            // Show loading state
            const submitBtn = cancelForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Cancelando...';
            submitBtn.disabled = true;
            
            fetch('/dashboard/api/appointments/cancel/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: `appointment_id=${appointmentId}&cancellation_reason=${encodeURIComponent(fullReason)}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Close both modals
                    const cancelModal = bootstrap.Modal.getInstance(cancelModalEl);
                    cancelModal.hide();
                    const detailsModal = bootstrap.Modal.getInstance(document.getElementById('appointmentDetailsModal'));
                    if (detailsModal) {
                        detailsModal.hide();
                    }
                    
                    showNotification(data.message, 'success');
                    refreshCalendar();
                    // Refresh agenda stats after cancelling appointment
                    if (typeof refreshAgendaStats === 'function') {
                        refreshAgendaStats();
                    }
                } else {
                    showNotification('Erro ao cancelar consulta: ' + data.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Erro ao cancelar consulta', 'error');
            })
            .finally(() => {
                // Restore button state
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            });
        });
    }
    
    // Reset form when modal is hidden
    if (cancelModalEl) {
        cancelModalEl.addEventListener('hidden.bs.modal', function() {
            if (cancelForm) {
                cancelForm.reset();
                document.getElementById('cancel-appointment-id').value = '';
            }
        });
    }
});

function showNewAppointmentModalForTime(start, end) {
    // Pre-fill the appointment modal with selected time
    const startDateObj = new Date(start);
    const startDate = startDateObj.getFullYear() + '-' + 
                     String(startDateObj.getMonth() + 1).padStart(2, '0') + '-' + 
                     String(startDateObj.getDate()).padStart(2, '0');
    const startTime = String(startDateObj.getHours()).padStart(2, '0') + ':' + 
                     String(startDateObj.getMinutes()).padStart(2, '0');
    
    // Set the date and time in the form
    document.getElementById('appointment_date').value = startDate;
    document.getElementById('appointment_time').value = startTime;
    
    // Calculate duration and set it
    const duration = Math.round((end - start) / (1000 * 60)); // in minutes
    document.getElementById('duration_minutes').value = duration;
    
    // Show the modal
    showNewAppointmentModal();
}

function updateAppointmentTime(event) {
    const appointmentId = event.id;
    
    // Get the local date and time properly
    const startDate = new Date(event.start);
    const newDate = startDate.getFullYear() + '-' + 
                   String(startDate.getMonth() + 1).padStart(2, '0') + '-' + 
                   String(startDate.getDate()).padStart(2, '0');
    const newTime = String(startDate.getHours()).padStart(2, '0') + ':' + 
                   String(startDate.getMinutes()).padStart(2, '0');
    
    // Send update to server
    fetch('/dashboard/api/appointments/update/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `appointment_id=${appointmentId}&appointment_date=${newDate}&appointment_time=${newTime}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Consulta atualizada com sucesso!', 'success');
            // Refresh agenda stats after updating appointment
            if (typeof refreshAgendaStats === 'function') {
                refreshAgendaStats();
            }
        } else {
            showNotification('Erro ao atualizar consulta: ' + data.error, 'error');
            // Revert the event position
            event.revert();
        }
    })
    .catch(error => {
        showNotification('Erro ao atualizar consulta', 'error');
        event.revert();
    });
}

function updateAppointmentDuration(event) {
    const appointmentId = event.id;
    const duration = Math.round((event.end - event.start) / (1000 * 60)); // in minutes
    
    // Send update to server
    fetch('/dashboard/api/appointments/update/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `appointment_id=${appointmentId}&duration_minutes=${duration}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Duração da consulta atualizada com sucesso!', 'success');
            // Refresh agenda stats after updating appointment duration
            if (typeof refreshAgendaStats === 'function') {
                refreshAgendaStats();
            }
        } else {
            showNotification('Erro ao atualizar duração: ' + data.error, 'error');
            // Revert the event
            event.revert();
        }
    })
    .catch(error => {
        showNotification('Erro ao atualizar duração', 'error');
        event.revert();
    });
}

function refreshCalendar() {
    if (calendar) {
        calendar.refetchEvents();
    }
}

// Function to edit appointment status
function editAppointmentStatus() {
    const statusBadge = document.getElementById('modal-status-badge');
    const editBtn = document.getElementById('edit-status-btn');
    const statusSelect = document.getElementById('modal-status-select');
    const saveBtn = document.getElementById('save-status-btn');
    const cancelBtn = document.getElementById('cancel-status-btn');
    
    if (statusBadge && editBtn && statusSelect && saveBtn && cancelBtn) {
        // Hide badge and edit button, show select and action buttons
        statusBadge.style.display = 'none';
        editBtn.style.display = 'none';
        statusSelect.style.display = 'inline-block';
        saveBtn.style.display = 'inline-block';
        cancelBtn.style.display = 'inline-block';
    }
}

// Function to cancel status edit
function cancelStatusEdit() {
    resetStatusEditUI();
}

// Function to reset status edit UI
function resetStatusEditUI() {
    const statusBadge = document.getElementById('modal-status-badge');
    const editBtn = document.getElementById('edit-status-btn');
    const statusSelect = document.getElementById('modal-status-select');
    const saveBtn = document.getElementById('save-status-btn');
    const cancelBtn = document.getElementById('cancel-status-btn');
    
    if (statusBadge && editBtn && statusSelect && saveBtn && cancelBtn) {
        statusBadge.style.display = 'inline-block';
        editBtn.style.display = 'inline-block';
        statusSelect.style.display = 'none';
        saveBtn.style.display = 'none';
        cancelBtn.style.display = 'none';
    }
}

// Function to save appointment status
function saveAppointmentStatus() {
    if (!currentAppointmentId) {
        showNotification('Erro: ID da consulta não encontrado', 'error');
        return;
    }
    
    const statusSelect = document.getElementById('modal-status-select');
    if (!statusSelect) {
        showNotification('Erro: Campo de status não encontrado', 'error');
        return;
    }
    
    const newStatus = statusSelect.value;
    if (!newStatus) {
        showNotification('Por favor, selecione um status', 'warning');
        return;
    }
    
    // Show loading state
    const saveBtn = document.getElementById('save-status-btn');
    const originalText = saveBtn ? saveBtn.innerHTML : '';
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }
    
    // Send update request
    fetch('/dashboard/api/appointments/update/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `appointment_id=${currentAppointmentId}&status=${newStatus}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update status badge
            const statusBadge = document.getElementById('modal-status-badge');
            if (statusBadge && data.appointment) {
                statusBadge.textContent = data.appointment.status_display || getStatusDisplay(newStatus);
                statusBadge.className = 'badge ' + getStatusBadgeClass(newStatus);
            }
            
            // Reset UI
            resetStatusEditUI();
            
            // Refresh calendar and stats
            if (typeof refreshCalendar === 'function') {
                refreshCalendar();
            }
            if (typeof refreshAgendaStats === 'function') {
                refreshAgendaStats();
            }
            
            showNotification('Status atualizado com sucesso!', 'success');
        } else {
            showNotification('Erro ao atualizar status: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('Error updating status:', error);
        showNotification('Erro ao atualizar status. Tente novamente.', 'error');
    })
    .finally(() => {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalText;
        }
    });
}

// Override the existing showNewAppointmentModal to refresh calendar after creation
const originalShowNewAppointmentModal = showNewAppointmentModal;
showNewAppointmentModal = function() {
    originalShowNewAppointmentModal();
    
    // Add event listener to refresh calendar when modal is closed
    const appointmentModal = document.getElementById('appointmentModal');
    if (appointmentModal) {
        appointmentModal.addEventListener('hidden.bs.modal', function() {
            refreshCalendar();
        });
    }
};
