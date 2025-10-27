let selectedPatient = null;
let selectedDoctorId = null;

// Doctor selection function for admins
function selectDoctor() {
    const selectElement = document.getElementById('doctor-selector');
    if (!selectElement) return;
    
    const doctorId = selectElement.value;
    selectedDoctorId = doctorId;
    
    if (doctorId) {
        // Call API to set selected doctor in session
        fetch('/dashboard/select-doctor/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: `doctor_id=${doctorId}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload the page to show the selected doctor's data
                window.location.reload();
            } else {
                console.error('Error selecting doctor:', data.error);
                alert('Erro ao selecionar médico: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Erro ao selecionar médico');
        });
    } else {
        // Clear doctor selection to show all doctors
        fetch('/dashboard/select-doctor/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: `doctor_id=`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload the page to show all doctors' data
                window.location.reload();
            } else {
                console.error('Error clearing doctor selection:', data.error);
                alert('Erro ao limpar seleção: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Erro ao limpar seleção');
        });
    }
}

// switchTab function is now handled by main.js

function switchChartView(view) {
    const monthlyChart = document.getElementById('monthly-chart');
    const weeklyChart = document.getElementById('weekly-chart');
    const chartTitle = document.querySelector('.card-header h5');
    const monthlyBtn = document.getElementById('monthly-chart-btn');
    const weeklyBtn = document.getElementById('weekly-chart-btn');
    
    if (view === 'weekly') {
        // Show weekly chart, hide monthly
        monthlyChart.style.display = 'none';
        weeklyChart.style.display = 'block';
        chartTitle.textContent = 'Agenda Semanal (%)';
        
        // Update button states
        monthlyBtn.classList.remove('active');
        weeklyBtn.classList.add('active');
    } else {
        // Show monthly chart, hide weekly
        monthlyChart.style.display = 'block';
        weeklyChart.style.display = 'none';
        chartTitle.textContent = 'Agenda Mensal (%)';
        
        // Update button states
        weeklyBtn.classList.remove('active');
        monthlyBtn.classList.add('active');
    }
}

function selectPatient(patientName, patientId) {
    selectedPatient = {
        name: patientName,
        id: patientId
    };
    
    // Update the persistent patient selection header
    updatePatientSelectionHeader(patientName, 'selected');
    
    // Enable all other tabs
    const disabledButtons = document.querySelectorAll('.btn-group .btn.disabled');
    disabledButtons.forEach(btn => {
        btn.classList.remove('disabled');
        btn.disabled = false;
    });
    
    // Update patient info in all tabs
    updatePatientInfo(patientName);
    
    // Load patient-specific data for prontuarios tab
    loadPatientProntuarios(patientId);
    
    // Show success message
    showNotification(`Paciente ${patientName} selecionado. Agora você pode acessar os outros módulos.`, 'success');
    
    // Update the page title to show selected patient
    document.title = `Dashboard Médico - ${patientName}`;
}

function updatePatientSelectionHeader(patientName, status) {
    const patientNameElement = document.getElementById('selected-patient-name');
    const patientInfoElement = document.getElementById('selected-patient-info');
    const patientStatusBadge = document.getElementById('patient-status-badge');
    const clearPatientBtn = document.getElementById('clear-patient-btn');
    const patientHeader = document.getElementById('patient-selection-header');
    
    if (status === 'selected') {
        patientNameElement.textContent = patientName;
        patientInfoElement.textContent = 'Paciente selecionado - Acesso liberado a todos os módulos';
        patientStatusBadge.textContent = 'Paciente Selecionado';
        patientStatusBadge.className = 'badge bg-success me-2';
        clearPatientBtn.style.display = 'inline-block';
        patientHeader.className = 'card border-success shadow-sm';
    } else {
        patientNameElement.textContent = 'Nenhum paciente selecionado';
        patientInfoElement.textContent = 'Selecione um paciente na agenda para acessar os módulos';
        patientStatusBadge.textContent = 'Aguardando seleção';
        patientStatusBadge.className = 'badge bg-secondary me-2';
        clearPatientBtn.style.display = 'none';
        patientHeader.className = 'card border-0 shadow-sm';
    }
}

