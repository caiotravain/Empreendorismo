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
        // Get current month and year for default filtering
        const now = new Date();
        const currentYear = now.getFullYear();
        const currentMonth = now.getMonth() + 1;
        
        // Then load expenses and income data via AJAX with current month filter
        Promise.all([
            fetch(`/dashboard/api/expenses/?year=${currentYear}&month=${currentMonth}`).then(response => response.json()),
            fetch(`/dashboard/api/incomes/?year=${currentYear}&month=${currentMonth}`).then(response => response.json())
        ])
        .then(([expensesData, incomesData]) => {
            const expenses = expensesData.success ? (expensesData.expenses || []) : [];
            const incomes = incomesData.success ? (incomesData.incomes || []) : [];
            
            if (expensesData.success) {
                updateExpensesList(expenses);
                updateExpenseTotals(expenses);
            } else {
                console.error('Error loading expenses:', expensesData.error);
                showAlert('Erro ao carregar despesas: ' + expensesData.error, 'danger');
            }
            
            if (incomesData.success) {
                updateIncomesList(incomes);
                updateIncomeTotals(incomes);
            } else {
                console.error('Error loading incomes:', incomesData.error);
                showAlert('Erro ao carregar receitas: ' + incomesData.error, 'danger');
            }
            
            // Update unified transactions table
            if (typeof updateUnifiedTransactionsTable === 'function') {
                updateUnifiedTransactionsTable(incomes, expenses);
            }
            
            // Update charts
            // Cash flow chart always shows last 6 months, not filtered data
            updateCashFlowChart();
            // Expenses category chart uses filtered data
            updateExpensesCategoryChart(expenses);
            
            // Update filter dropdowns with both expenses and incomes
            updateFilterDropdowns(expenses, incomes);
            
            // Add event listeners to filter dropdowns
            setupFilterEventListeners();
            
            // Update net income
            updateNetIncome(expenses, incomes);
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
        
        const currentMonth = new Date().getMonth() + 1; // getMonth() returns 0-11
        
        monthSelect.innerHTML = '<option value="">Todos os meses</option>';
        months.forEach(month => {
            const option = document.createElement('option');
            option.value = month.value;
            option.textContent = month.name;
            // Select current month by default
            if (month.value === currentMonth) {
                option.selected = true;
            }
            monthSelect.appendChild(option);
        });
    }
}

function updateExpensesList(expenses) {
    const expensesList = document.getElementById('expenses-list');
    // If unified table exists, skip updating old list
    if (document.getElementById('transactions-table-body')) {
        return;
    }
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
    // If unified table exists, skip updating old list
    if (document.getElementById('transactions-table-body')) {
        return;
    }
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
    if (netIncomeElement) {
    netIncomeElement.textContent = `R$ ${netIncome.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.')}`;
    
        // Update color based on positive/negative (keep minimalist design)
        netIncomeElement.className = `mb-0 text-slate-900 fw-bold`;
        if (netIncome < 0) {
            netIncomeElement.className = `mb-0 text-rose-600 fw-bold`;
        }
    }
}

