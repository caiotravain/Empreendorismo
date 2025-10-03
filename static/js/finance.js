// Finance Tab Functions
function loadFinanceData() {
    // First, try to sync appointment income automatically
    fetch('/dashboard/api/appointments/sync-income/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(syncData => {
        if (syncData.success && syncData.income_created_count > 0) {
            console.log(`Auto-sync: ${syncData.income_created_count} receitas criadas automaticamente`);
        }
    })
    .catch(error => {
        console.log('Auto-sync failed or no income to sync:', error);
    })
    .finally(() => {
        // Then load expenses and income data via AJAX
        Promise.all([
            fetch('/dashboard/api/expenses/').then(response => response.json()),
            fetch('/dashboard/api/incomes/').then(response => response.json())
        ])
        .then(([expensesData, incomesData]) => {
            if (expensesData.success) {
                updateExpensesList(expensesData.expenses);
                updateExpenseTotals(expensesData.expenses);
            } else {
                console.error('Error loading expenses:', expensesData.error);
                showAlert('Erro ao carregar despesas: ' + expensesData.error, 'danger');
            }
            
            if (incomesData.success) {
                updateIncomesList(incomesData.incomes);
                updateIncomeTotals(incomesData.incomes);
            } else {
                console.error('Error loading incomes:', incomesData.error);
                showAlert('Erro ao carregar receitas: ' + incomesData.error, 'danger');
            }
            
            // Update filter dropdowns with both expenses and incomes
            updateFilterDropdowns(expensesData.expenses || [], incomesData.incomes || []);
            
            // Add event listeners to filter dropdowns
            setupFilterEventListeners();
            
            // Update net income
            updateNetIncome(expensesData.expenses || [], incomesData.incomes || []);
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Erro ao carregar dados financeiros', 'danger');
        });
    });
}

function updateFilterDropdowns(expenses, incomes = []) {
    // Get unique years from both expenses and incomes
    const expenseYears = expenses.map(expense => {
        const date = new Date(expense.expense_date.split('/').reverse().join('-'));
        return date.getFullYear();
    });
    
    const incomeYears = incomes.map(income => {
        const date = new Date(income.income_date.split('/').reverse().join('-'));
        return date.getFullYear();
    });
    
    const years = [...new Set([...expenseYears, ...incomeYears])].sort((a, b) => b - a);
    
    // Add current year if not present
    const currentYear = new Date().getFullYear();
    if (!years.includes(currentYear)) {
        years.unshift(currentYear);
    }
    
    // Update year dropdown
    const yearSelect = document.getElementById('year-filter');
    if (yearSelect) {
        yearSelect.innerHTML = '<option value="">Todos os anos</option>';
        years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            if (year === currentYear) {
                option.selected = true;
            }
            yearSelect.appendChild(option);
        });
    }
    
    // Update month dropdown
    const monthSelect = document.getElementById('month-filter');
    if (monthSelect) {
        const months = [
            { value: 1, name: 'Janeiro' },
            { value: 2, name: 'Fevereiro' },
            { value: 3, name: 'Março' },
            { value: 4, name: 'Abril' },
            { value: 5, name: 'Maio' },
            { value: 6, name: 'Junho' },
            { value: 7, name: 'Julho' },
            { value: 8, name: 'Agosto' },
            { value: 9, name: 'Setembro' },
            { value: 10, name: 'Outubro' },
            { value: 11, name: 'Novembro' },
            { value: 12, name: 'Dezembro' }
        ];
        
        monthSelect.innerHTML = '<option value="">Todos os meses</option>';
        months.forEach(month => {
            const option = document.createElement('option');
            option.value = month.value;
            option.textContent = month.name;
            monthSelect.appendChild(option);
        });
    }
}