function clearPatientSelection() {
    selectedPatient = null;
    
    // Update the persistent patient selection header
    updatePatientSelectionHeader('', 'none');
    
    // Disable all other tabs except agenda and indicators
    const allButtons = document.querySelectorAll('.btn-group .btn');
    allButtons.forEach((btn, index) => {
        if (index > 0) { // Skip the first button (Agenda)
            // Keep indicators button enabled (index 1)
            if (index !== 1) {
                btn.classList.add('disabled');
                btn.disabled = true;
            }
        }
    });
    
    // Switch back to agenda tab
    switchTab('agenda');
    
    // Show info message
    showNotification('Seleção de paciente limpa. Selecione um paciente na agenda para continuar.', 'info');
    
    // Reset page title
    document.title = 'Dashboard Médico - MedSaaS';
    
    // Clear prescription form and update button states
    updatePrescriptionButtonStates();
    
    // Clear prescriptions list
    const prescriptionsList = document.getElementById('prescriptions-list');
    if (prescriptionsList) {
        prescriptionsList.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-prescription-bottle-alt fa-3x mb-3"></i>
                <p>Nenhuma prescrição encontrada para este paciente.</p>
            </div>
        `;
    }
}

function updatePatientInfo(patientName) {
    // Update patient info in prontuários tab
    const prontuariosInfo = document.getElementById('patient-info-prontuarios');
    if (prontuariosInfo) {
        prontuariosInfo.textContent = `Visualizando prontuário de: ${patientName}`;
    }
    
    
    
    // Update patient info in prescrição tab
    const prescricaoInfo = document.getElementById('patient-info-prescricao');
    if (prescricaoInfo) {
        prescricaoInfo.textContent = patientName;
    }
    
    // Load prescriptions for the selected patient
    loadPatientPrescriptions();
    
    // Update prescription button states
    updatePrescriptionButtonStates();
}

function loadPatientProntuarios(patientId, offset = 0) {
    // Load patient-specific medical records for prontuarios tab
    if (patientId) {
        // Make AJAX request to get patient-specific records
        const url = `/dashboard/prontuarios/?patient_id=${patientId}&offset=${offset}&limit=2`;
        fetch(url)
            .then(response => response.text())
            .then(html => {
                // Update the prontuarios tab content
                const prontuariosTab = document.getElementById('prontuarios-tab');
                if (prontuariosTab) {
                    // Parse the response and extract the prontuarios tab content
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const newProntuariosTab = doc.getElementById('prontuarios-tab');
                    if (newProntuariosTab) {
                        prontuariosTab.innerHTML = newProntuariosTab.innerHTML;
                        // Re-attach event listeners
                        attachProntuarioEventListeners();
                    }
                }
            })
            .catch(error => {
                console.error('Error loading patient prontuarios:', error);
            });
    }
}

function loadOlderRecords(offset) {
    const patientId = document.getElementById('patient-id');
    if (patientId) {
        // Show loading state
        const loadBtn = event.target;
        const originalText = loadBtn.innerHTML;
        loadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Carregando...';
        loadBtn.disabled = true;
        
        // Load older records and append them
        loadOlderRecordsAjax(patientId.value, offset, loadBtn, originalText);
    }
}

function loadOlderRecordsFromButton(button) {
    const patientId = document.getElementById('patient-id');
    const offset = button.getAttribute('data-offset');
    if (patientId && offset) {
        // Show loading state
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Carregando...';
        button.disabled = true;
        
        // Load older records and append them
        loadOlderRecordsAjax(patientId.value, offset, button, originalText);
    }
}

function loadOlderRecordsAjax(patientId, offset, loadBtn, originalText) {
    const url = `/dashboard/prontuarios/?patient_id=${patientId}&offset=${offset}&limit=3`;
    
    fetch(url)
        .then(response => response.text())
        .then(html => {
            // Parse the response to extract only the new records
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newRecordsContent = doc.getElementById('records-content');
            
            if (newRecordsContent) {
                const currentRecordsContent = document.getElementById('records-content');
                
                // Find and remove the existing load more button
                const existingLoadMoreContainer = currentRecordsContent.querySelector('.text-center.mt-3');
                if (existingLoadMoreContainer) {
                    existingLoadMoreContainer.remove();
                }
                
                // Extract new records and new load more button from response
                const newRecords = newRecordsContent.querySelectorAll('.timeline-item');
                const newLoadMoreContainer = newRecordsContent.querySelector('.text-center.mt-3');
                
                // Append all new records at the end
                newRecords.forEach(record => {
                    currentRecordsContent.appendChild(record);
                });
                
                // Add the new load more button or completion message at the very end
                if (newLoadMoreContainer) {
                    currentRecordsContent.appendChild(newLoadMoreContainer);
                } else {
                    // If no more records, show completion message
                    const completionDiv = document.createElement('div');
                    completionDiv.className = 'text-center mt-3';
                    completionDiv.innerHTML = `
                        <small class="text-muted">
                            <i class="fas fa-check-circle me-1"></i>
                            Todos os registros foram carregados
                        </small>
                    `;
                    currentRecordsContent.appendChild(completionDiv);
                }
            }
        })
        .catch(error => {
            console.error('Error loading older records:', error);
            showNotification('Erro ao carregar registros anteriores.', 'error');
        })
        .finally(() => {
            // Restore button state
            loadBtn.innerHTML = originalText;
            loadBtn.disabled = false;
        });
}

function attachProntuarioEventListeners() {
    // Attach form submit event listener
    const form = document.getElementById('new-record-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            saveNewRecord();
        });
    }
}

function saveNewRecord() {
    const patientId = document.getElementById('patient-id');
    const content = document.getElementById('new-record-content');
    
    if (!patientId || !content) {
        showNotification('Erro: Dados do paciente não encontrados.', 'error');
        return;
    }
    
    const contentText = content.value.trim();
    if (!contentText) {
        showNotification('Por favor, digite o conteúdo da entrada.', 'warning');
        content.focus();
        return;
    }
    
    // Show loading state
    const submitBtn = document.querySelector('#new-record-form button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Salvando...';
    submitBtn.disabled = true;
    
    // Prepare form data
    const formData = new FormData();
    formData.append('patient_id', patientId.value);
    formData.append('content', contentText);
    
    // Make AJAX request
    fetch('/dashboard/add-medical-record/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Clear the form
            content.value = '';
            
            // Reload the prontuarios tab to show the new record
            loadPatientProntuarios(patientId.value);
            
            showNotification('Entrada salva com sucesso!', 'success');
        } else {
            showNotification('Erro ao salvar: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('Error saving record:', error);
        showNotification('Erro ao salvar a entrada. Tente novamente.', 'error');
    })
    .finally(() => {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

function clearNewRecord() {
    const content = document.getElementById('new-record-content');
    if (content) {
        content.value = '';
        content.focus();
    }
}

function printProntuario() {
    const patientName = selectedPatient ? selectedPatient.name : 'Paciente';
    const printWindow = window.open('', '_blank');
    
    // Get the records content
    const recordsContent = document.getElementById('records-content');
    if (!recordsContent) {
        showNotification('Nenhum conteúdo para imprimir.', 'warning');
        return;
    }
    
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Prontuário - ${patientName}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #333; padding-bottom: 10px; }
                .record-date-group { margin-bottom: 20px; }
                .date-header { color: #007bff; font-weight: bold; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-bottom: 10px; }
                .record-entry { margin-bottom: 15px; padding: 10px; border-left: 3px solid #007bff; background-color: #f8f9fa; }
                .record-time { font-size: 12px; color: #666; }
                .record-content { margin-top: 5px; }
                @media print { body { margin: 0; } }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Prontuário Médico</h1>
                <h2>${patientName}</h2>
                <p>Data de impressão: ${new Date().toLocaleDateString('pt-BR')}</p>
            </div>
            ${recordsContent.innerHTML}
        </body>
        </html>
    `);
    
    printWindow.document.close();
    printWindow.print();
}

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Global variable to store current record data for printing
let currentRecordData = null;