// Unified Transactions Table Function
function updateUnifiedTransactionsTable(incomes, expenses) {
    const tbody = document.getElementById('transactions-table-body');
    if (!tbody) return;
    
    // Combine and sort transactions by date (newest first)
    const transactions = [];
    
    // Add incomes
    (incomes || []).forEach(income => {
        transactions.push({
            id: income.id,
            type: 'income',
            date: income.income_date,
            description: income.description,
            category: income.category_display || income.category,
            amount: parseFloat(income.amount),
            formatted_amount: income.formatted_amount || formatCurrency(income.amount),
            notes: income.notes,
            payment_method: income.payment_method_display || income.payment_method
        });
    });
    
    // Add expenses
    (expenses || []).forEach(expense => {
        transactions.push({
            id: expense.id,
            type: 'expense',
            date: expense.expense_date,
            description: expense.description,
            category: expense.category_display || expense.category,
            amount: parseFloat(expense.amount),
            formatted_amount: expense.formatted_amount || formatCurrency(expense.amount),
            notes: expense.notes,
            vendor: expense.vendor
        });
    });
    
    // Sort by date (newest first)
    transactions.sort((a, b) => {
        try {
            const dateA = new Date(a.date.split('/').reverse().join('-'));
            const dateB = new Date(b.date.split('/').reverse().join('-'));
            return dateB - dateA;
        } catch (e) {
            return 0;
        }
    });
    
    if (transactions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5">
                    <i class="fas fa-receipt fa-3x text-slate-300 mb-3"></i>
                    <h5 class="text-slate-500">Nenhuma transação encontrada</h5>
                    <p class="text-slate-400">Comece adicionando receitas ou despesas.</p>
                </td>
            </tr>
        `;
        return;
    }
    
    let tableHtml = '';
    transactions.forEach(transaction => {
        const isIncome = transaction.type === 'income';
        let formattedDate = transaction.date;
        try {
            const dateObj = new Date(transaction.date.split('/').reverse().join('-'));
            formattedDate = dateObj.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });
        } catch (e) {
            formattedDate = transaction.date;
        }
        
        tableHtml += `
            <tr class="border-bottom">
                <td class="py-3 px-4 text-slate-500" style="font-size: 0.875rem;">
                    ${formattedDate}
                </td>
                <td class="py-3 px-4">
                    <span class="text-slate-900 fw-medium">${escapeHtml(transaction.description)}</span>
                </td>
                <td class="py-3 px-4">
                    <span class="badge bg-slate-100 text-slate-700 rounded-full px-3 py-1" style="font-size: 0.75rem; font-weight: 500;">
                        ${escapeHtml(transaction.category)}
                    </span>
                </td>
                <td class="py-3 px-4">
                    <div class="d-flex align-items-center">
                        <span class="rounded-circle d-inline-block me-2" style="width: 8px; height: 8px; background-color: ${isIncome ? '#10b981' : '#f43f5e'};"></span>
                        <span class="text-slate-600" style="font-size: 0.875rem;">${isIncome ? 'Receita' : 'Despesa'}</span>
                    </div>
                </td>
                <td class="py-3 px-4 text-end">
                    <span class="fw-semibold ${isIncome ? 'text-emerald-600' : 'text-rose-600'}" style="font-size: 0.875rem;">
                        ${isIncome ? '+' : '-'} ${transaction.formatted_amount}
                    </span>
                </td>
                <td class="py-3 px-4 text-center">
                    <div class="d-flex align-items-center justify-content-center gap-2">
                        <button class="btn btn-sm btn-link text-slate-400 p-1" onclick="${isIncome ? 'viewIncome' : 'viewExpense'}(${transaction.id})" title="Editar" style="text-decoration: none;">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                        </button>
                        <button class="btn btn-sm btn-link text-slate-400 p-1" onclick="${isIncome ? 'deleteIncome' : 'deleteExpense'}(${transaction.id})" title="Excluir" style="text-decoration: none;">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    tbody.innerHTML = tableHtml;
}

function formatCurrency(value) {
    return `R$ ${parseFloat(value).toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.')}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make function globally available
window.updateUnifiedTransactionsTable = updateUnifiedTransactionsTable;

// Chart instances
let cashFlowChart = null;
let expensesCategoryChart = null;

// Initialize Cash Flow Chart
function initializeCashFlowChart() {
    const ctx = document.getElementById('cashFlowChart');
    if (!ctx) return;
    
    cashFlowChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Receita',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Despesa',
                    data: [],
                    borderColor: '#f43f5e',
                    backgroundColor: 'rgba(244, 63, 94, 0.1)',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': R$ ' + context.parsed.y.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return 'R$ ' + value.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
                        },
                        font: {
                            size: 11
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    ticks: {
                        font: {
                            size: 11
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Initialize Expenses by Category Chart
function initializeExpensesCategoryChart() {
    const ctx = document.getElementById('expensesCategoryChart');
    if (!ctx) return;
    
    expensesCategoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#ef4444', // Red
                    '#f97316', // Orange
                    '#10b981', // Green
                    '#3b82f6', // Blue
                    '#8b5cf6', // Purple
                    '#ec4899', // Pink
                    '#06b6d4', // Cyan
                    '#f59e0b', // Amber
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 10,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return label + ': R$ ' + value.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ' (' + percentage + '%)';
                        }
                    }
                }
            },
            cutout: '60%'
        }
    });
}

// Update Cash Flow Chart with last 6 months data
// This function always shows the last 6 completed months, regardless of current filter
function updateCashFlowChart() {
    if (!cashFlowChart) {
        initializeCashFlowChart();
        if (!cashFlowChart) return;
    }
    
    // Always fetch last 6 months of data regardless of current filter
    fetchCashFlowData();
}

// Fetch last 6 months of data for cash flow chart
async function fetchCashFlowData() {
    const now = new Date();
    const monthNames = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
    
    // Get last 6 months labels
    const months = [];
    for (let i = 5; i >= 0; i--) {
        const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
        months.push(monthNames[date.getMonth()] + ' ' + date.getFullYear());
    }
    
    // Fetch data for each of the last 6 months
    const incomeData = [];
    const expenseData = [];
    
    const fetchPromises = [];
    
    for (let i = 5; i >= 0; i--) {
        const targetDate = new Date(now.getFullYear(), now.getMonth() - i, 1);
        const targetYear = targetDate.getFullYear();
        const targetMonth = targetDate.getMonth() + 1;
        
        // Fetch incomes and expenses for this month
        fetchPromises.push(
            Promise.all([
                fetch(`/dashboard/api/incomes/?year=${targetYear}&month=${targetMonth}`).then(r => r.json()),
                fetch(`/dashboard/api/expenses/?year=${targetYear}&month=${targetMonth}`).then(r => r.json())
            ]).then(([incomesData, expensesData]) => {
                const monthIncomes = incomesData.success ? (incomesData.incomes || []) : [];
                const monthExpenses = expensesData.success ? (expensesData.expenses || []) : [];
                
                const incomeTotal = monthIncomes.reduce((sum, income) => sum + parseFloat(income.amount || 0), 0);
                const expenseTotal = monthExpenses.reduce((sum, expense) => sum + parseFloat(expense.amount || 0), 0);
                
                return { incomeTotal, expenseTotal };
            })
        );
    }
    
    try {
        const results = await Promise.all(fetchPromises);
        results.forEach(result => {
            incomeData.push(result.incomeTotal);
            expenseData.push(result.expenseTotal);
        });
        
        if (cashFlowChart) {
            cashFlowChart.data.labels = months;
            cashFlowChart.data.datasets[0].data = incomeData;
            cashFlowChart.data.datasets[1].data = expenseData;
            cashFlowChart.update();
        }
    } catch (error) {
        console.error('Error fetching cash flow data:', error);
    }
}

// Update Expenses by Category Chart
function updateExpensesCategoryChart(expenses) {
    if (!expensesCategoryChart) {
        initializeExpensesCategoryChart();
        if (!expensesCategoryChart) return;
    }
    
    // Group expenses by category
    const categoryTotals = {};
    (expenses || []).forEach(expense => {
        const category = expense.category_display || expense.category || 'Outros';
        if (!categoryTotals[category]) {
            categoryTotals[category] = 0;
        }
        categoryTotals[category] += parseFloat(expense.amount || 0);
    });
    
    // Convert to arrays for chart
    const labels = Object.keys(categoryTotals);
    const data = Object.values(categoryTotals);
    
    expensesCategoryChart.data.labels = labels;
    expensesCategoryChart.data.datasets[0].data = data;
    expensesCategoryChart.update();
}

// Initialize charts when finance tab is shown
document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts when finance tab becomes visible
    const financeTab = document.getElementById('finance-tab');
    if (financeTab) {
        const observer = new MutationObserver(function(mutations) {
            if (financeTab.style.display !== 'none') {
                if (!cashFlowChart) initializeCashFlowChart();
                if (!expensesCategoryChart) initializeExpensesCategoryChart();
            }
        });
        observer.observe(financeTab, { attributes: true, attributeFilter: ['style'] });
    }
});

function updateCategoryBreakdown(expenses) {
    // Skip if using new unified table design
    if (document.getElementById('transactions-table-body')) {
        return;
    }
    
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
        const expensesCard = document.querySelector('#expenses-list')?.closest('.card');
        if (!expensesCard) {
            // Old expenses list doesn't exist, skip category breakdown
            return;
        }
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

function showIncomeModal(appointmentId = null, patientId = null) {
    const modal = new bootstrap.Modal(document.getElementById('incomeModal'));
    
    // Set today's date as default
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('income-date').value = today;
    
    // Clear form
    document.getElementById('incomeForm').reset();
    document.getElementById('income-date').value = today;
    
    // Hide patient creation form
    document.getElementById('income-patient-create-form').style.display = 'none';
    
    // Load patients
    loadPatientsForIncome();
    
    // Auto-fill appointment and patient if provided
    if (appointmentId) {
        document.getElementById('income-appointment-id').value = appointmentId;
        // Load patient from appointment
        if (patientId) {
            document.getElementById('income-patient').value = patientId;
        } else {
            // Fetch appointment to get patient
            fetch(`/dashboard/api/appointments/${appointmentId}/`)
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.appointment.patient_id) {
                        document.getElementById('income-patient').value = data.appointment.patient_id;
                    }
                })
                .catch(error => console.error('Error loading appointment:', error));
        }
    } else {
        document.getElementById('income-appointment-id').value = '';
    }
    
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
    const yearSelect = document.getElementById('year-filter');
    const monthSelect = document.getElementById('month-filter');
    const year = yearSelect ? yearSelect.value : '';
    const month = monthSelect ? monthSelect.value : '';
    
    // If no filters selected, default to current month
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;
    
    const filterYear = year || currentYear;
    const filterMonth = month || currentMonth;
    
    // Build API URLs with parameters
    const params = new URLSearchParams();
    params.append('year', filterYear);
    params.append('month', filterMonth);
    
    const expensesApiUrl = '/dashboard/api/expenses/?' + params.toString();
    const incomesApiUrl = '/dashboard/api/incomes/?' + params.toString();
    
    // Load filtered data for both expenses and incomes
    Promise.all([
        fetch(expensesApiUrl).then(response => response.json()),
        fetch(incomesApiUrl).then(response => response.json())
    ])
    .then(([expensesData, incomesData]) => {
        const expenses = expensesData.success ? (expensesData.expenses || []) : [];
        const incomes = incomesData.success ? (incomesData.incomes || []) : [];
        
        if (expensesData.success) {
            updateExpensesList(expenses);
            updateExpenseTotals(expenses);
        } else {
            console.error('Error loading filtered expenses:', expensesData.error);
            showAlert('Erro ao carregar despesas filtradas: ' + expensesData.error, 'danger');
        }
        
        if (incomesData.success) {
            updateIncomesList(incomes);
            updateIncomeTotals(incomes);
        } else {
            console.error('Error loading filtered incomes:', incomesData.error);
            showAlert('Erro ao carregar receitas filtradas: ' + incomesData.error, 'danger');
        }
        
        // Update unified transactions table
        if (typeof updateUnifiedTransactionsTable === 'function') {
            updateUnifiedTransactionsTable(incomes, expenses);
        }
        
            // Update charts
            if (typeof Chart !== 'undefined') {
                // Cash flow chart always shows last 6 months, not filtered data
                updateCashFlowChart();
                // Expenses category chart uses filtered data
                updateExpensesCategoryChart(expenses);
            }
        
        // Update net income with filtered data
        updateNetIncome(expenses, incomes);
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
        
        // Patient creation button
        const incomeCreatePatientBtn = document.getElementById('income-create-patient-btn');
        if (incomeCreatePatientBtn) {
            incomeCreatePatientBtn.addEventListener('click', function(e) {
                e.preventDefault();
                showIncomePatientCreateForm();
            });
        }
        
        // Cancel patient creation button
        const incomeCancelPatientCreate = document.getElementById('income-cancel-patient-create');
        if (incomeCancelPatientCreate) {
            incomeCancelPatientCreate.addEventListener('click', function(e) {
                e.preventDefault();
                hideIncomePatientCreateForm();
            });
        }
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

function loadPatientsForIncome() {
    const patientSelect = document.getElementById('income-patient');
    if (!patientSelect) return;
    
    // Clear existing options except the first one
    patientSelect.innerHTML = '<option value="">Selecione um paciente</option>';
    
    // Fetch patients
    fetch('/dashboard/api/patients/')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.patients) {
                data.patients.forEach(patient => {
                    const option = document.createElement('option');
                    option.value = patient.id;
                    option.textContent = patient.full_name;
                    patientSelect.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Error loading patients:', error);
        });
}

function showIncomePatientCreateForm() {
    const form = document.getElementById('income-patient-create-form');
    if (form) {
        form.style.display = 'block';
        // Clear patient selection
        document.getElementById('income-patient').value = '';
    }
}

function hideIncomePatientCreateForm() {
    const form = document.getElementById('income-patient-create-form');
    if (form) {
        form.style.display = 'none';
        // Clear form fields
        form.querySelectorAll('input, select').forEach(field => {
            field.value = '';
        });
    }
}

function createIncome() {
    const form = document.getElementById('incomeForm');
    const formData = new FormData(form);
    
    // Check if creating new patient
    const createForm = document.getElementById('income-patient-create-form');
    const isCreatingPatient = createForm && createForm.style.display !== 'none';
    
    if (isCreatingPatient) {
        // Validate patient fields
        const firstName = document.getElementById('income-patient-first-name').value.trim();
        const lastName = document.getElementById('income-patient-last-name').value.trim();
        const dob = document.getElementById('income-patient-dob').value;
        const gender = document.getElementById('income-patient-gender').value;
        
        if (!firstName || !lastName || !dob || !gender) {
            showAlert('Preencha todos os campos obrigatórios do paciente', 'danger');
            return;
        }
        
        // Add patient creation flag and data
        formData.append('create_patient', 'true');
        formData.append('patient_first_name', firstName);
        formData.append('patient_last_name', lastName);
        formData.append('patient_date_of_birth', dob);
        formData.append('patient_gender', gender);
        
        const email = document.getElementById('income-patient-email').value.trim();
        const phone = document.getElementById('income-patient-phone').value.trim();
        if (email) formData.append('patient_email', email);
        if (phone) formData.append('patient_phone', phone);
    }
    
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