function updateExpensesList(expenses) {
    const expensesList = document.getElementById('expenses-list');
    if (!expensesList) return;
    
    if (expenses.length === 0) {
        expensesList.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-receipt fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">Nenhuma despesa encontrada</h5>
                <p class="text-muted">Clique em "Nova Despesa" para começar a registrar suas despesas.</p>
            </div>
        `;
        return;
    }
    
    let tableHtml = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Data</th>
                        <th>Descrição</th>
                        <th>Categoria</th>
                        <th>Fornecedor</th>
                        <th>Valor</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    expenses.forEach(expense => {
        tableHtml += `
            <tr>
                <td>${expense.expense_date}</td>
                <td>
                    <div>
                        <strong>${expense.description}</strong>
                        ${expense.notes ? `<br><small class="text-muted">${expense.notes.substring(0, 50)}${expense.notes.length > 50 ? '...' : ''}</small>` : ''}
                    </div>
                </td>
                <td>
                    <span class="badge bg-secondary">${expense.category}</span>
                </td>
                <td>${expense.vendor || '-'}</td>
                <td>
                    <strong class="text-primary">${expense.formatted_amount}</strong>
                </td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-outline-primary" onclick="viewExpense(${expense.id})" title="Ver detalhes">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteExpense(${expense.id})" title="Excluir despesa">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    tableHtml += `
                </tbody>
            </table>
        </div>
    `;
    
    expensesList.innerHTML = tableHtml;
}

function updateExpenseTotals(expenses) {
    // Calculate totals
    const totalAmount = expenses.reduce((sum, expense) => sum + expense.amount, 0);
    const totalCount = expenses.length;
    
    // Update total amount
    const totalAmountElement = document.getElementById('total-expenses-amount');
    if (totalAmountElement) {
        totalAmountElement.textContent = `R$ ${totalAmount.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.')}`;
    }
    
    // Update total count
    const totalCountElement = document.getElementById('total-expenses-count');
    if (totalCountElement) {
        totalCountElement.textContent = totalCount;
    }
    
    // Update category breakdown
    updateCategoryBreakdown(expenses);
}

function updateIncomesList(incomes) {
    const incomesList = document.getElementById('incomes-list');
    const loadingIncomes = document.getElementById('loading-incomes');
    
    if (loadingIncomes) {
        loadingIncomes.style.display = 'none';
    }
    
    if (incomes.length === 0) {
        incomesList.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-chart-line fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">Nenhuma receita encontrada</h5>
                <p class="text-muted">Adicione uma nova receita para começar</p>
            </div>
        `;
        return;
    }
    
    let tableHtml = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Data</th>
                        <th>Descrição</th>
                        <th>Categoria</th>
                        <th>Forma de Pagamento</th>
                        <th>Valor</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    incomes.forEach(income => {
        tableHtml += `
            <tr>
                <td>${income.income_date}</td>
                <td>
                    <div>
                        <strong>${income.description}</strong>
                        ${income.notes ? `<br><small class="text-muted">${income.notes.substring(0, 50)}${income.notes.length > 50 ? '...' : ''}</small>` : ''}
                    </div>
                </td>
                <td>
                    <span class="badge bg-success">${income.category_display}</span>
                </td>
                <td>${income.payment_method_display || '-'}</td>
                <td>
                    <strong class="text-success">R$ ${parseFloat(income.amount).toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.')}</strong>
                </td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-outline-success" onclick="viewIncome(${income.id})" title="Ver detalhes">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteIncome(${income.id})" title="Excluir receita">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    tableHtml += `
                </tbody>
            </table>
        </div>
    `;
    
    incomesList.innerHTML = tableHtml;
}

function updateIncomeTotals(incomes) {
    const totalAmount = incomes.reduce((sum, income) => sum + parseFloat(income.amount), 0);
    
    document.getElementById('total-income-amount').textContent = `R$ ${totalAmount.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.')}`;
}

function updateNetIncome(expenses, incomes) {
    const totalExpenses = expenses.reduce((sum, expense) => sum + parseFloat(expense.amount), 0);
    const totalIncomes = incomes.reduce((sum, income) => sum + parseFloat(income.amount), 0);
    const netIncome = totalIncomes - totalExpenses;
    
    const netIncomeElement = document.getElementById('net-income-amount');
    netIncomeElement.textContent = `R$ ${netIncome.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.')}`;
    
    // Change color based on positive/negative
    const cardElement = netIncomeElement.closest('.card');
    if (netIncome >= 0) {
        cardElement.className = 'card border-0 shadow-sm bg-success text-white';
    } else {
        cardElement.className = 'card border-0 shadow-sm bg-danger text-white';
    }
}

function updateCategoryBreakdown(expenses) {
    const categoryTotals = {};
    expenses.forEach(expense => {
        if (!categoryTotals[expense.category]) {
            categoryTotals[expense.category] = 0;
        }
        categoryTotals[expense.category] += expense.amount;
    });
    
    // Find or create category breakdown section
    let categorySection = document.getElementById('category-breakdown')?.closest('.card');
    if (!categorySection) {
        // Create category breakdown section if it doesn't exist
        const expensesCard = document.querySelector('#expenses-list').closest('.card');
        const categoryHtml = `
            <div class="col-12 mt-4">
                <div class="card border-0 shadow-sm">
                    <div class="card-header bg-light">
                        <h6 class="mb-0">
                            <i class="fas fa-chart-pie me-2"></i>Despesas por Categoria
                        </h6>
                    </div>
                    <div class="card-body" id="category-breakdown">
                        <!-- Categories will be loaded here -->
                    </div>
                </div>
            </div>
        `;
        expensesCard.parentNode.insertAdjacentHTML('afterend', categoryHtml);
        categorySection = document.getElementById('category-breakdown').closest('.card');
    }
    
    const categoryBreakdown = document.getElementById('category-breakdown');
    if (categoryBreakdown) {
        let categoryHtml = '<div class="row">';
        Object.entries(categoryTotals).forEach(([category, amount]) => {
            categoryHtml += `
                <div class="col-md-4 col-lg-3 mb-3">
                    <div class="d-flex justify-content-between align-items-center p-2 border rounded">
                        <span class="fw-medium">${category}</span>
                        <span class="text-primary fw-bold">R$ ${amount.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.')}</span>
                    </div>
                </div>
            `;
        });
        categoryHtml += '</div>';
        categoryBreakdown.innerHTML = categoryHtml;
    }
}

function showExpenseModal() {
    const modal = new bootstrap.Modal(document.getElementById('expenseModal'));
    
    // Set today's date as default
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('expense-date').value = today;
    
    // Clear form
    document.getElementById('expenseForm').reset();
    document.getElementById('expense-date').value = today;
    
    modal.show();
}

function showIncomeModal() {
    const modal = new bootstrap.Modal(document.getElementById('incomeModal'));
    
    // Set today's date as default
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('income-date').value = today;
    
    // Clear form
    document.getElementById('incomeForm').reset();
    document.getElementById('income-date').value = today;
    
    modal.show();
}

function filterExpenses() {
    const year = document.getElementById('year-filter').value;
    const month = document.getElementById('month-filter').value;
    
    // Build API URL with parameters
    let apiUrl = '/dashboard/api/expenses/';
    const params = new URLSearchParams();
    if (year) params.append('year', year);
    if (month) params.append('month', month);
    
    if (params.toString()) {
        apiUrl += '?' + params.toString();
    }
    
    // Load filtered data
    fetch(apiUrl)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateExpensesList(data.expenses);
                updateExpenseTotals(data.expenses);
            } else {
                console.error('Error loading filtered expenses:', data.error);
                showAlert('Erro ao carregar despesas filtradas: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Erro ao carregar despesas filtradas', 'danger');
        });
}

function filterIncomes() {
    const year = document.getElementById('year-filter').value;
    const month = document.getElementById('month-filter').value;
    
    // Build API URL with parameters
    let apiUrl = '/dashboard/api/incomes/';
    const params = new URLSearchParams();
    if (year) params.append('year', year);
    if (month) params.append('month', month);
    
    if (params.toString()) {
        apiUrl += '?' + params.toString();
    }
    
    // Load filtered data
    fetch(apiUrl)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateIncomesList(data.incomes);
                updateIncomeTotals(data.incomes);
            } else {
                console.error('Error loading filtered incomes:', data.error);
                showAlert('Erro ao carregar receitas filtradas: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Erro ao carregar receitas filtradas', 'danger');
        });
}