function showRecordPopup(recordId, date, time, doctor, content) {
    // Store record data for printing
    currentRecordData = {
        id: recordId,
        date: date,
        time: time,
        doctor: doctor,
        content: content
    };
    
    // Populate modal with record data
    document.getElementById('popup-date').textContent = date;
    document.getElementById('popup-time').textContent = time;
    document.getElementById('popup-doctor').textContent = doctor;
    document.getElementById('popup-content').textContent = content;
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('recordPopupModal'));
    modal.show();
}

function showRecordPopupFromTimeline(element) {
    // Extract data from timeline element
    const recordId = element.getAttribute('data-record-id');
    const date = element.getAttribute('data-record-date');
    const time = element.getAttribute('data-record-time');
    const doctor = element.getAttribute('data-record-doctor');
    const content = element.getAttribute('data-record-content');
    
    // Call the existing function
    showRecordPopup(recordId, date, time, doctor, content);
}

function printRecord() {
    if (!currentRecordData) {
        showNotification('Nenhum registro selecionado para impressão.', 'warning');
        return;
    }
    
    const printWindow = window.open('', '_blank');
    const patientName = selectedPatient ? selectedPatient.name : 'Paciente';
    
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Registro Médico - ${patientName}</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 20px; 
                    line-height: 1.6;
                }
                .header { 
                    text-align: center; 
                    margin-bottom: 30px; 
                    border-bottom: 2px solid #333; 
                    padding-bottom: 10px; 
                }
                .record-info {
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }
                .record-content {
                    background-color: #fff;
                    border: 1px solid #ddd;
                    padding: 20px;
                    border-radius: 5px;
                    white-space: pre-wrap;
                    font-family: 'Courier New', monospace;
                    font-size: 14px;
                }
                @media print { 
                    body { margin: 0; } 
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Registro Médico</h1>
                <h2>${patientName}</h2>
                <p>Data de impressão: ${new Date().toLocaleDateString('pt-BR')}</p>
            </div>
            
            <div class="record-info">
                <p><strong>Data:</strong> ${currentRecordData.date}</p>
                <p><strong>Hora:</strong> ${currentRecordData.time}</p>
                <p><strong>Médico:</strong> ${currentRecordData.doctor}</p>
            </div>
            
            <div class="record-content">
                ${currentRecordData.content}
            </div>
        </body>
        </html>
    `);
    
    printWindow.document.close();
    printWindow.print();
}

function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}


// Set default active tab to 'agenda'
document.addEventListener('DOMContentLoaded', function() {
    // Set the first button (Agenda) as active by default
    const firstButton = document.querySelector('.btn-group .btn');
    if (firstButton) {
        firstButton.classList.remove('btn-outline-primary');
        firstButton.classList.add('btn-primary');
    }
    
    // Initialize patient selection header
    updatePatientSelectionHeader('', 'none');
    
    // Attach prontuario event listeners
    attachProntuarioEventListeners();
    
    // Show initial message
    showNotification('Selecione um paciente na agenda para acessar os outros módulos.', 'info');
    
    // Load patients and doctors for appointment modal
    loadPatientsAndDoctors();
    
    // Initialize prescription form
    initializePrescriptionForm();
    
    // Refresh agenda stats on page load
    refreshAgendaStats();
});

// Appointment Modal Functions
function showNewAppointmentModal() {
    const modal = new bootstrap.Modal(document.getElementById('newAppointmentModal'));
    
    // Set default date to today (using local date to avoid timezone issues)
    const today = new Date();
    const localDate = today.getFullYear() + '-' + 
                     String(today.getMonth() + 1).padStart(2, '0') + '-' + 
                     String(today.getDate()).padStart(2, '0');
    document.getElementById('appointment-date').value = localDate;
    
    // Set default time to next hour
    const nextHour = new Date();
    nextHour.setHours(nextHour.getHours() + 1, 0, 0, 0);
    document.getElementById('appointment-time').value = nextHour.toTimeString().slice(0, 5);
    
    // Ensure patient search is set up when modal is shown
    if (window.allPatients && window.allPatients.length > 0) {
        setupPatientSearch();
    } else {
        // Load patients if not already loaded
        loadPatientsAndDoctors();
    }
    
    // Also set up patient search when modal is fully shown
    const modalElement = document.getElementById('newAppointmentModal');
    modalElement.addEventListener('shown.bs.modal', function() {
        setupPatientSearch();
    }, { once: true });
    
    modal.show();
}

function showNewPatientModal() {
    // Close appointment modal first
    const appointmentModal = bootstrap.Modal.getInstance(document.getElementById('newAppointmentModal'));
    if (appointmentModal) {
        appointmentModal.hide();
    }
    
    // Show patient modal
    const modal = new bootstrap.Modal(document.getElementById('newPatientModal'));
    modal.show();
}

function loadPatientsAndDoctors() {
    // Load patients
    fetch('/dashboard/api/patients/')
        .then(response => response.json())
        .then(data => {
            console.log('Patients loaded:', data);
            window.allPatients = data.success ? data.patients : [];
            setupPatientSearch();
        })
        .catch(error => {
            console.error('Error loading patients:', error);
            window.allPatients = [];
        });
    
    // Doctor is automatically set to current user, no need to load doctors
}

function setupPatientSearch() {
    const searchInput = document.getElementById('appointment-patient-search');
    const dropdown = document.getElementById('appointment-patient-dropdown');
    const hiddenInput = document.getElementById('appointment-patient');
    
    console.log('Setting up patient search:', {
        searchInput: !!searchInput,
        dropdown: !!dropdown,
        hiddenInput: !!hiddenInput,
        patientsCount: window.allPatients ? window.allPatients.length : 0
    });
    
    if (!searchInput || !dropdown || !hiddenInput) {
        console.log('Patient search elements not found, will retry when modal opens');
        return;
    }
    
    // Show all patients initially
    showPatients(window.allPatients);
    
    // Handle search input
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const filteredPatients = window.allPatients.filter(patient => 
            `${patient.first_name} ${patient.last_name}`.toLowerCase().includes(searchTerm)
        );
        showPatients(filteredPatients);
    });
    
    // Handle click outside to close dropdown
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
    
    // Handle focus to show dropdown
    searchInput.addEventListener('focus', function() {
        dropdown.style.display = 'block';
    });
}

function showPatients(patients) {
    const dropdown = document.getElementById('appointment-patient-dropdown');
    const hiddenInput = document.getElementById('appointment-patient');
    const searchInput = document.getElementById('appointment-patient-search');
    
    dropdown.innerHTML = '';
    
    if (patients.length === 0) {
        dropdown.innerHTML = '<div class="dropdown-item text-muted">Nenhum paciente encontrado</div>';
    } else {
        patients.forEach(patient => {
            const item = document.createElement('div');
            item.className = 'dropdown-item';
            item.style.cursor = 'pointer';
            item.textContent = `${patient.first_name} ${patient.last_name}`;
            
            item.addEventListener('click', function() {
                console.log('Clicking patient:', patient);
                console.log('Before setting - hiddenInput:', hiddenInput.value, 'searchInput:', searchInput.value);
                
                hiddenInput.value = patient.id;
                searchInput.value = `${patient.first_name} ${patient.last_name}`;
                
                console.log('After setting - hiddenInput:', hiddenInput.value, 'searchInput:', searchInput.value);
                
                // Force update
                searchInput.dispatchEvent(new Event('input', { bubbles: true }));
                
                dropdown.style.display = 'none';
                
                console.log('Final - hiddenInput:', hiddenInput.value, 'searchInput:', searchInput.value);
            });
            
            dropdown.appendChild(item);
        });
    }
    
    dropdown.style.display = 'block';
}

// Handle new appointment form submission
document.addEventListener('DOMContentLoaded', function() {
    const appointmentForm = document.getElementById('newAppointmentForm');
    if (appointmentForm) {
        appointmentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitNewAppointment();
        });
    }
    
    const patientForm = document.getElementById('newPatientForm');
    if (patientForm) {
        patientForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitNewPatient();
        });
    }
    
    // Confirm attendance button is handled by fullcalendar.js when showing appointment details
    
    // Cancel appointment button is handled by fullcalendar.js when showing appointment details
});

function submitNewAppointment() {
    const form = document.getElementById('newAppointmentForm');
    const formData = new FormData(form);
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Agendando...';
    submitBtn.disabled = true;
    
    fetch('/dashboard/api/appointments/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('newAppointmentModal'));
            modal.hide();
            
            // Reset form
            form.reset();
            
            // Show success message
            showNotification('Consulta agendada com sucesso!', 'success');
            
            // Refresh calendar and stats instead of reloading the page
            if (typeof refreshCalendar === 'function') {
                refreshCalendar();
            }
            if (typeof refreshAgendaStats === 'function') {
                refreshAgendaStats();
            }
        } else {
            showNotification('Erro ao agendar consulta: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('Error creating appointment:', error);
        showNotification('Erro ao agendar consulta. Tente novamente.', 'error');
    })
    .finally(() => {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

function submitNewPatient() {
    const form = document.getElementById('newPatientForm');
    const formData = new FormData(form);
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Salvando...';
    submitBtn.disabled = true;
    
    fetch('/dashboard/api/patients/create/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('newPatientModal'));
            modal.hide();
            
            // Reset form
            form.reset();
            
            // Show success message
            showNotification('Paciente criado com sucesso!', 'success');
            
            // Reload patients list
            loadPatientsAndDoctors();
            
            // Reopen appointment modal with new patient selected
            setTimeout(() => {
                showNewAppointmentModal();
                // Find the new patient and set it in the search
                const newPatient = window.allPatients.find(p => p.id == data.patient_id);
                if (newPatient) {
                    document.getElementById('appointment-patient').value = data.patient_id;
                    document.getElementById('patient-search').value = `${newPatient.first_name} ${newPatient.last_name}`;
                }
            }, 500);
        } else {
            showNotification('Erro ao criar paciente: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('Error creating patient:', error);
        showNotification('Erro ao criar paciente. Tente novamente.', 'error');
    })
    .finally(() => {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

// Patient Selection Popup Functions
function showPatientSelectionModal() {
    const modal = new bootstrap.Modal(document.getElementById('patientSelectionModal'));
    modal.show();
    
    // Load all patients when modal opens
    loadAllPatientsForPopup();
    
    // Setup search functionality
    setupPatientPopupSearch();
}

function loadAllPatientsForPopup() {
    const loadingDiv = document.getElementById('patient-search-loading');
    const patientList = document.getElementById('patient-list');
    const noResultsDiv = document.getElementById('no-patients-found');
    
    // Show loading state
    loadingDiv.style.display = 'flex';
    patientList.innerHTML = '';
    noResultsDiv.style.display = 'none';
    
    // Load patients from API
    fetch('/dashboard/api/patients/')
        .then(response => response.json())
        .then(data => {
            loadingDiv.style.display = 'none';
            
            if (data.success && data.patients.length > 0) {
                displayPatientsInPopup(data.patients);
            } else {
                noResultsDiv.style.display = 'flex';
            }
        })
        .catch(error => {
            console.error('Error loading patients:', error);
            loadingDiv.style.display = 'none';
            noResultsDiv.style.display = 'flex';
        });
}

function displayPatientsInPopup(patients) {
    const patientList = document.getElementById('patient-list');
    const noResultsDiv = document.getElementById('no-patients-found');
    
    patientList.innerHTML = '';
    
    if (patients.length === 0) {
        noResultsDiv.style.display = 'flex';
        return;
    }
    
    noResultsDiv.style.display = 'none';
    
    patients.forEach(patient => {
        const patientCard = createPatientCard(patient);
        patientList.appendChild(patientCard);
    });
}

function createPatientCard(patient) {
    const col = document.createElement('div');
    col.className = 'col-12';
    
    // Get initials for avatar
    const initials = `${patient.first_name.charAt(0)}${patient.last_name.charAt(0)}`.toUpperCase();
    
    // Escape special characters in patient name for HTML
    const escapedName = patient.full_name.replace(/'/g, "\\'").replace(/"/g, '\\"');
    
    col.innerHTML = `
        <div class="patient-card" onclick="selectPatientFromPopup('${patient.id}', '${escapedName}')">
            <div class="patient-info">
                <div class="patient-avatar">
                    ${initials}
                </div>
                <div class="patient-name">${patient.full_name}</div>
            </div>
            <div class="patient-actions">
                <button class="btn btn-select-patient" onclick="event.stopPropagation(); selectPatientFromPopup('${patient.id}', '${escapedName}')">
                    Selecionar
                </button>
            </div>
        </div>
    `;
    
    return col;
}

function selectPatientFromPopup(patientId, patientName) {
    // Close the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('patientSelectionModal'));
    modal.hide();
    
    // Set patient in appointment form if it exists
    const appointmentPatientInput = document.getElementById('appointment-patient');
    const appointmentPatientSearch = document.getElementById('appointment-patient-search');
    
    if (appointmentPatientInput && appointmentPatientSearch) {
        appointmentPatientInput.value = patientId;
        appointmentPatientSearch.value = patientName;
        appointmentPatientSearch.removeAttribute('placeholder');
        console.log('Set patient in appointment form:', {
            hidden: patientId,
            visible: patientName
        });
    }
    
    // Use the existing selectPatient function for main dashboard
    selectPatient(patientName, patientId);
}

function setupPatientPopupSearch() {
    const searchInput = document.getElementById('patient-popup-search');
    if (!searchInput) return;
    
    let searchTimeout;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.trim();
        
        // Clear previous timeout
        clearTimeout(searchTimeout);
        
        // Show loading if search term is long enough
        if (searchTerm.length >= 2) {
            const loadingDiv = document.getElementById('patient-search-loading');
            const patientList = document.getElementById('patient-list');
            const noResultsDiv = document.getElementById('no-patients-found');
            
            loadingDiv.style.display = 'flex';
            patientList.innerHTML = '';
            noResultsDiv.style.display = 'none';
            
            // Debounce search
            searchTimeout = setTimeout(() => {
                searchPatientsInPopup(searchTerm);
            }, 300);
        } else if (searchTerm.length === 0) {
            // Show all patients if search is empty
            loadAllPatientsForPopup();
        }
    });
}

function searchPatientsInPopup(searchTerm) {
    const loadingDiv = document.getElementById('patient-search-loading');
    const patientList = document.getElementById('patient-list');
    const noResultsDiv = document.getElementById('no-patients-found');
    
    // Load all patients and filter them
    fetch('/dashboard/api/patients/')
        .then(response => response.json())
        .then(data => {
            loadingDiv.style.display = 'none';
            
            if (data.success && data.patients.length > 0) {
                // Filter patients based on search term
                const filteredPatients = data.patients.filter(patient => {
                    const fullName = `${patient.first_name} ${patient.last_name}`.toLowerCase();
                    const email = (patient.email || '').toLowerCase();
                    const phone = (patient.phone || '').toLowerCase();
                    const searchLower = searchTerm.toLowerCase();
                    
                    return fullName.includes(searchLower) || 
                           email.includes(searchLower) || 
                           phone.includes(searchLower);
                });
                
                displayPatientsInPopup(filteredPatients);
            } else {
                noResultsDiv.style.display = 'flex';
            }
        })
        .catch(error => {
            console.error('Error searching patients:', error);
            loadingDiv.style.display = 'none';
            noResultsDiv.style.display = 'flex';
        });
}

// Next Appointment Details Function
function showNextAppointmentDetails() {
    const nextAppointmentText = document.getElementById('proxima-consulta').textContent;
    
    if (nextAppointmentText === 'N/A' || nextAppointmentText === '--:--') {
        showNotification('Nenhuma consulta próxima agendada.', 'info');
        return;
    }
    
    // Get the next appointment from the server
    fetch('/dashboard/api/next-appointment/')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.appointment) {
                // Show the appointment details in a modal or notification
                const appointment = data.appointment;
                const message = `Próxima consulta: ${appointment.patient_name} em ${appointment.appointment_date} às ${appointment.appointment_time}`;
                showNotification(message, 'info');
                
                // Optionally, you could show a detailed modal here
                // showAppointmentDetailsModal(appointment);
            } else {
                showNotification('Não foi possível carregar os detalhes da próxima consulta.', 'error');
            }
        })
        .catch(error => {
            console.error('Error fetching next appointment:', error);
            showNotification('Erro ao carregar próxima consulta.', 'error');
        });
}

// Function to refresh agenda stats
function refreshAgendaStats() {
    console.log('Refreshing agenda stats');
    fetch('/dashboard/api/agenda-stats/')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update the stats cards - look specifically in the agenda tab
                const agendaTab = document.getElementById('agenda-tab');
                if (agendaTab) {
                    const consultasHojeElement = agendaTab.querySelector('.stats-card-primary .stats-number');
                    const pacientesAtendidosElement = agendaTab.querySelector('.stats-card-success .stats-number');
                    const consultasPendentesElement = agendaTab.querySelector('.stats-card-info .stats-number');
                    const proximaConsultaElement = agendaTab.querySelector('.stats-card-warning .stats-number');
                    
                    if (consultasHojeElement) {
                        consultasHojeElement.textContent = data.stats.consultas_hoje;
                    }
                    if (pacientesAtendidosElement) {
                        pacientesAtendidosElement.textContent = data.stats.pacientes_atendidos;
                    }
                    if (consultasPendentesElement) {
                        consultasPendentesElement.textContent = data.stats.consultas_pendentes;
                    }
                    if (proximaConsultaElement) {
                        proximaConsultaElement.textContent = data.stats.proxima_consulta;
                    }
                }
            }
        })
        .catch(error => {
            // Silent fail
        });
}

// Prescription functionality
let currentPrescriptionId = null;

function initializePrescriptionForm() {
    // Set default date to today
    const today = new Date();
    const localDate = today.getFullYear() + '-' + 
                     String(today.getMonth() + 1).padStart(2, '0') + '-' + 
                     String(today.getDate()).padStart(2, '0');
    document.getElementById('prescription-date').value = localDate;
    
    // Add event listeners
    document.getElementById('add-medication').addEventListener('click', addMedicationItem);
    document.getElementById('save-prescription-btn').addEventListener('click', savePrescription);
    document.getElementById('send-email-btn').addEventListener('click', sendPrescriptionEmail);
    document.getElementById('send-whatsapp-btn').addEventListener('click', sendPrescriptionWhatsApp);
    document.getElementById('print-prescription-btn').addEventListener('click', printPrescription);
    
    // Add event listeners for remove buttons
    document.querySelectorAll('.remove-medication').forEach(btn => {
        btn.addEventListener('click', removeMedicationItem);
    });
    
    // Update button states based on patient selection
    updatePrescriptionButtonStates();
}

function addMedicationItem() {
    const medicationItems = document.getElementById('medication-items');
    const itemCount = medicationItems.children.length;
    
    const newItem = document.createElement('div');
    newItem.className = 'medication-item mb-4 p-3 border rounded bg-light';
    newItem.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <label class="form-label fw-bold">Medicamento</label>
                <input type="text" class="form-control" name="medication_name[]" placeholder="Nome do medicamento">
            </div>
            <div class="col-md-3">
                <label class="form-label fw-bold">Quantidade</label>
                <input type="text" class="form-control" name="quantity[]" placeholder="Ex: 30 comprimidos">
            </div>
            <div class="col-md-3 d-flex align-items-end">
                <button type="button" class="btn btn-outline-danger btn-sm remove-medication">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
        <div class="row mt-2">
            <div class="col-12">
                <label class="form-label fw-bold">Posologia</label>
                <textarea class="form-control" name="dosage[]" rows="2" placeholder="Ex: 1 comprimido de 8/8 horas"></textarea>
            </div>
        </div>
    `;
    
    medicationItems.appendChild(newItem);
    
    // Add event listener to the new remove button
    newItem.querySelector('.remove-medication').addEventListener('click', removeMedicationItem);
    
    // Show remove buttons if there are more than 1 items
    updateRemoveButtons();
}

