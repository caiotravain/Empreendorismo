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
    console.log('selectPatient called:', { patientName, patientId, pendingTab: window.pendingTabSwitch });
    
    selectedPatient = {
        name: patientName,
        id: patientId
    };
    
    // Save to localStorage for persistence
    localStorage.setItem('selectedPatient', JSON.stringify(selectedPatient));
    
    // Update the persistent patient selection header (if it exists)
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
    if (typeof loadPatientProntuarios === 'function') {
        loadPatientProntuarios(patientId);
    }
    
    // Load and display patient details if on prontuarios or prescricao tab
    const activeTab = document.querySelector('.tab-content.active');
    if (activeTab) {
        const tabId = activeTab.id;
        if (tabId === 'prontuarios-tab' || tabId === 'prescricao-tab') {
            const tabName = tabId.replace('-tab', '');
            setTimeout(() => {
                if (typeof loadAndDisplayPatientDetails === 'function') {
                    loadAndDisplayPatientDetails(patientId, tabName);
                }
            }, 100);
        }
    }
    
    // Show success message
    if (typeof showNotification === 'function') {
        showNotification(`Paciente ${patientName} selecionado.`, 'success');
    }
    
    // Update the page title to show selected patient
    document.title = `Dashboard Médico - ${patientName}`;
    
    // Switch to pending tab if one was requested
    if (typeof window.pendingTabSwitch !== 'undefined' && window.pendingTabSwitch !== null && typeof switchTab === 'function') {
        const tabToSwitch = window.pendingTabSwitch;
        console.log('Switching to pending tab:', tabToSwitch);
        window.pendingTabSwitch = null; // Clear it before switching to avoid loops
        setTimeout(() => {
            switchTab(tabToSwitch);
        }, 100); // Small delay to ensure patient data is loaded
    } else {
        console.log('No pending tab switch or switchTab not available');
    }
}