function filterFinanceData() {
    const year = document.getElementById('year-filter').value;
    const month = document.getElementById('month-filter').value;
    
    // Build API URLs with parameters
    let expensesApiUrl = '/dashboard/api/expenses/';
    let incomesApiUrl = '/dashboard/api/incomes/';
    const params = new URLSearchParams();
    if (year) params.append('year', year);
    if (month) params.append('month', month);
    
    if (params.toString()) {
        expensesApiUrl += '?' + params.toString();
        incomesApiUrl += '?' + params.toString();
    }
    
    // Load filtered data for both expenses and incomes
    Promise.all([
        fetch(expensesApiUrl).then(response => response.json()),
        fetch(incomesApiUrl).then(response => response.json())
    ])
    .then(([expensesData, incomesData]) => {
        if (expensesData.success) {
            updateExpensesList(expensesData.expenses);
            updateExpenseTotals(expensesData.expenses);
        } else {
            console.error('Error loading filtered expenses:', expensesData.error);
            showAlert('Erro ao carregar despesas filtradas: ' + expensesData.error, 'danger');
        }
        
        if (incomesData.success) {
            updateIncomesList(incomesData.incomes);
            updateIncomeTotals(incomesData.incomes);
        } else {
            console.error('Error loading filtered incomes:', incomesData.error);
            showAlert('Erro ao carregar receitas filtradas: ' + incomesData.error, 'danger');
        }
        
        // Update net income with filtered data
        updateNetIncome(expensesData.expenses || [], incomesData.incomes || []);
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Erro ao carregar dados filtrados', 'danger');
    });
}