function removeMedicationItem(event) {
    const medicationItems = document.getElementById('medication-items');
    if (medicationItems.children.length > 1) {
        event.target.closest('.medication-item').remove();
        updateRemoveButtons();
    }
}

function updateRemoveButtons() {
    const medicationItems = document.getElementById('medication-items');
    const removeButtons = medicationItems.querySelectorAll('.remove-medication');
    
    removeButtons.forEach(btn => {
        btn.style.display = medicationItems.children.length > 1 ? 'block' : 'none';
    });
}

function updatePrescriptionButtonStates() {
    const hasPatient = selectedPatient !== null;
    const saveBtn = document.getElementById('save-prescription-btn');
    const emailBtn = document.getElementById('send-email-btn');
    const whatsappBtn = document.getElementById('send-whatsapp-btn');
    const printBtn = document.getElementById('print-prescription-btn');
    
    if (hasPatient) {
        saveBtn.disabled = false;
        emailBtn.disabled = false;
        whatsappBtn.disabled = false;
        printBtn.disabled = false;
    } else {
        saveBtn.disabled = true;
        emailBtn.disabled = true;
        whatsappBtn.disabled = true;
        printBtn.disabled = true;
    }
}

function savePrescription() {
    if (!selectedPatient) {
        showNotification('Por favor, selecione um paciente primeiro.', 'warning');
        return;
    }
    
    const form = document.getElementById('prescription-form');
    const formData = new FormData(form);
    
    // Add patient ID
    formData.append('patient_id', selectedPatient.id);
    
    // Validate form
    const prescriptionDate = formData.get('prescription_date');
    const medicationNames = formData.getAll('medication_name[]');
    
    if (!prescriptionDate) {
        showNotification('Por favor, selecione uma data para a prescrição.', 'warning');
        return;
    }
    
    if (!medicationNames.some(name => name.trim())) {
        showNotification('Por favor, adicione pelo menos um medicamento.', 'warning');
        return;
    }
    
    // Show loading state
    const saveBtn = document.getElementById('save-prescription-btn');
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>SALVANDO...';
    saveBtn.disabled = true;
    
    // Make AJAX request
    fetch('/dashboard/api/prescriptions/create/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentPrescriptionId = data.prescription_id;
            showNotification(data.message, 'success');
            
            // Clear form
            form.reset();
            
            // Set default date to today
            const today = new Date();
            const localDate = today.getFullYear() + '-' + 
                             String(today.getMonth() + 1).padStart(2, '0') + '-' + 
                             String(today.getDate()).padStart(2, '0');
            document.getElementById('prescription-date').value = localDate;
            
            // Reset to 2 medication items
            resetMedicationItems();
            
            // Load prescriptions for the patient
            loadPatientPrescriptions();
        } else {
            showNotification('Erro ao salvar prescrição: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('Error saving prescription:', error);
        showNotification('Erro ao salvar prescrição. Tente novamente.', 'error');
    })
    .finally(() => {
        // Restore button state
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    });
}