function updatePatientSelectionHeader(patientName, status) {
    const patientNameElement = document.getElementById('selected-patient-name');
    const patientInfoElement = document.getElementById('selected-patient-info');
    const patientStatusBadge = document.getElementById('patient-status-badge');
    const clearPatientBtn = document.getElementById('clear-patient-btn');
    const patientHeader = document.getElementById('patient-selection-header');
    
    // Only update if elements exist (header might be commented out)
    if (!patientNameElement || !patientInfoElement || !patientStatusBadge || !clearPatientBtn || !patientHeader) {
        return; // Exit early if header elements don't exist
    }
    
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
    
    // Remove from localStorage
    localStorage.removeItem('selectedPatient');
    
    // Update the persistent patient selection header
    updatePatientSelectionHeader('', 'none');
    
    // Disable all other tabs except agenda, indicators, prontuarios, and prescricao
    const allButtons = document.querySelectorAll('.btn-group .btn');
    allButtons.forEach((btn, index) => {
        if (index > 0) { // Skip the first button (Agenda)
            const btnId = btn.id;
            // Keep indicators button, prontuarios, and prescricao enabled
            if (index !== 1 && btnId !== 'prontuarios-btn' && btnId !== 'prescricao-btn') {
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
    document.title = 'Dashboard Médico - Plena';
    
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

function loadAndDisplayPatientDetails(patientId, tabName) {
    // Fetch patient details from API
    fetch(`/dashboard/api/patients/${patientId}/`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const patient = data.patient;
                displayPatientDetailsInTab(patient, tabName);
            } else {
                console.error('Error loading patient details:', data.error);
            }
        })
        .catch(error => {
            console.error('Error fetching patient details:', error);
        });
}

function displayPatientDetailsInTab(patient, tabName) {
    // Format date of birth
    const dob = patient.date_of_birth ? new Date(patient.date_of_birth).toLocaleDateString('pt-BR') : 'Não informado';
    
    // Format gender
    const gender = patient.gender === 'M' ? 'Masculino' : patient.gender === 'F' ? 'Feminino' : 'Outro';
    
    // Create patient details HTML
    const detailsHTML = `
        <div class="card shadow-sm mb-3">
            <div class="card-header bg-primary text-white py-2 d-flex justify-content-between align-items-center">
                <h6 class="mb-0" style="cursor: pointer; flex: 1;" onclick="togglePatientDetails('${tabName}')">
                    <i class="fas fa-user-circle me-2"></i>${patient.full_name}
                </h6>
                <div class="d-flex align-items-center gap-2">
                    <button class="btn btn-sm btn-outline-light" onclick="event.stopPropagation(); showPatientSelectionModal();" title="Alterar paciente" style="white-space: nowrap;">
                        <i class="fas fa-exchange-alt me-1"></i>Alterar
                    </button>
                    <i class="fas fa-chevron-down patient-details-arrow" id="patient-details-arrow-${tabName}" style="cursor: pointer; font-size: 0.9rem;" onclick="togglePatientDetails('${tabName}')"></i>
                </div>
            </div>
            <div class="card-body p-3 patient-details-body" id="patient-details-body-${tabName}">
                <div class="row">
                    <div class="col-md-3 col-sm-6 mb-2">
                        <h6 class="mb-1 small"><i class="fas fa-id-card me-2 text-muted"></i>CPF</h6>
                        <p class="text-muted mb-0 small">${patient.cpf || 'Não informado'}</p>
                    </div>
                    <div class="col-md-3 col-sm-6 mb-2">
                        <h6 class="mb-1 small"><i class="fas fa-envelope me-2 text-muted"></i>Email</h6>
                        <p class="text-muted mb-0 small">${patient.email || 'Não informado'}</p>
                    </div>
                    <div class="col-md-3 col-sm-6 mb-2">
                        <h6 class="mb-1 small"><i class="fas fa-phone me-2 text-muted"></i>Telefone</h6>
                        <p class="text-muted mb-0 small">${patient.phone || 'Não informado'}</p>
                    </div>
                    <div class="col-md-3 col-sm-6 mb-2">
                        <h6 class="mb-1 small"><i class="fas fa-birthday-cake me-2 text-muted"></i>Data de Nascimento</h6>
                        <p class="text-muted mb-0 small">${dob}</p>
                    </div>
                    <div class="col-md-3 col-sm-6 mb-2">
                        <h6 class="mb-1 small"><i class="fas fa-calendar-alt me-2 text-muted"></i>Idade</h6>
                        <p class="text-muted mb-0 small">${patient.age || 0} anos</p>
                    </div>
                    <div class="col-md-3 col-sm-6 mb-2">
                        <h6 class="mb-1 small"><i class="fas fa-venus-mars me-2 text-muted"></i>Sexo</h6>
                        <p class="text-muted mb-0 small">${gender}</p>
                    </div>
                    <div class="col-md-3 col-sm-6 mb-2">
                        <h6 class="mb-1 small"><i class="fas fa-map-marker-alt me-2 text-muted"></i>Endereço</h6>
                        <p class="text-muted mb-0 small">${patient.address || 'Não informado'}</p>
                    </div>
                    <div class="col-md-3 col-sm-6 mb-2">
                        <h6 class="mb-1 small"><i class="fas fa-city me-2 text-muted"></i>Cidade/Estado</h6>
                        <p class="text-muted mb-0 small">${patient.city || 'Não informado'}${patient.state ? ', ' + patient.state : ''}</p>
                    </div>
                    <div class="col-md-3 col-sm-6 mb-2">
                        <h6 class="mb-1 small"><i class="fas fa-mail-bulk me-2 text-muted"></i>CEP</h6>
                        <p class="text-muted mb-0 small">${patient.zip_code || 'Não informado'}</p>
                    </div>
                </div>
                ${patient.emergency_contact_name || patient.emergency_contact_phone || patient.medical_insurance ? `
                <hr class="my-2">
                <div class="row">
                    ${patient.emergency_contact_name || patient.emergency_contact_phone ? `
                    <div class="col-md-4 col-sm-6 mb-2">
                        <h6 class="mb-1 small"><i class="fas fa-user-friends me-2 text-muted"></i>Contato de Emergência</h6>
                        <p class="text-muted mb-1 small">${patient.emergency_contact_name || 'Não informado'}</p>
                        <p class="text-muted mb-0 small"><i class="fas fa-phone-alt me-1"></i>${patient.emergency_contact_phone || 'Não informado'}</p>
                    </div>
                    ` : ''}
                    ${patient.medical_insurance ? `
                    <div class="col-md-4 col-sm-6 mb-2">
                        <h6 class="mb-1 small"><i class="fas fa-heartbeat me-2 text-muted"></i>Plano de Saúde</h6>
                        <p class="text-muted mb-0 small">${patient.medical_insurance}</p>
                    </div>
                    ` : ''}
                </div>
                ` : ''}
            </div>
        </div>
    `;
    
    // Insert into the appropriate tab
    if (tabName === 'prontuarios') {
        const prontuariosTab = document.getElementById('prontuarios-tab');
        if (prontuariosTab) {
            // Hide the alert banner

            // Find or create patient details container
            let detailsContainer = document.getElementById('patient-details-prontuarios');
            if (!detailsContainer) {
                // Create container at the beginning of the col-12
                const col12 = prontuariosTab.querySelector('.col-12');
                if (col12) {
                    detailsContainer = document.createElement('div');
                    detailsContainer.id = 'patient-details-prontuarios';
                    col12.insertBefore(detailsContainer, col12.firstChild);
                }
            }
            if (detailsContainer) {
                detailsContainer.innerHTML = detailsHTML;
            }
        }
    } else if (tabName === 'prescricao') {
        const prescricaoTab = document.getElementById('prescricao-tab');
        if (prescricaoTab) {
            // Hide the alert banner

            
            // Find or create patient details container
            let detailsContainer = document.getElementById('patient-details-prescricao');
            if (!detailsContainer) {
                // Create container at the beginning of the col-12
                const col12 = prescricaoTab.querySelector('.col-12');
                if (col12) {
                    detailsContainer = document.createElement('div');
                    detailsContainer.id = 'patient-details-prescricao';
                    col12.insertBefore(detailsContainer, col12.firstChild);
                }
            }
            if (detailsContainer) {
                detailsContainer.innerHTML = detailsHTML;
            }
        }
    }
}

function togglePatientDetails(tabName) {
    const bodyId = `patient-details-body-${tabName}`;
    const arrowId = `patient-details-arrow-${tabName}`;
    const body = document.getElementById(bodyId);
    const arrow = document.getElementById(arrowId);
    
    if (body && arrow) {
        const isCollapsed = body.classList.contains('collapsed');
        
        if (isCollapsed) {
            // Expand
            body.classList.remove('collapsed');
            arrow.classList.remove('fa-chevron-up');
            arrow.classList.add('fa-chevron-down');
            arrow.classList.remove('rotated');
        } else {
            // Collapse
            body.classList.add('collapsed');
            arrow.classList.remove('fa-chevron-down');
            arrow.classList.add('fa-chevron-up');
            arrow.classList.add('rotated');
        }
    }
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

// WhatsApp Test Functions
function showWhatsAppTestModal() {
    const modalElement = document.getElementById('whatsappTestModal');
    if (!modalElement) {
        console.error('WhatsApp test modal not found');
        return;
    }
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

function sendWhatsAppTest() {
    const phoneNumber = document.getElementById('test-phone-number')?.value.trim();
    const message = document.getElementById('test-message')?.value.trim();
    
    if (!phoneNumber) {
        showNotification('Por favor, digite o número de telefone', 'warning');
        return;
    }
    
    if (!message) {
        showNotification('Por favor, digite a mensagem', 'warning');
        return;
    }
    
    // Show loading notification
    showNotification('Gerando link do WhatsApp...', 'info');
    
    // Send request to API
    fetch('/dashboard/api/whatsapp/send/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `phone_number=${encodeURIComponent(phoneNumber)}&message=${encodeURIComponent(message)}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Open WhatsApp link in new tab
            window.open(data.whatsapp_url, '_blank');
            showNotification('Link do WhatsApp aberto! Complete o envio no WhatsApp Web.', 'success');
            
            // Close modal
            const modalElement = document.getElementById('whatsappTestModal');
            if (modalElement) {
                const modal = bootstrap.Modal.getInstance(modalElement);
                if (modal) {
                    modal.hide();
                }
            }
        } else {
            showNotification('Erro: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Erro ao enviar mensagem: ' + error.message, 'error');
    });
}

// Global variable to store current record data for printing
let currentRecordData = null;

function showRecordPopup(recordId, date, time, doctor, content) {
    // Decode Unicode escape sequences in content
    function decodeUnicode(str) {
        if (!str) return '';
        // Replace Unicode escape sequences
        return str.replace(/\\u([0-9a-fA-F]{4})/g, function(match, hex) {
            return String.fromCharCode(parseInt(hex, 16));
        })
        // Replace common escape sequences
        .replace(/\\n/g, '\n')
        .replace(/\\r/g, '\r')
        .replace(/\\t/g, '\t')
        .replace(/\\"/g, '"')
        .replace(/\\'/g, "'")
        .replace(/\\\\/g, '\\');
    }
    
    // Decode content
    const decodedContent = decodeUnicode(content);
    
    // Store record data for printing
    currentRecordData = {
        id: recordId,
        date: date,
        time: time,
        doctor: doctor,
        content: decodedContent
    };
    
    // Populate modal with record data
    document.getElementById('popup-date').textContent = date;
    document.getElementById('popup-time').textContent = time;
    document.getElementById('popup-doctor').textContent = doctor;
    
    // Display content with proper line breaks (preserve whitespace)
    const contentElement = document.getElementById('popup-content');
    contentElement.style.whiteSpace = 'pre-wrap'; // Preserve line breaks and wrap text
    contentElement.textContent = decodedContent;
    
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
    let content = element.getAttribute('data-record-content');
    
    // Decode HTML entities that might have been escaped by Django's escapejs
    if (content) {
        const textarea = document.createElement('textarea');
        textarea.innerHTML = content;
        content = textarea.value;
    }
    
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


// View mode state (doctor or administrator)
let currentViewMode = 'doctor'; // Default to doctor view

// Switch between doctor and administrator view modes
function switchViewMode(mode) {
    if (mode !== 'doctor' && mode !== 'administrator') {
        return;
    }
    
    currentViewMode = mode;
    
    // Update navbar dropdown menu items to show active state
    const navbarDoctorItem = document.getElementById('navbar-doctor-item');
    const navbarAdminItem = document.getElementById('navbar-admin-item');
    
    if (navbarDoctorItem && navbarAdminItem) {
        navbarDoctorItem.classList.remove('active');
        navbarAdminItem.classList.remove('active');
        
        if (mode === 'doctor') {
            navbarDoctorItem.classList.add('active');
        } else {
            navbarAdminItem.classList.add('active');
        }
    }
    
    // Show/hide tab groups
    const doctorTabsGroup = document.getElementById('doctor-tabs-group');
    const adminTabsGroup = document.getElementById('administrator-tabs-group');
    
    if (mode === 'doctor') {
        // Show doctor tabs, hide administrator tabs
        if (doctorTabsGroup) {
            doctorTabsGroup.style.setProperty('display', 'flex', 'important');
            doctorTabsGroup.style.setProperty('visibility', 'visible', 'important');
        }
        if (adminTabsGroup) {
            adminTabsGroup.style.setProperty('display', 'none', 'important');
            adminTabsGroup.style.setProperty('visibility', 'hidden', 'important');
        }
    } else {
        // Show administrator tabs, hide doctor tabs
        if (doctorTabsGroup) {
            doctorTabsGroup.style.setProperty('display', 'none', 'important');
            doctorTabsGroup.style.setProperty('visibility', 'hidden', 'important');
        }
        if (adminTabsGroup) {
            adminTabsGroup.style.setProperty('display', 'flex', 'important');
            adminTabsGroup.style.setProperty('visibility', 'visible', 'important');
        }
    }
    
    // Update URL with view mode
    const url = new URL(window.location);
    if (mode === 'administrator') {
        url.searchParams.set('view', 'administrator');
    } else {
        url.searchParams.delete('view');
    }
    window.history.pushState({}, '', url);
    
    // Close the navbar dropdown after selection
    const navbarDropdown = document.getElementById('navbarDropdown');
    if (navbarDropdown && typeof bootstrap !== 'undefined') {
        const dropdownInstance = bootstrap.Dropdown.getInstance(navbarDropdown);
        if (dropdownInstance) {
            dropdownInstance.hide();
        }
    }
    
    // If switching to administrator, go to indicadores tab
    // But only if there's no tab parameter in the URL
    const urlParams = new URLSearchParams(window.location.search);
    const tabParam = urlParams.get('tab');
    
    if (mode === 'administrator') {
        // Switch to indicadores tab when entering administrator mode
        // But only if no tab parameter is specified in URL
        if (tabParam) {
            // Apply the tab from URL parameter after a delay to ensure view mode switching is complete
            setTimeout(function() {
                if (typeof switchTab === 'function') {
                    switchTab(tabParam);
                }
            }, 200);
        } else {
            switchTab('indicadores');
        }
    } else {
        // Switch back to agenda when going to doctor view
        // But only if no tab parameter is specified in URL
        if (tabParam) {
            // Apply the tab from URL parameter after a delay to ensure view mode switching is complete
            setTimeout(function() {
                if (typeof switchTab === 'function') {
                    switchTab(tabParam);
                }
            }, 200);
        } else {
            switchTab('agenda');
        }
    }
}

// Set default active tab to 'agenda' or from URL parameter
document.addEventListener('DOMContentLoaded', function() {
    // Initialize view mode (default to doctor)
    // Check if navbar dropdown items exist (available to all users now)
    const navbarDoctorItem = document.getElementById('navbar-doctor-item');
    const navbarAdminItem = document.getElementById('navbar-admin-item');
    const hasViewToggle = !!(navbarDoctorItem && navbarAdminItem);
    
    // Check URL parameter for active tab first (before view mode switching)
    const urlParams = new URLSearchParams(window.location.search);
    const tabParam = urlParams.get('tab');
    
    if (hasViewToggle) {
        // Check if there's a view mode in URL or session
        const viewMode = urlParams.get('view') || 'doctor';
        if (viewMode === 'administrator') {
            switchViewMode('administrator');
        } else {
            switchViewMode('doctor');
        }
        // switchViewMode will handle tabParam if it exists, so we skip the duplicate call below
    } else {
        // If no view toggle, handle tab parameter directly
        if (tabParam && typeof switchTab === 'function') {
            // Switch to the tab from URL parameter
            setTimeout(function() {
                switchTab(tabParam);
            }, 150);
        }
    }
    
    // Only set default agenda tab if no tab parameter and view mode wasn't toggled
    if (!tabParam && !hasViewToggle) {
        // Ensure agenda tab is shown by default
        const agendaTab = document.getElementById('agenda-tab');
        if (agendaTab) {
            // Hide all tabs first
            const allTabs = document.querySelectorAll('.tab-content');
            allTabs.forEach(tab => {
                tab.style.display = 'none';
                tab.classList.remove('active');
            });
            // Show agenda tab
            agendaTab.style.display = 'block';
            agendaTab.classList.add('active');
        }
        
        // Set the first button (Agenda) as active by default
        const activeTabGroup = currentViewMode === 'administrator' ? 
            document.getElementById('administrator-tabs-group') : 
            document.getElementById('doctor-tabs-group');
        const firstButton = activeTabGroup ? activeTabGroup.querySelector('.btn') : null;
        if (firstButton) {
            firstButton.classList.remove('btn-outline-primary');
            firstButton.classList.add('btn-primary');
        }
        
        // Initialize FullCalendar for agenda tab
        if (typeof initializeFullCalendar === 'function') {
            setTimeout(function() {
                initializeFullCalendar();
            }, 200);
        }
    }
    
    // Restore selected patient from localStorage
    const savedPatient = localStorage.getItem('selectedPatient');
    if (savedPatient) {
        try {
            selectedPatient = JSON.parse(savedPatient);
            if (selectedPatient && selectedPatient.name && selectedPatient.id) {
                // Restore patient selection
                updatePatientSelectionHeader(selectedPatient.name, 'selected');
                // Update patient info in tabs
                if (typeof updatePatientInfo === 'function') {
                    updatePatientInfo(selectedPatient.name);
                }
                // Load patient-specific data
                if (typeof loadPatientProntuarios === 'function') {
                    loadPatientProntuarios(selectedPatient.id);
                }
            }
        } catch (e) {
            console.error('Error restoring patient from localStorage:', e);
            selectedPatient = null;
        }
    }
    
    // Initialize patient selection header (if no patient restored)
    if (!selectedPatient) {
        updatePatientSelectionHeader('', 'none');
    }
    
    // Restore active tab from localStorage if not in URL
    const savedTab = localStorage.getItem('activeTab');
    if (savedTab && !tabParam && typeof switchTab === 'function') {
        setTimeout(function() {
            switchTab(savedTab);
            // If patient is restored and we're on prontuarios or prescricao, load details
            if (selectedPatient && (savedTab === 'prontuarios' || savedTab === 'prescricao')) {
                setTimeout(() => {
                    if (typeof loadAndDisplayPatientDetails === 'function') {
                        loadAndDisplayPatientDetails(selectedPatient.id, savedTab);
                    }
                }, 300);
            }
        }, 250);
    } else if (tabParam && selectedPatient && (tabParam === 'prontuarios' || tabParam === 'prescricao')) {
        // If tab is in URL and patient is restored, load patient details
        setTimeout(() => {
            if (typeof loadAndDisplayPatientDetails === 'function') {
                loadAndDisplayPatientDetails(selectedPatient.id, tabParam);
            }
        }, 300);
    }
    
    // Attach prontuario event listeners
    attachProntuarioEventListeners();
    
    
    // Load patients and doctors for appointment modal
    loadPatientsAndDoctors();
    
    // Initialize prescription form
    initializePrescriptionForm();
    
    // Refresh agenda stats on page load
    refreshAgendaStats();
    
    // Initialize reports tab with default dates
    initializeReportsTab();
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
    
    // Set default status to 'scheduled'
    const statusSelect = document.getElementById('appointment-status');
    if (statusSelect) {
        // Try to set to 'scheduled', if option exists
        const scheduledOption = statusSelect.querySelector('option[value="scheduled"]');
        if (scheduledOption) {
            statusSelect.value = 'scheduled';
        } else {
            // If 'scheduled' option doesn't exist yet (settings not loaded), set it after settings are applied
            const modalElement = document.getElementById('newAppointmentModal');
            const setScheduledStatus = function() {
                const statusSelectAfter = document.getElementById('appointment-status');
                if (statusSelectAfter) {
                    const scheduledOpt = statusSelectAfter.querySelector('option[value="scheduled"]');
                    if (scheduledOpt) {
                        statusSelectAfter.value = 'scheduled';
                    }
                }
            };
            modalElement.addEventListener('shown.bs.modal', setScheduledStatus, { once: true });
        }
    }
    
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
        // Load and apply settings to the modal
        if (typeof updateAppointmentModalWithSettings === 'function') {
            // If settings are already loaded, update immediately
            if (typeof appointmentSettings !== 'undefined' && appointmentSettings) {
                updateAppointmentModalWithSettings();
            } else {
                // Otherwise, load settings first
                if (typeof loadSettings === 'function') {
                    loadSettings();
                }
            }
        }
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
    // Load patients and return the promise
    return fetch('/dashboard/api/patients/')
        .then(response => response.json())
        .then(data => {
            console.log('Patients loaded:', data);
            window.allPatients = data.success ? data.patients : [];
            setupPatientSearch();
            return data;
        })
        .catch(error => {
            console.error('Error loading patients:', error);
            window.allPatients = [];
            throw error;
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
        const filteredPatients = window.allPatients.filter(patient => {
            const name = `${patient.first_name} ${patient.last_name}`.toLowerCase();
            const cpf = (patient.cpf || '').toLowerCase();
            return name.includes(searchTerm) || cpf.includes(searchTerm);
        });
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
        
        // Handle payment type change: show value input for particular, insurance operator for convenio
        const paymentTypeSelect = document.getElementById('appointment-payment-type');
        const insuranceOperatorRow = document.getElementById('insurance-operator-row');
        const valueRow = document.getElementById('appointment-value-row');
        if (paymentTypeSelect) {
            function togglePaymentFields() {
                const isConvenio = paymentTypeSelect.value === 'convenio';
                const isParticular = paymentTypeSelect.value === 'particular';
                if (insuranceOperatorRow) {
                    insuranceOperatorRow.style.display = isConvenio ? 'flex' : 'none';
                    if (!isConvenio) {
                        const insuranceOperatorSelect = document.getElementById('appointment-insurance-operator');
                        if (insuranceOperatorSelect) insuranceOperatorSelect.value = '';
                    }
                }
                if (valueRow) {
                    valueRow.style.display = isParticular ? 'flex' : 'none';
                    if (!isParticular) {
                        const valueInput = document.getElementById('appointment-value');
                        if (valueInput) valueInput.value = '';
                    }
                }
            }
            paymentTypeSelect.addEventListener('change', togglePaymentFields);
            togglePaymentFields(); // Initial state when modal opens
        }
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
    
    // When convenio, use configured price for the selected insurance operator
    const paymentType = formData.get('payment_type');
    if (paymentType === 'convenio' && typeof appointmentSettings !== 'undefined' && appointmentSettings && appointmentSettings.convenio_prices) {
        const selectedOperator = formData.get('insurance_operator') || '';
        const price = appointmentSettings.convenio_prices[selectedOperator];
        formData.set('value', (price != null && price !== '') ? String(price) : '0');
    }
    
    // Ensure status is set to 'scheduled' if not provided
    const statusSelect = document.getElementById('appointment-status');
    if (statusSelect && !formData.get('status')) {
        formData.set('status', 'scheduled');
    } else if (statusSelect && statusSelect.value) {
        // Make sure we're using the actual value, not display name
        formData.set('status', statusSelect.value);
    } else {
        formData.set('status', 'scheduled');
    }
    
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
    console.log('selectPatientFromPopup called:', { patientId, patientName });
    
    // Close the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('patientSelectionModal'));
    if (modal) {
        modal.hide();
    }
    
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
                    const cpf = (patient.cpf || '').toLowerCase();
                    const searchLower = searchTerm.toLowerCase();
                    
                    return fullName.includes(searchLower) || 
                           email.includes(searchLower) || 
                           phone.includes(searchLower) ||
                           cpf.includes(searchLower);
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
    
    // Initialize autocomplete for existing medication inputs
    initializeMedicationAutocomplete();
    
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
                <input type="text" class="form-control medication-autocomplete" name="medication_name[]" placeholder="Nome do medicamento" autocomplete="off">
                <div class="medication-autocomplete-list" style="display: none;"></div>
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
    
    // Initialize autocomplete for the new medication input
    initializeMedicationAutocompleteForInput(newItem.querySelector('.medication-autocomplete'));
    
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

// Medication autocomplete functionality
let autocompleteTimeout = null;

function initializeMedicationAutocomplete() {
    // Initialize autocomplete for all existing medication inputs
    document.querySelectorAll('.medication-autocomplete').forEach(input => {
        initializeMedicationAutocompleteForInput(input);
    });
    
    // Also initialize for inputs without the class (existing ones in HTML)
    document.querySelectorAll('input[name="medication_name[]"]').forEach(input => {
        if (!input.classList.contains('medication-autocomplete')) {
            input.classList.add('medication-autocomplete');
            // Create autocomplete list container if it doesn't exist
            if (!input.nextElementSibling || !input.nextElementSibling.classList.contains('medication-autocomplete-list')) {
                const listDiv = document.createElement('div');
                listDiv.className = 'medication-autocomplete-list';
                listDiv.style.display = 'none';
                listDiv.style.position = 'absolute';
                listDiv.style.zIndex = '1000';
                listDiv.style.backgroundColor = 'white';
                listDiv.style.border = '1px solid #ccc';
                listDiv.style.borderRadius = '4px';
                listDiv.style.maxHeight = '200px';
                listDiv.style.overflowY = 'auto';
                listDiv.style.width = input.offsetWidth + 'px';
                input.parentElement.style.position = 'relative';
                input.parentElement.appendChild(listDiv);
            }
            initializeMedicationAutocompleteForInput(input);
        }
    });
}

function initializeMedicationAutocompleteForInput(input) {
    // Create autocomplete list container if it doesn't exist
    let listDiv = input.nextElementSibling;
    if (!listDiv || !listDiv.classList.contains('medication-autocomplete-list')) {
        listDiv = document.createElement('div');
        listDiv.className = 'medication-autocomplete-list';
        listDiv.style.display = 'none';
        listDiv.style.position = 'absolute';
        listDiv.style.zIndex = '1000';
        listDiv.style.backgroundColor = 'white';
        listDiv.style.border = '1px solid #ccc';
        listDiv.style.borderRadius = '4px';
        listDiv.style.maxHeight = '200px';
        listDiv.style.overflowY = 'auto';
        listDiv.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
        input.parentElement.style.position = 'relative';
        input.parentElement.appendChild(listDiv);
    }
    
    // Set width to match input
    listDiv.style.width = input.offsetWidth + 'px';
    
    // Debounced search function
    input.addEventListener('input', function(e) {
        const query = e.target.value.trim();
        
        // Clear previous timeout
        if (autocompleteTimeout) {
            clearTimeout(autocompleteTimeout);
        }
        
        // Hide list if query is empty
        if (query.length < 2) {
            listDiv.style.display = 'none';
            return;
        }
        
        // Debounce API call
        autocompleteTimeout = setTimeout(() => {
            searchMedications(query, input, listDiv);
        }, 300);
    });
    
    // Hide list when input loses focus (with delay to allow click on list)
    input.addEventListener('blur', function() {
        setTimeout(() => {
            listDiv.style.display = 'none';
        }, 200);
    });
    
    // Handle keyboard navigation
    input.addEventListener('keydown', function(e) {
        const items = listDiv.querySelectorAll('.autocomplete-item');
        const currentActive = listDiv.querySelector('.autocomplete-item.active');
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (currentActive) {
                currentActive.classList.remove('active');
                const next = currentActive.nextElementSibling;
                if (next) {
                    next.classList.add('active');
                    next.scrollIntoView({ block: 'nearest' });
                } else {
                    items[0]?.classList.add('active');
                }
            } else {
                items[0]?.classList.add('active');
            }
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (currentActive) {
                currentActive.classList.remove('active');
                const prev = currentActive.previousElementSibling;
                if (prev) {
                    prev.classList.add('active');
                    prev.scrollIntoView({ block: 'nearest' });
                } else {
                    items[items.length - 1]?.classList.add('active');
                }
            } else {
                items[items.length - 1]?.classList.add('active');
            }
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (currentActive) {
                const medicationName = currentActive.dataset.name;
                input.value = medicationName;
                listDiv.style.display = 'none';
            }
        } else if (e.key === 'Escape') {
            listDiv.style.display = 'none';
        }
    });
}

function searchMedications(query, input, listDiv) {
    fetch(`/dashboard/api/medications/search/?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.medications.length > 0) {
                displayMedicationSuggestions(data.medications, input, listDiv);
            } else {
                listDiv.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error searching medications:', error);
            listDiv.style.display = 'none';
        });
}

function displayMedicationSuggestions(medications, input, listDiv) {
    listDiv.innerHTML = '';
    
    medications.forEach(medication => {
        const item = document.createElement('div');
        item.className = 'autocomplete-item';
        item.style.padding = '4px 8px';
        item.style.cursor = 'pointer';
        item.style.borderBottom = '1px solid #eee';
        item.style.fontSize = '14px';
        item.style.lineHeight = '1.4';
        item.dataset.name = medication.name;
        
        // Highlight matching text
        const name = medication.name;
        const query = input.value.toLowerCase();
        const nameLower = name.toLowerCase();
        const index = nameLower.indexOf(query);
        
        let html = name;
        if (index !== -1) {
            const before = name.substring(0, index);
            const match = name.substring(index, index + query.length);
            const after = name.substring(index + query.length);
            html = `${before}<strong>${match}</strong>${after}`;
        }
        
        item.innerHTML = html;
        if (medication.description) {
            item.innerHTML += `<br><small class="text-muted" style="font-size: 11px; line-height: 1.3;">${medication.description}</small>`;
        }
        
        // Hover effect
        item.addEventListener('mouseenter', function() {
            listDiv.querySelectorAll('.autocomplete-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            item.style.backgroundColor = '#f0f0f0';
        });
        
        item.addEventListener('mouseleave', function() {
            item.style.backgroundColor = '';
        });
        
        // Click to select
        item.addEventListener('click', function() {
            input.value = medication.name;
            listDiv.style.display = 'none';
            input.focus();
        });
        
        listDiv.appendChild(item);
    });
    
    // Update width and position
    listDiv.style.width = input.offsetWidth + 'px';
    listDiv.style.display = 'block';
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
    
    // Open PDF in new window/tab
    const pdfUrl = `/dashboard/api/prescriptions/generate-pdf/?prescription_id=${prescriptionId}`;
    window.open(pdfUrl, '_blank');
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

// Reports Functions
let currentReportData = null;

function initializeReportsTab() {
    // Set default dates to current month
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    
    const startDateInput = document.getElementById('report-start-date');
    const endDateInput = document.getElementById('report-end-date');
    
    if (startDateInput) {
        startDateInput.value = firstDay.toISOString().split('T')[0];
    }
    if (endDateInput) {
        endDateInput.value = lastDay.toISOString().split('T')[0];
    }
}

function handleReportTypeChange() {
    const reportType = document.getElementById('report-type');
    if (reportType && reportType.value) {
        loadQuickStats();
    }
}

function loadQuickStats() {
    const startDate = document.getElementById('report-start-date');
    const endDate = document.getElementById('report-end-date');
    
    if (!startDate || !startDate.value || !endDate || !endDate.value) {
        return;
    }
    
    fetch(`/dashboard/api/reports/quick-stats/?start_date=${startDate.value}&end_date=${endDate.value}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const completedEl = document.getElementById('quick-stats-completed');
                const revenueEl = document.getElementById('quick-stats-revenue');
                const patientsEl = document.getElementById('quick-stats-patients');
                
                if (completedEl) completedEl.textContent = data.stats.completed_appointments;
                if (revenueEl) revenueEl.textContent = `R$ ${data.stats.total_revenue.toFixed(2)}`;
                if (patientsEl) patientsEl.textContent = data.stats.unique_patients;
            }
        })
        .catch(error => {
            console.error('Error loading quick stats:', error);
        });
}

function generateReport() {
    const reportType = document.getElementById('report-type');
    const startDate = document.getElementById('report-start-date');
    const endDate = document.getElementById('report-end-date');
    
    if (!reportType || !reportType.value) {
        showNotification('Por favor, selecione um tipo de relatório', 'warning');
        return;
    }
    
    if (!startDate || !startDate.value || !endDate || !endDate.value) {
        showNotification('Por favor, selecione as datas de início e fim', 'warning');
        return;
    }
    
    if (new Date(startDate.value) > new Date(endDate.value)) {
        showNotification('A data de início deve ser anterior à data de fim', 'warning');
        return;
    }
    
    // Show loading
    showNotification('Gerando relatório...', 'info');
    
    fetch(`/dashboard/api/reports/generate/?report_type=${reportType.value}&start_date=${startDate.value}&end_date=${endDate.value}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentReportData = data;
                displayReport(data);
                const exportBtn = document.getElementById('export-btn');
                if (exportBtn) exportBtn.style.display = 'inline-block';
                showNotification('Relatório gerado com sucesso!', 'success');
            } else {
                showNotification('Erro ao gerar relatório: ' + data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error generating report:', error);
            showNotification('Erro ao gerar relatório', 'error');
        });
}

function displayReport(data) {
    const resultsContainer = document.getElementById('report-results-container');
    const resultsDiv = document.getElementById('report-results');
    
    if (!resultsContainer || !resultsDiv) return;
    
    resultsContainer.style.display = 'block';
    
    let html = '';
    
    // Summary
    html += `<div class="alert alert-info">
        <h6>Resumo do Relatório</h6>
        <p><strong>Período:</strong> ${data.summary.start_date} a ${data.summary.end_date}</p>
    </div>`;
    
    // Report-specific content
    if (data.report_type === 'appointments') {
        html += generateAppointmentsTable(data);
    } else if (data.report_type === 'payment_methods') {
        html += generatePaymentMethodsTable(data);
    } else if (data.report_type === 'patient_summary') {
        html += generatePatientSummaryTable(data);
    } else if (data.report_type === 'financial_summary') {
        html += generateFinancialSummaryTable(data);
    } else if (data.report_type === 'monthly_appointments') {
        html += generateMonthlyAppointmentsTable(data);
    }
    
    resultsDiv.innerHTML = html;
}

function generateAppointmentsTable(data) {
    let html = `<table class="table table-striped">
        <thead>
            <tr>
                <th>Data</th>
                <th>Hora</th>
                <th>Paciente</th>
                <th>Tipo</th>
                <th>Pagamento</th>
                <th>Valor</th>
            </tr>
        </thead>
        <tbody>`;
    
    data.data.forEach(item => {
        html += `<tr>
            <td>${item.date}</td>
            <td>${item.time}</td>
            <td>${item.patient}</td>
            <td>${item.type}</td>
            <td>${item.payment}</td>
            <td>R$ ${item.value.toFixed(2)}</td>
        </tr>`;
    });
    
    html += `</tbody></table>`;
    html += `<p><strong>Total de consultas:</strong> ${data.summary.total_appointments}</p>`;
    html += `<p><strong>Receita total:</strong> R$ ${data.summary.total_revenue.toFixed(2)}</p>`;
    
    return html;
}

function generatePaymentMethodsTable(data) {
    let html = `<table class="table table-striped">
        <thead>
            <tr>
                <th>Método de Pagamento</th>
                <th>Quantidade</th>
            </tr>
        </thead>
        <tbody>`;
    
    data.data.forEach(item => {
        html += `<tr>
            <td>${item.payment_method}</td>
            <td>${item.count}</td>
        </tr>`;
    });
    
    html += `</tbody></table>`;
    html += `<p><strong>Total de consultas:</strong> ${data.summary.total_appointments}</p>`;
    
    return html;
}

function generatePatientSummaryTable(data) {
    let html = `<table class="table table-striped">
        <thead>
            <tr>
                <th>Paciente</th>
                <th>Total de Consultas</th>
            </tr>
        </thead>
        <tbody>`;
    
    data.data.forEach(item => {
        html += `<tr>
            <td>${item.patient_name}</td>
            <td>${item.total_appointments}</td>
        </tr>`;
    });
    
    html += `</tbody></table>`;
    html += `<p><strong>Total de pacientes:</strong> ${data.summary.total_patients}</p>`;
    
    return html;
}

function generateFinancialSummaryTable(data) {
    let html = `<h6>Receita por Categoria</h6>
        <table class="table table-striped mb-4">
            <thead>
                <tr>
                    <th>Categoria</th>
                    <th>Valor</th>
                </tr>
            </thead>
            <tbody>`;
    
    data.data.by_category.forEach(item => {
        html += `<tr>
            <td>${item.category}</td>
            <td>R$ ${item.amount.toFixed(2)}</td>
        </tr>`;
    });
    
    html += `</tbody></table>`;
    
    html += `<h6>Receita por Método de Pagamento</h6>
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>Método</th>
                    <th>Valor</th>
                </tr>
            </thead>
            <tbody>`;
    
    data.data.by_method.forEach(item => {
        html += `<tr>
            <td>${item.method}</td>
            <td>R$ ${item.amount.toFixed(2)}</td>
        </tr>`;
    });
    
    html += `</tbody></table>`;
    html += `<p class="mt-3"><strong>Receita total:</strong> R$ ${data.data.total_revenue.toFixed(2)}</p>`;
    
    return html;
}

function generateMonthlyAppointmentsTable(data) {
    let html = `<table class="table table-striped">
        <thead>
            <tr>
                <th>Mês</th>
                <th>Quantidade de Consultas</th>
            </tr>
        </thead>
        <tbody>`;
    
    data.data.forEach(item => {
        html += `<tr>
            <td>${item.month}</td>
            <td>${item.count}</td>
        </tr>`;
    });
    
    html += `</tbody></table>`;
    html += `<p><strong>Total de consultas:</strong> ${data.summary.total_appointments}</p>`;
    
    return html;
}

function exportReport() {
    if (!currentReportData) {
        showNotification('Nenhum relatório gerado para exportar', 'warning');
        return;
    }
    
    // Get the date inputs
    const startDate = document.getElementById('report-start-date').value;
    const endDate = document.getElementById('report-end-date').value;
    const reportType = document.getElementById('report-type').value;
    
    if (!startDate || !endDate || !reportType) {
        showNotification('Por favor, selecione todas as informações do relatório', 'warning');
        return;
    }
    
    // Show loading notification
    showNotification('Gerando PDF...', 'info');
    
    // Generate PDF using the API
    window.location.href = `/dashboard/api/reports/generate-pdf/?report_type=${reportType}&start_date=${startDate}&end_date=${endDate}`;
}

// ============================================================================
// WAITING LIST FUNCTIONS
// ============================================================================

// Global variable to store waitlist entries
let waitlistEntries = [];

function showAddToWaitlistModal() {
    const modal = new bootstrap.Modal(document.getElementById('addToWaitlistModal'));
    const form = document.getElementById('addToWaitlistForm');
    
    // Only reset if not in edit mode
    if (!form.dataset.entryId) {
        // Reset form
        if (form) {
            form.reset();
        }
        
        // Clear patient selection
        document.getElementById('waitlist-patient').value = '';
        document.getElementById('waitlist-patient-search').value = '';
        
        // Restore original button text and title
        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.innerHTML = '<i class="fas fa-clock me-1"></i>Adicionar à Lista de Espera';
        
        const modalTitle = document.getElementById('addToWaitlistModalLabel');
        modalTitle.innerHTML = '<i class="fas fa-clock me-2"></i>Adicionar à Lista de Espera';
        
        // Remove entryId to ensure it's treated as a new entry
        delete form.dataset.entryId;
    }
    
    // Set up patient search if patients are loaded
    if (window.allPatients && window.allPatients.length > 0) {
        setupWaitlistPatientSearch();
    } else {
        loadPatientsAndDoctors()
            .then(() => {
                setupWaitlistPatientSearch();
            })
            .catch(error => {
                console.error('Error loading patients for waitlist:', error);
                // Still try to set up the search with empty patients
                setupWaitlistPatientSearch();
            });
    }
    
    // Set up patient search when modal is shown
    const modalElement = document.getElementById('addToWaitlistModal');
    modalElement.addEventListener('shown.bs.modal', function() {
        setupWaitlistPatientSearch();
    }, { once: true });
    
    modal.show();
}

function setupWaitlistPatientSearch() {
    const searchInput = document.getElementById('waitlist-patient-search');
    const dropdown = document.getElementById('waitlist-patient-dropdown');
    const hiddenInput = document.getElementById('waitlist-patient');
    const nameInput = document.getElementById('waitlist-patient-name');
    const phoneInput = document.getElementById('waitlist-phone');
    const emailInput = document.getElementById('waitlist-email');
    
    if (!searchInput || !dropdown || !hiddenInput) return;
    
    // Show all patients initially
    showWaitlistPatients(window.allPatients || []);
    
    // Handle search input
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const filteredPatients = (window.allPatients || []).filter(patient => {
            const name = `${patient.first_name} ${patient.last_name}`.toLowerCase();
            const cpf = (patient.cpf || '').toLowerCase();
            return name.includes(searchTerm) || cpf.includes(searchTerm);
        });
        showWaitlistPatients(filteredPatients);
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

function showWaitlistPatients(patients) {
    const dropdown = document.getElementById('waitlist-patient-dropdown');
    const hiddenInput = document.getElementById('waitlist-patient');
    const searchInput = document.getElementById('waitlist-patient-search');
    const nameInput = document.getElementById('waitlist-patient-name');
    const phoneInput = document.getElementById('waitlist-phone');
    const emailInput = document.getElementById('waitlist-email');
    
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
                hiddenInput.value = patient.id;
                searchInput.value = `${patient.first_name} ${patient.last_name}`;
                nameInput.value = `${patient.first_name} ${patient.last_name}`;
                if (patient.phone) phoneInput.value = patient.phone;
                if (patient.email) emailInput.value = patient.email;
                dropdown.style.display = 'none';
            });
            
            dropdown.appendChild(item);
        });
    }
    
    dropdown.style.display = 'block';
}

// Handle waitlist form submission
document.addEventListener('DOMContentLoaded', function() {
    const waitlistForm = document.getElementById('addToWaitlistForm');
    if (waitlistForm) {
        waitlistForm.addEventListener('submit', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Check if we're in edit mode
            const entryId = waitlistForm.dataset.entryId;
            if (entryId) {
                updateWaitlistEntry(entryId);
            } else {
                submitWaitlistEntry();
            }
        });
    }
});

function submitWaitlistEntry() {
    const form = document.getElementById('addToWaitlistForm');
    
    // Prevent double submission
    if (form.dataset.submitting === 'true') {
        return;
    }
    
    form.dataset.submitting = 'true';
    const formData = new FormData(form);
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Adicionando...';
    submitBtn.disabled = true;
    
    fetch('/dashboard/api/waiting-list/', {
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
            const modal = bootstrap.Modal.getInstance(document.getElementById('addToWaitlistModal'));
            modal.hide();
            
            // Reset form
            form.reset();
            delete form.dataset.submitting;
            delete form.dataset.entryId;
            
            // Show success message
            showNotification(data.message || 'Paciente adicionado à lista de espera com sucesso!', 'success');
            
            // Reload waitlist if on waitlist tab
            const waitlistTab = document.getElementById('waitlist-tab');
            if (waitlistTab && waitlistTab.style.display !== 'none') {
                loadWaitlist();
            }
        } else {
            delete form.dataset.submitting;
            showNotification('Erro ao adicionar à lista de espera: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('Error adding to waitlist:', error);
        delete form.dataset.submitting;
        showNotification('Erro ao adicionar à lista de espera. Tente novamente.', 'error');
    })
    .finally(() => {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

function loadWaitlist() {
    const loadingDiv = document.getElementById('waitlist-loading');
    const tableBody = document.getElementById('waitlist-table-body');
    const emptyDiv = document.getElementById('waitlist-empty');
    const tableCard = document.getElementById('waitlist-table-card');
    
    // Show loading
    if (loadingDiv) loadingDiv.style.display = 'block';
    if (tableBody) tableBody.innerHTML = '';
    if (emptyDiv) emptyDiv.style.display = 'none';
    if (tableCard) tableCard.style.display = 'block'; // Show table card by default
    
    // Build URL - load all entries (no status filter)
    let url = '/dashboard/api/waiting-list/';
    
    fetch(url, {
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (loadingDiv) loadingDiv.style.display = 'none';
        
        // Always show table card
        if (tableCard) {
            tableCard.style.display = 'block';
        }
        
        if (data.success && data.entries && data.entries.length > 0) {
            waitlistEntries = data.entries;
            displayWaitlistEntries(data.entries);
            if (emptyDiv) emptyDiv.style.display = 'none';
        } else {
            waitlistEntries = [];
            filteredWaitlistEntries = [];
            // Show empty state in table
            if (tableBody) {
                tableBody.innerHTML = `
                    <tr id="waitlist-empty-row">
                        <td colspan="6" class="text-center text-slate-500 py-5">
                            <p class="h6 mb-2" style="font-size: 1rem;">Nenhuma entrada encontrada.</p>
                            <p class="text-slate-400" style="font-size: 0.875rem;">Clique em "Adicionar à Lista" para adicionar o primeiro paciente.</p>
                        </td>
                    </tr>
                `;
            }
            if (emptyDiv) emptyDiv.style.display = 'none';
            // Update pagination to show 0
            if (document.getElementById('waitlist-total')) {
                document.getElementById('waitlist-total').textContent = '0';
                document.getElementById('waitlist-showing-start').textContent = '0';
                document.getElementById('waitlist-showing-end').textContent = '0';
                document.getElementById('waitlist-current-page').textContent = '1';
                document.getElementById('waitlist-total-pages').textContent = '1';
            }
        }
    })
    .catch(error => {
        console.error('Error loading waitlist:', error);
        if (loadingDiv) loadingDiv.style.display = 'none';
        if (tableCard) tableCard.style.display = 'block';
        showNotification('Erro ao carregar lista de espera.', 'error');
    });
}

// Waitlist pagination variables
let currentWaitlistPage = 1;
const waitlistPerPage = 10;
let filteredWaitlistEntries = [];

function displayWaitlistEntries(entries) {
    const tableBody = document.getElementById('waitlist-table-body');
    const tableCard = document.getElementById('waitlist-table-card');
    
    if (!tableBody) {
        console.error('waitlist-table-body not found');
        return;
    }
    
    // Ensure table card is visible
    if (tableCard) {
        tableCard.style.display = 'block';
    }
    
    // Store entries globally for filtering
    waitlistEntries = entries;
    
    // Apply urgency filter if set
    const urgencyFilter = document.getElementById('waitlist-urgency-filter')?.value;
    let filteredEntries = entries;
    if (urgencyFilter) {
        filteredEntries = entries.filter(entry => entry.urgency_level === urgencyFilter);
    }
    
    // Apply search filter if set
    const searchTerm = document.getElementById('waitlist-search')?.value.toLowerCase();
    if (searchTerm) {
        filteredEntries = filteredEntries.filter(entry => 
            entry.patient_name.toLowerCase().includes(searchTerm) ||
            (entry.phone && entry.phone.toLowerCase().includes(searchTerm)) ||
            (entry.email && entry.email.toLowerCase().includes(searchTerm))
        );
    }
    
    // Store filtered entries for pagination
    filteredWaitlistEntries = filteredEntries;
    
    // Reset to page 1 when filtering
    currentWaitlistPage = 1;
    
    // Display paginated entries
    displayWaitlistPage();
}

function displayWaitlistPage() {
    const tableBody = document.getElementById('waitlist-table-body');
    const emptyDiv = document.getElementById('waitlist-empty');
    const tableCard = document.getElementById('waitlist-table-card');
    
    if (!tableBody) return;
    
    const totalFiltered = filteredWaitlistEntries.length;
    const totalPages = Math.ceil(totalFiltered / waitlistPerPage) || 1;
    
    // Clear table body
    tableBody.innerHTML = '';
    
            // Show empty state if no entries
            if (totalFiltered === 0) {
                tableBody.innerHTML = `
                    <tr id="waitlist-empty-row">
                        <td colspan="6" class="text-center text-slate-500 py-5">
                            <p class="h6 mb-2" style="font-size: 1rem;">Nenhuma entrada encontrada.</p>
                            <p class="text-slate-400" style="font-size: 0.875rem;">Clique em "Adicionar à Lista" para adicionar o primeiro paciente.</p>
                        </td>
                    </tr>
                `;
        if (tableCard) tableCard.style.display = 'block';
        if (emptyDiv) emptyDiv.style.display = 'none';
    } else {
        if (tableCard) tableCard.style.display = 'block';
        if (emptyDiv) emptyDiv.style.display = 'none';
        // Calculate range
        const startIndex = (currentWaitlistPage - 1) * waitlistPerPage;
        const endIndex = Math.min(startIndex + waitlistPerPage, totalFiltered);
        
        // Create rows for current page
        for (let i = startIndex; i < endIndex; i++) {
            const entry = filteredWaitlistEntries[i];
            const createdDate = formatDate(entry.created_at);
            
            const row = document.createElement('tr');
            row.className = 'border-bottom waitlist-row';
            row.innerHTML = `
                <td class="py-2 px-3">
                    <span class="text-slate-900 fw-medium">
                        ${entry.patient_name}
                    </span>
                </td>
                <td class="py-2 px-3 text-slate-500" style="font-size: 0.875rem;">
                    ${entry.email || '<span class="text-slate-400">-</span>'}
                </td>
                <td class="py-2 px-3 text-slate-500" style="font-size: 0.875rem;">
                    ${entry.phone || '<span class="text-slate-400">-</span>'}
                </td>
                <td class="py-2 px-3" style="font-size: 0.875rem;">
                    ${getUrgencyDot(entry.urgency_level, entry.urgency_display)}
                </td>
                <td class="py-2 px-3 text-slate-500" style="font-size: 0.875rem;">
                    ${createdDate}
                </td>
                <td class="py-2 px-3" onclick="event.stopPropagation();">
                    <div class="d-flex align-items-center gap-2">
                        <button class="btn btn-sm btn-link text-primary p-1" onclick="convertWaitlistToAppointment(${entry.id})" title="Agendar">
                            <svg xmlns="http://www.w3.org/2000/svg" class="icon-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                        </button>
                        <button class="btn btn-sm btn-link text-slate-500 p-1" onclick="editWaitlistEntry(${entry.id})" title="Editar">
                            <svg xmlns="http://www.w3.org/2000/svg" class="icon-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                        </button>
                        <button class="btn btn-sm btn-link text-danger p-1" onclick="deleteWaitlistEntry(${entry.id})" title="Remover">
                            <svg xmlns="http://www.w3.org/2000/svg" class="icon-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                        </button>
                    </div>
                </td>
            `;
            tableBody.appendChild(row);
        }
    }
    
    // Update pagination info
    document.getElementById('waitlist-current-page').textContent = currentWaitlistPage;
    document.getElementById('waitlist-total-pages').textContent = totalPages;
    document.getElementById('waitlist-total').textContent = totalFiltered;
    document.getElementById('waitlist-showing-start').textContent = totalFiltered > 0 ? (currentWaitlistPage - 1) * waitlistPerPage + 1 : 0;
    document.getElementById('waitlist-showing-end').textContent = totalFiltered > 0 ? Math.min(currentWaitlistPage * waitlistPerPage, totalFiltered) : 0;
    
    // Update prev/next buttons
    const prevBtn = document.getElementById('waitlist-prev');
    const nextBtn = document.getElementById('waitlist-next');
    
    if (currentWaitlistPage <= 1 || totalFiltered === 0) {
        prevBtn.classList.add('disabled');
        prevBtn.style.pointerEvents = 'none';
        prevBtn.style.opacity = '0.5';
    } else {
        prevBtn.classList.remove('disabled');
        prevBtn.style.pointerEvents = 'auto';
        prevBtn.style.opacity = '1';
    }
    
    if (currentWaitlistPage >= totalPages || totalFiltered === 0) {
        nextBtn.classList.add('disabled');
        nextBtn.style.pointerEvents = 'none';
        nextBtn.style.opacity = '0.5';
    } else {
        nextBtn.classList.remove('disabled');
        nextBtn.style.pointerEvents = 'auto';
        nextBtn.style.opacity = '1';
    }
}

function changeWaitlistPage(direction) {
    const totalPages = Math.ceil(filteredWaitlistEntries.length / waitlistPerPage) || 1;
    const newPage = currentWaitlistPage + direction;
    
    if (newPage >= 1 && newPage <= totalPages) {
        currentWaitlistPage = newPage;
        displayWaitlistPage();
    }
}

function clearWaitlistFilters() {
    document.getElementById('waitlist-search').value = '';
    document.getElementById('waitlist-urgency-filter').value = '';
    filterWaitlist();
}

function getUrgencyClass(urgency) {
    switch(urgency) {
        case 'high': return 'bg-danger text-white';
        case 'medium': return 'bg-warning text-dark';
        case 'low': return 'bg-info text-white';
        default: return 'bg-secondary text-white';
    }
}

function getUrgencyIcon(urgency) {
    switch(urgency) {
        case 'high': return 'fas fa-exclamation-triangle';
        case 'medium': return 'fas fa-exclamation-circle';
        case 'low': return 'fas fa-info-circle';
        default: return 'fas fa-circle';
    }
}

function getStatusBadge(status) {
    const badges = {
        'pending': '<span class="badge bg-warning">Pendente</span>',
        'scheduled': '<span class="badge bg-success">Agendada</span>',
        'archived': '<span class="badge bg-secondary">Arquivada</span>'
    };
    return badges[status] || '<span class="badge bg-secondary">' + status + '</span>';
}

function getStatusBadgeInline(status, display) {
    const badges = {
        'pending': '<span class="d-inline-flex align-items-center"><span class="status-dot me-2" style="background-color: #fbbf24;"></span>Pendente</span>',
        'scheduled': '<span class="d-inline-flex align-items-center"><span class="status-dot bg-green-400 me-2"></span>Agendada</span>',
        'archived': '<span class="d-inline-flex align-items-center"><span class="status-dot bg-gray-300 me-2"></span>Arquivada</span>'
    };
    return badges[status] || '<span class="d-inline-flex align-items-center"><span class="status-dot bg-gray-300 me-2"></span>' + (display || status) + '</span>';
}

function getUrgencyBadge(urgency, display) {
    const urgencyIcon = getUrgencyIcon(urgency);
    let badgeClass = '';
    let iconColor = '';
    
    switch(urgency) {
        case 'high':
            badgeClass = 'badge bg-danger';
            iconColor = 'text-white';
            break;
        case 'medium':
            badgeClass = 'badge bg-warning text-dark';
            iconColor = 'text-dark';
            break;
        case 'low':
            badgeClass = 'badge bg-info';
            iconColor = 'text-white';
            break;
        default:
            badgeClass = 'badge bg-secondary';
            iconColor = 'text-white';
    }
    
    return `<span class="${badgeClass} d-inline-flex align-items-center">
        <i class="${urgencyIcon} ${iconColor} me-1" style="font-size: 0.75rem;"></i>
        ${display || urgency}
    </span>`;
}

function getUrgencyDot(urgency, display) {
    let dotColor = '';
    
    switch(urgency) {
        case 'high':
            dotColor = '#ef4444'; // red-500
            break;
        case 'medium':
            dotColor = '#f59e0b'; // amber-500
            break;
        case 'low':
            dotColor = '#3b82f6'; // blue-500
            break;
        default:
            dotColor = '#6b7280'; // gray-500
    }
    
    return `<span class="d-inline-flex align-items-center">
        <span class="status-dot me-2" style="background-color: ${dotColor};"></span>
        ${display || urgency}
    </span>`;
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR') + ' ' + date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function formatDate(dateString) {
    // Parse the date string (handles both ISO format and legacy format)
    let date;
    if (dateString.includes('T') || dateString.includes('+') || dateString.endsWith('Z')) {
        // ISO format with timezone
        date = new Date(dateString);
    } else {
        // Legacy format without timezone - assume UTC and convert to local
        // Format: 'YYYY-MM-DD HH:MM:SS'
        const dateTimeStr = dateString.replace(' ', 'T') + 'Z';
        date = new Date(dateTimeStr);
    }
    
    return date.toLocaleDateString('pt-BR', { 
        day: '2-digit', 
        month: '2-digit', 
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
    });
}

function filterWaitlist() {
    if (waitlistEntries && waitlistEntries.length > 0) {
        displayWaitlistEntries(waitlistEntries);
    } else {
        loadWaitlist();
    }
}

function refreshWaitlist() {
    loadWaitlist();
    showNotification('Lista de espera atualizada', 'success');
}

function convertWaitlistToAppointment(entryId) {
    // Show loading
    showNotification('Carregando dados do paciente...', 'info');
    
    fetch(`/dashboard/api/waiting-list/${entryId}/convert/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.entry) {
            const entry = data.entry;
            
            // Pre-fill appointment form
            if (entry.patient_id) {
                document.getElementById('appointment-patient').value = entry.patient_id;
                // Try to find and set patient name in search
                if (window.allPatients) {
                    const patient = window.allPatients.find(p => p.id == entry.patient_id);
                    if (patient) {
                        document.getElementById('appointment-patient-search').value = `${patient.first_name} ${patient.last_name}`;
                    }
                }
            }
            
            // Pre-fill notes with waitlist notes
            const notesField = document.getElementById('appointment-notes');
            if (notesField && entry.notes) {
                notesField.value = `[Lista de Espera] ${entry.notes}`;
            }
            
            // Pre-fill reason with preferred days/times if available
            const reasonField = document.getElementById('appointment-reason');
            if (reasonField && entry.preferred_days_times) {
                reasonField.value = `Preferências: ${entry.preferred_days_times}`;
            }
            
            // Show appointment modal
            showNewAppointmentModal();
            
            // Update waitlist entry status to scheduled
            updateWaitlistEntryStatus(entryId, 'scheduled');
            
            showNotification(data.message || 'Dados do paciente carregados. Preencha a data e horário.', 'success');
        } else {
            showNotification('Erro ao converter entrada: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('Error converting waitlist entry:', error);
        showNotification('Erro ao converter entrada. Tente novamente.', 'error');
    });
}

function updateWaitlistEntryStatus(entryId, status) {
    const formData = new FormData();
    formData.append('status', status);
    
    fetch(`/dashboard/api/waiting-list/${entryId}/`, {
        method: 'PATCH',
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reload waitlist
            loadWaitlist();
        }
    })
    .catch(error => {
        console.error('Error updating waitlist entry:', error);
    });
}

function editWaitlistEntry(entryId) {
    const entry = waitlistEntries.find(e => e.id === entryId);
    if (!entry) {
        showNotification('Entrada não encontrada', 'error');
        return;
    }
    
    // Store entry ID for update BEFORE showing modal
    const form = document.getElementById('addToWaitlistForm');
    form.dataset.entryId = entryId;
    
    // Change submit button text and modal title BEFORE showing
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-save me-1"></i>Salvar Alterações';
    
    const modalTitle = document.getElementById('addToWaitlistModalLabel');
    const originalTitle = modalTitle.innerHTML;
    modalTitle.innerHTML = '<i class="fas fa-edit me-2"></i>Editar Entrada da Lista de Espera';
    
    // Show modal first
    const modal = new bootstrap.Modal(document.getElementById('addToWaitlistModal'));
    
    // Set up patient search
    if (window.allPatients && window.allPatients.length > 0) {
        setupWaitlistPatientSearch();
    } else {
        loadPatientsAndDoctors()
            .then(() => {
                setupWaitlistPatientSearch();
            })
            .catch(error => {
                console.error('Error loading patients for waitlist edit:', error);
                // Still try to set up the search with empty patients
                setupWaitlistPatientSearch();
            });
    }
    
    // Pre-fill modal with entry data AFTER modal is shown
    const modalElement = document.getElementById('addToWaitlistModal');
    const fillFormData = function() {
        // Pre-fill all fields with entry data
        document.getElementById('waitlist-patient-name').value = entry.patient_name || '';
        document.getElementById('waitlist-phone').value = entry.phone || '';
        document.getElementById('waitlist-email').value = entry.email || '';
        document.getElementById('waitlist-preferred').value = entry.preferred_days_times || '';
        document.getElementById('waitlist-urgency').value = entry.urgency_level || 'medium';
        document.getElementById('waitlist-notes').value = entry.notes || '';
        
        if (entry.patient_id) {
            document.getElementById('waitlist-patient').value = entry.patient_id;
            if (window.allPatients) {
                const patient = window.allPatients.find(p => p.id == entry.patient_id);
                if (patient) {
                    document.getElementById('waitlist-patient-search').value = `${patient.first_name} ${patient.last_name}`;
                }
            }
        } else {
            document.getElementById('waitlist-patient').value = '';
            document.getElementById('waitlist-patient-search').value = '';
        }
        
        // The global listener will handle edit mode via dataset.entryId
        // No need to override onsubmit here
        
        // Remove listener after first use
        modalElement.removeEventListener('shown.bs.modal', fillFormData);
    };
    
    modalElement.addEventListener('shown.bs.modal', fillFormData, { once: true });
    
    // Also restore original state when modal is hidden
    modalElement.addEventListener('hidden.bs.modal', function restoreOriginalState() {
        form.reset();
        delete form.dataset.entryId;
        submitBtn.innerHTML = originalBtnText;
        modalTitle.innerHTML = originalTitle;
        // The global listener will handle new entries when entryId is not set
        modalElement.removeEventListener('hidden.bs.modal', restoreOriginalState);
    }, { once: true });
    
    modal.show();
}

function updateWaitlistEntry(entryId) {
    const form = document.getElementById('addToWaitlistForm');
    const formData = new FormData(form);
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Salvando...';
    submitBtn.disabled = true;
    
    fetch(`/dashboard/api/waiting-list/${entryId}/update/`, {
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
            const modal = bootstrap.Modal.getInstance(document.getElementById('addToWaitlistModal'));
            modal.hide();
            
            // Reset form
            form.reset();
            delete form.dataset.entryId;
            
            // Restore submit button
            submitBtn.innerHTML = '<i class="fas fa-clock me-1"></i>Adicionar à Lista de Espera';
            
            // Show success message
            showNotification('Entrada atualizada com sucesso!', 'success');
            
            // Reload waitlist
            loadWaitlist();
        } else {
            showNotification('Erro ao atualizar entrada: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('Error updating waitlist entry:', error);
        showNotification('Erro ao atualizar entrada. Tente novamente.', 'error');
    })
    .finally(() => {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

function deleteWaitlistEntry(entryId) {
    if (!confirm('Tem certeza que deseja remover esta entrada da lista de espera?')) {
        return;
    }
    
    fetch(`/dashboard/api/waiting-list/${entryId}/`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Entrada removida da lista de espera', 'success');
            loadWaitlist();
        } else {
            showNotification('Erro ao remover entrada: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting waitlist entry:', error);
        showNotification('Erro ao remover entrada. Tente novamente.', 'error');
    });
}

// ============================================================================
// BULK CANCEL APPOINTMENTS FUNCTIONS
// ============================================================================

function showBulkCancelModal() {
    const modal = new bootstrap.Modal(document.getElementById('bulkCancelModal'));
    
    // Reset form
    const form = document.getElementById('bulk-cancel-form');
    if (form) {
        form.reset();
    }
    
    // Set default dates (today to 30 days from now)
    const today = new Date();
    const futureDate = new Date();
    futureDate.setDate(today.getDate() + 30);
    
    const todayStr = today.toISOString().split('T')[0];
    // Get current time and round up to next 5 minutes for easier selection
    const minutes = today.getMinutes();
    const roundedMinutes = Math.ceil(minutes / 5) * 5;
    const roundedTime = new Date(today);
    roundedTime.setMinutes(roundedMinutes, 0, 0);
    // If rounded time is in the next hour, use it, otherwise use current hour
    if (roundedMinutes >= 60) {
        roundedTime.setHours(roundedTime.getHours() + 1);
        roundedTime.setMinutes(0, 0, 0);
    }
    const currentTime = roundedTime.toTimeString().slice(0, 5); // HH:MM format
    
    const fromDateInput = document.getElementById('cancel-from-date');
    const untilDateInput = document.getElementById('cancel-until-date');
    const fromTimeInput = document.getElementById('cancel-from-time');
    const untilTimeInput = document.getElementById('cancel-until-time');
    
    if (fromDateInput) {
        fromDateInput.value = todayStr;
        fromDateInput.min = todayStr; // Prevent selecting past dates
    }
    if (untilDateInput) {
        untilDateInput.value = futureDate.toISOString().split('T')[0];
        untilDateInput.min = todayStr; // Prevent selecting past dates
    }
    if (fromTimeInput) {
        fromTimeInput.value = currentTime;
    }
    if (untilTimeInput) {
        // Set to end of day (23:59)
        untilTimeInput.value = '23:59';
    }
    
    // Load cancellation reasons
    loadBulkCancellationReasons();
    
    // Hide preview initially
    const previewDiv = document.getElementById('bulk-cancel-preview');
    if (previewDiv) {
        previewDiv.style.display = 'none';
    }
    
    // Add event listeners for date and time changes to update preview and validate
    if (fromDateInput && untilDateInput) {
        const updatePreview = () => {
            const fromDate = fromDateInput.value;
            const untilDate = untilDateInput.value;
            const fromTime = fromTimeInput ? fromTimeInput.value : '';
            const untilTime = untilTimeInput ? untilTimeInput.value : '';
            
            // Ensure until date is not before from date
            if (fromDate && untilDate && untilDate < fromDate) {
                untilDateInput.value = fromDate;
            }
            
            // If same date, ensure until time is not before from time
            if (fromDate && untilDate && fromDate === untilDate && fromTime && untilTime) {
                if (untilTime < fromTime) {
                    untilTimeInput.value = fromTime;
                }
            }
            
            if (fromDate && untilDate && fromTime && untilTime) {
                previewAppointmentCount(fromDate, untilDate);
            } else {
                // Hide preview if dates or times are missing
                const previewDiv = document.getElementById('bulk-cancel-preview');
                if (previewDiv) {
                    previewDiv.style.display = 'none';
                }
            }
        };
        
        fromDateInput.addEventListener('change', updatePreview);
        untilDateInput.addEventListener('change', updatePreview);
        if (fromTimeInput) {
            fromTimeInput.addEventListener('change', updatePreview);
        }
        if (untilTimeInput) {
            untilTimeInput.addEventListener('change', updatePreview);
        }
    }
    
    modal.show();
}

function loadBulkCancellationReasons() {
    const select = document.getElementById('bulk-cancellation-reason');
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
                if (data.success && data.settings && data.settings.cancellation_reasons) {
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
                showNotification('Erro ao carregar motivos de cancelamento', 'error');
            });
    }
}

function previewAppointmentCount(fromDate, untilDate) {
    const fromTimeInput = document.getElementById('cancel-from-time');
    const untilTimeInput = document.getElementById('cancel-until-time');
    const excludeCompleted = document.getElementById('exclude-completed');
    
    if (!fromDate || !untilDate || !fromTimeInput || !untilTimeInput) {
        return;
    }
    
    const fromTime = fromTimeInput.value;
    const untilTime = untilTimeInput.value;
    
    if (!fromTime || !untilTime) {
        return;
    }
    
    // Build query string
    const params = new URLSearchParams({
        from_date: fromDate,
        until_date: untilDate,
        from_time: fromTime,
        until_time: untilTime,
        exclude_completed: excludeCompleted ? excludeCompleted.checked : true
    });
    
    // Fetch count from API
    fetch(`/dashboard/api/appointments/count-to-cancel/?${params.toString()}`)
        .then(response => response.json())
        .then(data => {
            const previewDiv = document.getElementById('bulk-cancel-preview');
            const previewCount = document.getElementById('preview-count');
            
            if (previewDiv && previewCount) {
                if (data.success) {
                    previewCount.textContent = data.count || 0;
                    previewDiv.style.display = 'block';
                } else {
                    previewDiv.style.display = 'none';
                }
            }
        })
        .catch(error => {
            console.error('Error counting appointments:', error);
            const previewDiv = document.getElementById('bulk-cancel-preview');
            if (previewDiv) {
                previewDiv.style.display = 'none';
            }
        });
}

function confirmBulkCancel() {
    const fromDateInput = document.getElementById('cancel-from-date');
    const untilDateInput = document.getElementById('cancel-until-date');
    const fromTimeInput = document.getElementById('cancel-from-time');
    const untilTimeInput = document.getElementById('cancel-until-time');
    const reasonSelect = document.getElementById('bulk-cancellation-reason');
    const excludeCompleted = document.getElementById('exclude-completed');
    const confirmBtn = document.getElementById('confirm-bulk-cancel-btn');
    
    if (!fromDateInput || !untilDateInput || !fromTimeInput || !untilTimeInput || !reasonSelect) {
        showNotification('Erro: Campos não encontrados', 'error');
        return;
    }
    
    const fromDate = fromDateInput.value;
    const untilDate = untilDateInput.value;
    const fromTime = fromTimeInput.value;
    const untilTime = untilTimeInput.value;
    const reason = reasonSelect.value;
    
    // Validate inputs
    if (!fromDate || !untilDate) {
        showNotification('Por favor, preencha ambas as datas', 'error');
        return;
    }
    
    if (!fromTime || !untilTime) {
        showNotification('Por favor, preencha ambos os horários', 'error');
        return;
    }
    
    // Validate dates are not in the past
    // Compare dates as strings to avoid timezone issues
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0]; // YYYY-MM-DD format
    
    if (fromDate < todayStr) {
        showNotification('A data inicial não pode ser no passado', 'error');
        fromDateInput.focus();
        return;
    }
    
    // If from_date is today, validate that from_time is not in the past
    // Allow >= current_time to allow canceling appointments starting from now
    const now = new Date();
    const currentTime = now.toTimeString().slice(0, 5); // HH:MM format
    
    if (fromDate === todayStr && fromTime < currentTime) {
        showNotification('O horário inicial não pode ser no passado', 'error');
        fromTimeInput.focus();
        return;
    }
    
    // If same date, validate times
    if (fromDate === untilDate && fromTime > untilTime) {
        showNotification('O horário final não pode ser anterior ao horário inicial no mesmo dia', 'error');
        untilTimeInput.focus();
        return;
    }
    
    // If until_date is today, validate that until_time is not in the past
    if (untilDate === todayStr && untilTime < currentTime) {
        showNotification('O horário final não pode ser no passado para o dia de hoje', 'error');
        untilTimeInput.focus();
        return;
    }
    
    if (!reason) {
        showNotification('Por favor, selecione um motivo do cancelamento', 'error');
        reasonSelect.focus();
        return;
    }
    
    // Confirm action
    if (!confirm(`Tem certeza que deseja cancelar todas as consultas de ${fromDate} ${fromTime} até ${untilDate} ${untilTime}?\n\nEsta ação não pode ser desfeita!`)) {
        return;
    }
    
    // Disable button and show loading
    const originalText = confirmBtn.innerHTML;
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Cancelando...';
    
    // Prepare form data
    const formData = new FormData();
    formData.append('from_date', fromDate);
    formData.append('until_date', untilDate);
    formData.append('from_time', fromTime);
    formData.append('until_time', untilTime);
    formData.append('cancellation_reason', reason);
    formData.append('exclude_completed', excludeCompleted ? excludeCompleted.checked : true);
    
    // Make API call
    fetch('/dashboard/api/appointments/bulk-cancel/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('bulkCancelModal'));
            if (modal) {
                modal.hide();
            }
            
            // Reload calendar if it exists
            if (typeof refreshCalendar === 'function') {
                refreshCalendar();
            } else if (typeof initializeFullCalendar === 'function') {
                // Reinitialize calendar to show updated appointments
                setTimeout(() => {
                    initializeFullCalendar();
                }, 500);
            }
            
            // Reload agenda stats if function exists
            if (typeof refreshAgendaStats === 'function') {
                refreshAgendaStats();
            }
        } else {
            showNotification('Erro: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('Error bulk canceling appointments:', error);
        showNotification('Erro ao cancelar consultas. Tente novamente.', 'error');
    })
    .finally(() => {
        // Restore button state
        confirmBtn.innerHTML = originalText;
        confirmBtn.disabled = false;
    });
}

// ============================================================================
// BLOCK CALENDAR (BLOQUEAR AGENDA) FUNCTIONS
// ============================================================================

function showBlockCalendarModal() {
    const modal = new bootstrap.Modal(document.getElementById('blockCalendarModal'));
    const form = document.getElementById('block-calendar-form');
    if (form) {
        form.reset();
    }
    const today = new Date();
    const futureDate = new Date();
    futureDate.setDate(today.getDate() + 7);
    const todayStr = today.toISOString().split('T')[0];
    const fromDateInput = document.getElementById('block-from-date');
    const untilDateInput = document.getElementById('block-until-date');
    const fromTimeInput = document.getElementById('block-from-time');
    const untilTimeInput = document.getElementById('block-until-time');
    if (fromDateInput) {
        fromDateInput.value = todayStr;
        fromDateInput.min = todayStr;
    }
    if (untilDateInput) {
        untilDateInput.value = futureDate.toISOString().split('T')[0];
        untilDateInput.min = todayStr;
    }
    if (fromTimeInput) {
        fromTimeInput.value = '08:00';
    }
    if (untilTimeInput) {
        untilTimeInput.value = '18:00';
    }
    modal.show();
}

function confirmBlockCalendar() {
    const fromDateInput = document.getElementById('block-from-date');
    const untilDateInput = document.getElementById('block-until-date');
    const fromTimeInput = document.getElementById('block-from-time');
    const untilTimeInput = document.getElementById('block-until-time');
    const reasonInput = document.getElementById('block-reason');
    const confirmBtn = document.getElementById('confirm-block-calendar-btn');
    if (!fromDateInput || !untilDateInput || !fromTimeInput || !untilTimeInput) {
        showNotification('Erro: Campos não encontrados', 'error');
        return;
    }
    const fromDate = fromDateInput.value;
    const untilDate = untilDateInput.value;
    const fromTime = fromTimeInput.value;
    const untilTime = untilTimeInput.value;
    const reason = reasonInput ? reasonInput.value.trim() : '';
    if (!fromDate || !untilDate || !fromTime || !untilTime) {
        showNotification('Por favor, preencha data e horário inicial e final', 'error');
        return;
    }
    // Use local date so "today" matches the user's calendar (toISOString is UTC)
    const now = new Date();
    const todayStr = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
    if (fromDate < todayStr) {
        showNotification('A data inicial não pode ser no passado', 'error');
        return;
    }
    if (untilDate < todayStr) {
        showNotification('A data final não pode ser no passado', 'error');
        return;
    }
    const currentTime = now.toTimeString().slice(0, 5);
    if (fromDate === todayStr && fromTime < currentTime) {
        showNotification('O horário inicial não pode ser no passado', 'error');
        return;
    }
    if (fromDate === untilDate && fromTime >= untilTime) {
        showNotification('O horário final deve ser posterior ao horário inicial', 'error');
        return;
    }
    const originalText = confirmBtn.innerHTML;
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Bloqueando...';
    const formData = new FormData();
    formData.append('from_date', fromDate);
    formData.append('until_date', untilDate);
    formData.append('from_time', fromTime);
    formData.append('until_time', untilTime);
    if (reason) {
        formData.append('reason', reason);
    }
    fetch('/dashboard/api/calendar-block/create/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('blockCalendarModal'));
            if (modal) {
                modal.hide();
            }
            if (typeof refreshCalendar === 'function') {
                refreshCalendar();
            } else if (typeof calendar !== 'undefined' && calendar && typeof calendar.refetchEvents === 'function') {
                calendar.refetchEvents();
            }
            if (typeof refreshAgendaStats === 'function') {
                refreshAgendaStats();
            }
        } else {
            showNotification('Erro: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('Error creating calendar block:', error);
        showNotification('Erro ao bloquear agenda. Tente novamente.', 'error');
    })
    .finally(() => {
        confirmBtn.innerHTML = originalText;
        confirmBtn.disabled = false;
    });
}

// Show block details modal when user clicks a calendar block
function showBlockDetailsModal(blockEvent) {
    const idStr = blockEvent.id;
    const numericId = typeof idStr === 'string' && idStr.startsWith('block-')
        ? parseInt(idStr.replace('block-', ''), 10)
        : parseInt(idStr, 10);
    if (isNaN(numericId)) {
        showNotification('ID do bloqueio inválido', 'error');
        return;
    }
    const start = blockEvent.start;
    const end = blockEvent.end;
    const reason = (blockEvent.extendedProps && blockEvent.extendedProps.reason) || '';

    function formatDt(d) {
        if (!d) return '-';
        const date = d.getDate().toString().padStart(2, '0');
        const month = (d.getMonth() + 1).toString().padStart(2, '0');
        const year = d.getFullYear();
        const hours = d.getHours().toString().padStart(2, '0');
        const minutes = d.getMinutes().toString().padStart(2, '0');
        return date + '/' + month + '/' + year + ' ' + hours + ':' + minutes;
    }
    const periodText = (start && end) ? (formatDt(start) + ' até ' + formatDt(end)) : '-';
    const descriptionText = reason.trim() || 'Sem descrição';

    document.getElementById('block-details-id').value = numericId;
    document.getElementById('block-details-period').textContent = periodText;
    document.getElementById('block-details-description').textContent = descriptionText;

    const modal = new bootstrap.Modal(document.getElementById('blockDetailsModal'));
    modal.show();
}

function confirmRemoveBlock() {
    const idEl = document.getElementById('block-details-id');
    const blockId = idEl ? idEl.value : null;
    if (!blockId) {
        showNotification('Bloqueio não encontrado', 'error');
        return;
    }
    if (!confirm('Remover este bloqueio da agenda? O período voltará a ficar disponível para agendamentos.')) {
        return;
    }
    const btn = document.getElementById('confirm-remove-block-btn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Removendo...';

    const formData = new FormData();
    formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

    fetch('/dashboard/api/calendar-block/' + blockId + '/delete/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('blockDetailsModal'));
            if (modal) modal.hide();
            if (typeof calendar !== 'undefined' && calendar && typeof calendar.refetchEvents === 'function') {
                calendar.refetchEvents();
            }
            if (typeof refreshAgendaStats === 'function') refreshAgendaStats();
        } else {
            showNotification('Erro: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('Error removing block:', error);
        showNotification('Erro ao remover bloqueio. Tente novamente.', 'error');
    })
    .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}