// Setup event listeners for filter dropdowns
function setupFilterEventListeners() {
    const yearFilter = document.getElementById('year-filter');
    const monthFilter = document.getElementById('month-filter');
    
    console.log('Setting up filter event listeners...');
    console.log('Year filter found:', !!yearFilter);
    console.log('Month filter found:', !!monthFilter);
    
    if (yearFilter) {
        // Remove existing event listeners to avoid duplicates
        yearFilter.removeEventListener('change', filterFinanceData);
        yearFilter.addEventListener('change', filterFinanceData);
        console.log('Year filter event listener added');
    }
    
    if (monthFilter) {
        // Remove existing event listeners to avoid duplicates
        monthFilter.removeEventListener('change', filterFinanceData);
        monthFilter.addEventListener('change', filterFinanceData);
        console.log('Month filter event listener added');
    }
}

// Make function globally available
window.filterFinanceData = filterFinanceData;

// Handle form submissions
document.addEventListener('DOMContentLoaded', function() {
    const expenseForm = document.getElementById('expenseForm');
    if (expenseForm) {
        expenseForm.addEventListener('submit', function(e) {
            e.preventDefault();
            createExpense();
        });
    }
    
    const incomeForm = document.getElementById('incomeForm');
    if (incomeForm) {
        incomeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            createIncome();
        });
    }
});