function resetMedicationItems() {
    const medicationItems = document.getElementById('medication-items');
    
    // Remove all items except the first two
    while (medicationItems.children.length > 2) {
        medicationItems.removeChild(medicationItems.lastChild);
    }
    
    // Clear the first two items
    medicationItems.querySelectorAll('input, textarea').forEach(input => {
        input.value = '';
    });
    
    updateRemoveButtons();
}

function loadPatientPrescriptions() {
    if (!selectedPatient) return;
    
    fetch(`/dashboard/api/prescriptions/?patient_id=${selectedPatient.id}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayPrescriptions(data.prescriptions);
            } else {
                console.error('Error loading prescriptions:', data.error);
            }
        })
        .catch(error => {
            console.error('Error loading prescriptions:', error);
        });
}

function displayPrescriptions(prescriptions) {
    const prescriptionsList = document.getElementById('prescriptions-list');
    
    if (prescriptions.length === 0) {
        prescriptionsList.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-prescription-bottle-alt fa-3x mb-3"></i>
                <p>Nenhuma prescrição encontrada para este paciente.</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    prescriptions.forEach(prescription => {
        const statusClass = getPrescriptionStatusClass(prescription.status_value);
        const actionsHtml = getPrescriptionActionsHtml(prescription);
        
        html += `
            <div class="card mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <div>
                            <h6 class="card-title mb-1">Prescrição de ${prescription.prescription_date}</h6>
                            <span class="badge ${statusClass}">${prescription.status}</span>
                        </div>
                        <div class="dropdown">
                            <button class="btn btn-outline-secondary btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown">
                                Ações
                            </button>
                            <ul class="dropdown-menu">
                                ${actionsHtml}
                            </ul>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-12">
                            <h6>Medicamentos:</h6>
                            <ul class="list-unstyled">
        `;
        
        prescription.items.forEach(item => {
            html += `
                <li class="mb-2">
                    <strong>${item.medication_name}</strong> - ${item.quantity}<br>
                    <small class="text-muted">${item.dosage}</small>
                </li>
            `;
        });
        
        html += `
                            </ul>
        `;
        
        if (prescription.notes) {
            html += `
                <div class="mt-3">
                    <h6>Observações:</h6>
                    <p class="text-muted">${prescription.notes}</p>
                </div>
            `;
        }
        
        html += `
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    prescriptionsList.innerHTML = html;
}

function getPrescriptionStatusClass(status) {
    switch(status) {
        case 'active': return 'bg-success';
        case 'completed': return 'bg-primary';
        case 'cancelled': return 'bg-danger';
        case 'expired': return 'bg-warning';
        default: return 'bg-secondary';
    }
}

function getPrescriptionActionsHtml(prescription) {
    let html = '';
    
    // Always show email and WhatsApp options (allow multiple sends)
    html += `<li><a class="dropdown-item" href="#" onclick="sendPrescriptionEmail(${prescription.id}); return false;"><i class="fas fa-envelope me-2"></i>Enviar por Email</a></li>`;
    html += `<li><a class="dropdown-item" href="#" onclick="sendPrescriptionWhatsApp(${prescription.id}); return false;"><i class="fas fa-phone me-2"></i>Enviar por WhatsApp</a></li>`;
    html += `<li><a class="dropdown-item" href="#" onclick="printPrescription(${prescription.id}); return false;"><i class="fas fa-print me-2"></i>Imprimir</a></li>`;
    
    return html;
}

function sendPrescriptionEmail(prescriptionId) {
    // Handle event object if passed from onclick
    if (prescriptionId && typeof prescriptionId === 'object' && prescriptionId.target) {
        prescriptionId = null; // Reset to use currentPrescriptionId
    }
    
    if (!prescriptionId) prescriptionId = currentPrescriptionId;
    
    if (!prescriptionId) {
        showNotification('Nenhuma prescrição selecionada para envio.', 'warning');
        return;
    }
    
    const formData = new FormData();
    formData.append('prescription_id', prescriptionId);
    
    fetch('/dashboard/api/prescriptions/send-email/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            // Don't reload since we allow multiple sends
        } else {
            showNotification('Erro ao enviar por email: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('Error sending prescription email:', error);
        showNotification('Erro ao enviar prescrição por email. Tente novamente.', 'error');
    });
}

function sendPrescriptionWhatsApp(prescriptionId) {
    // Handle event object if passed from onclick
    if (prescriptionId && typeof prescriptionId === 'object' && prescriptionId.target) {
        prescriptionId = null; // Reset to use currentPrescriptionId
    }
    
    if (!prescriptionId) prescriptionId = currentPrescriptionId;
    
    if (!prescriptionId) {
        showNotification('Nenhuma prescrição selecionada para envio.', 'warning');
        return;
    }
    
    const formData = new FormData();
    formData.append('prescription_id', prescriptionId);
    
    fetch('/dashboard/api/prescriptions/send-whatsapp/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            // Don't reload since we allow multiple sends
        } else {
            showNotification('Erro ao enviar por WhatsApp: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('Error sending prescription WhatsApp:', error);
        showNotification('Erro ao enviar prescrição por WhatsApp. Tente novamente.', 'error');
    });
}

function printPrescription(prescriptionId) {
    // Handle event object if passed from onclick
    if (prescriptionId && typeof prescriptionId === 'object' && prescriptionId.target) {
        prescriptionId = null; // Reset to use currentPrescriptionId
    }
    
    if (!prescriptionId) prescriptionId = currentPrescriptionId;
    
    if (!prescriptionId) {
        showNotification('Nenhuma prescrição selecionada para impressão.', 'warning');
        return;
    }
    
    fetch(`/dashboard/api/prescriptions/print/?prescription_id=${prescriptionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                printPrescriptionWindow(data.prescription);
                // Don't reload since we allow multiple prints
            } else {
                showNotification('Erro ao carregar prescrição: ' + (data.error || 'Erro desconhecido'), 'error');
            }
        })
        .catch(error => {
            console.error('Error loading prescription for print:', error);
            showNotification('Erro ao carregar prescrição para impressão. Tente novamente.', 'error');
        });
}

function printPrescriptionWindow(prescription) {
    const printWindow = window.open('', '_blank');
    
    let itemsHtml = '';
    prescription.items.forEach(item => {
        itemsHtml += `
            <div class="medication-item mb-3 p-3 border">
                <h6><strong>${item.medication_name}</strong></h6>
                <p><strong>Quantidade:</strong> ${item.quantity}</p>
                <p><strong>Posologia:</strong> ${item.dosage}</p>
                ${item.notes ? `<p><strong>Observações:</strong> ${item.notes}</p>` : ''}
            </div>
        `;
    });
    
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Prescrição Médica - ${prescription.patient_name}</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 20px; 
                    line-height: 1.6;
                }
                .header { 
                    text-align: center; 
                    margin-bottom: 30px; 
                    border-bottom: 2px solid #333; 
                    padding-bottom: 10px; 
                }
                .prescription-info {
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }
                .medication-item {
                    background-color: #fff;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                }
                @media print { 
                    body { margin: 0; } 
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Prescrição Médica</h1>
                <h2>${prescription.patient_name}</h2>
                <p>Data: ${prescription.prescription_date}</p>
            </div>
            
            <div class="prescription-info">
                <p><strong>Paciente:</strong> ${prescription.patient_name}</p>
                <p><strong>Médico:</strong> ${prescription.doctor_name}</p>
                <p><strong>Data:</strong> ${prescription.prescription_date}</p>
            </div>
            
            <div class="medications">
                <h3>Medicamentos Prescritos:</h3>
                ${itemsHtml}
            </div>
            
            ${prescription.notes ? `
                <div class="notes mt-4">
                    <h3>Observações:</h3>
                    <p>${prescription.notes}</p>
                </div>
            ` : ''}
        </body>
        </html>
    `);
    
    printWindow.document.close();
    printWindow.print();
}