function createExpense() {
    const form = document.getElementById('expenseForm');
    const formData = new FormData(form);
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Salvando...';
    submitBtn.disabled = true;
    
    fetch('/dashboard/api/expenses/create/', {
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
            const modal = bootstrap.Modal.getInstance(document.getElementById('expenseModal'));
            modal.hide();
            
            // Show success message
            showAlert('Despesa criada com sucesso!', 'success');
            
            // Reload finance data instead of full page reload
            loadFinanceData();
        } else {
            showAlert(data.error || 'Erro ao criar despesa', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Erro ao criar despesa', 'danger');
    })
    .finally(() => {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

function createIncome() {
    const form = document.getElementById('incomeForm');
    const formData = new FormData(form);
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Salvando...';
    submitBtn.disabled = true;
    
    fetch('/dashboard/api/incomes/create/', {
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
            const modal = bootstrap.Modal.getInstance(document.getElementById('incomeModal'));
            modal.hide();
            
            // Show success message
            showAlert('Receita criada com sucesso!', 'success');
            
            // Reload finance data instead of full page reload
            loadFinanceData();
        } else {
            showAlert(data.error || 'Erro ao criar receita', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Erro ao criar receita', 'danger');
    })
    .finally(() => {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

function viewExpense(expenseId) {
    // For now, just show a placeholder
    // In a real implementation, you would fetch expense details
    const modal = new bootstrap.Modal(document.getElementById('expenseDetailsModal'));
    document.getElementById('expense-details-content').innerHTML = `
        <div class="text-center">
            <i class="fas fa-receipt fa-3x text-muted mb-3"></i>
            <h5>Detalhes da Despesa #${expenseId}</h5>
            <p class="text-muted">Funcionalidade em desenvolvimento...</p>
        </div>
    `;
    modal.show();
}

function viewIncome(incomeId) {
    // For now, just show a placeholder
    // In a real implementation, you would fetch income details
    const modal = new bootstrap.Modal(document.getElementById('incomeDetailsModal'));
    document.getElementById('income-details-content').innerHTML = `
        <div class="text-center">
            <i class="fas fa-chart-line fa-3x text-muted mb-3"></i>
            <h5>Detalhes da Receita #${incomeId}</h5>
            <p class="text-muted">Funcionalidade em desenvolvimento...</p>
        </div>
    `;
    modal.show();
}

function syncAppointmentIncome() {
    if (confirm('Deseja sincronizar as receitas das consultas confirmadas/concluídas? Isso criará registros de receita para todas as consultas que têm valor mas ainda não têm receita registrada.')) {
        // Show loading state
        const syncBtn = document.querySelector('[onclick="syncAppointmentIncome()"]');
        const originalText = syncBtn.innerHTML;
        syncBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Sincronizando...';
        syncBtn.disabled = true;
        
        fetch('/dashboard/api/appointments/sync-income/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert(data.message, 'success');
                // Reload finance data to show new income records
                loadFinanceData();
            } else {
                showAlert('Erro: ' + (data.error || 'Erro desconhecido'), 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Erro ao sincronizar receitas', 'danger');
        })
        .finally(() => {
            // Restore button state
            syncBtn.innerHTML = originalText;
            syncBtn.disabled = false;
        });
    }
}


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

function showAlert(message, type) {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to page
    document.body.appendChild(alertDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 5000);
}

// Delete functions
function deleteExpense(expenseId) {
    if (confirm('Tem certeza que deseja excluir esta despesa? Esta ação não pode ser desfeita.')) {
        // Show loading state
        const deleteBtn = event.target.closest('button');
        const originalContent = deleteBtn.innerHTML;
        deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        deleteBtn.disabled = true;
        
        fetch(`/dashboard/api/expenses/delete/${expenseId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('Despesa excluída com sucesso!', 'success');
                // Reload finance data
                loadFinanceData();
            } else {
                showAlert('Erro ao excluir despesa: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Erro ao excluir despesa', 'danger');
        })
        .finally(() => {
            // Restore button state
            deleteBtn.innerHTML = originalContent;
            deleteBtn.disabled = false;
        });
    }
}

function deleteIncome(incomeId) {
    if (confirm('Tem certeza que deseja excluir esta receita? Esta ação não pode ser desfeita.')) {
        // Show loading state
        const deleteBtn = event.target.closest('button');
        const originalContent = deleteBtn.innerHTML;
        deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        deleteBtn.disabled = true;
        
        fetch(`/dashboard/api/incomes/delete/${incomeId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('Receita excluída com sucesso!', 'success');
                // Reload finance data
                loadFinanceData();
            } else {
                showAlert('Erro ao excluir receita: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Erro ao excluir receita', 'danger');
        })
        .finally(() => {
            // Restore button state
            deleteBtn.innerHTML = originalContent;
            deleteBtn.disabled = false;
        });
    }
}

// Make functions globally available
window.deleteExpense = deleteExpense;
window.deleteIncome = deleteIncome;
