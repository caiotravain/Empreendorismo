// Finance Tab Functions
function _getFilterPeriod() {
    // Returns {year, month, label} based on current filter dropdowns (defaults to current month)
    const now = new Date();
    const monthNames = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
    const yearSel = document.getElementById('year-filter');
    const monthSel = document.getElementById('month-filter');
    const year = (yearSel && yearSel.value) ? parseInt(yearSel.value) : now.getFullYear();
    const month = (monthSel && monthSel.value) ? parseInt(monthSel.value) : (now.getMonth() + 1);
    const label = monthNames[month - 1] + ' ' + year;
    return { year, month, label };
}

function _updatePeriodLabels(label) {
    const catLabel = document.getElementById('category-chart-period-label');
    if (catLabel) catLabel.textContent = label;
    const cfLabel = document.getElementById('cashflow-period-label');
    if (cfLabel) cfLabel.textContent = label;
}

function loadFinanceData() {
    // Load expenses and income immediately so the tab never stays loading
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;

    Promise.all([
        fetch(`/dashboard/api/expenses/?year=${currentYear}&month=${currentMonth}`).then(response => response.json()),
        fetch(`/dashboard/api/incomes/?year=${currentYear}&month=${currentMonth}`).then(response => response.json())
    ])
    .then(([expensesData, incomesData]) => {
        const expenses = expensesData.success ? (expensesData.expenses || []) : [];
        const incomes = incomesData.success ? (incomesData.incomes || []) : [];

        if (!expensesData.success) {
            console.error('Error loading expenses:', expensesData.error);
            showAlert('Erro ao carregar despesas: ' + (expensesData.error || ''), 'danger');
        }
        if (!incomesData.success) {
            console.error('Error loading incomes:', incomesData.error);
            showAlert('Erro ao carregar receitas: ' + (incomesData.error || ''), 'danger');
        }

        // Always update UI so spinners are cleared (use empty arrays on error)
        updateExpensesList(expenses);
        updateExpenseTotals(expenses);
        updateIncomesList(incomes);
        updateIncomeTotals(incomes);

        if (typeof updateUnifiedTransactionsTable === 'function') {
            updateUnifiedTransactionsTable(incomes, expenses);
        }

        const now = new Date();
        updateCashFlowChart(now.getFullYear(), now.getMonth() + 1);
        updateExpensesCategoryChart(expenses);
        updateFilterDropdowns(expenses, incomes);
        setupFilterEventListeners();
        updateNetIncome(expenses, incomes);

        const monthNames = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
        _updatePeriodLabels(monthNames[now.getMonth()] + ' ' + now.getFullYear());
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Erro ao carregar dados financeiros', 'danger');
        // Clear loading state with empty data
        updateExpensesList([]);
        updateExpenseTotals([]);
        updateIncomesList([]);
        updateIncomeTotals([]);
        if (typeof updateUnifiedTransactionsTable === 'function') {
            updateUnifiedTransactionsTable([], []);
        }
        updateNetIncome([], []);
    });

    // Sync appointment income in background (do not block tab load)
    fetch('/dashboard/api/appointments/sync-income/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(syncData => {
        if (syncData.success && syncData.income_created_count > 0) {
            console.log('Auto-sync: ' + syncData.income_created_count + ' receitas criadas automaticamente');
            loadFinanceData(); // Reload to show new incomes
        }
    })
    .catch(() => {});
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

    const transactions = [];

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
            patient_name: income.patient_name || '',
            payment_type: income.payment_type_display || income.payment_type || '',
            is_free_return: income.is_free_return || false,
            raw: income
        });
    });

    (expenses || []).forEach(expense => {
        transactions.push({
            id: expense.id,
            type: 'expense',
            date: expense.expense_date,
            description: expense.description,
            category: expense.category || expense.category_display || '',
            amount: parseFloat(expense.amount),
            formatted_amount: expense.formatted_amount || formatCurrency(expense.amount),
            notes: expense.notes,
            patient_name: '',
            payment_type: '',
            raw: expense
        });
    });

    transactions.sort((a, b) => {
        try {
            const dateA = new Date(a.date.split('/').reverse().join('-'));
            const dateB = new Date(b.date.split('/').reverse().join('-'));
            return dateB - dateA;
        } catch (e) { return 0; }
    });

    if (transactions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-5">
                    <i class="fas fa-receipt fa-3x text-slate-300 mb-3 d-block"></i>
                    <h5 class="text-slate-500">Nenhuma transação encontrada</h5>
                    <p class="text-slate-400">Comece adicionando receitas ou despesas.</p>
                </td>
            </tr>`;
        return;
    }

    let tableHtml = '';
    transactions.forEach(transaction => {
        const isIncome = transaction.type === 'income';
        let formattedDate = transaction.date;
        try {
            const dateObj = new Date(transaction.date.split('/').reverse().join('-'));
            formattedDate = dateObj.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });
        } catch (e) { formattedDate = transaction.date; }

        const patientCell = transaction.patient_name
            ? `<span class="text-slate-700" style="font-size:0.8rem;">${escapeHtml(transaction.patient_name)}</span>`
            : `<span class="text-slate-300" style="font-size:0.8rem;">—</span>`;

        let atendCell = '<span class="text-slate-300" style="font-size:0.8rem;">—</span>';
        if (isIncome) {
            if (transaction.is_free_return) {
                atendCell = `<span class="badge" style="font-size:0.7rem;background:#e0e7ff;color:#4338ca;">Retorno Gratuito</span>`;
            } else if (transaction.payment_type) {
                const isParticular = transaction.payment_type.toLowerCase().includes('particular');
                atendCell = `<span class="badge" style="font-size:0.7rem;background:${isParticular ? '#d1fae5' : '#dbeafe'};color:${isParticular ? '#065f46' : '#1e40af'};">${escapeHtml(transaction.payment_type)}</span>`;
            }
        }

        const displayAmount = transaction.is_free_return
            ? `<span class="fw-semibold text-slate-400" style="font-size:0.875rem;">Gratuito</span>`
            : `<span class="fw-semibold ${isIncome ? 'text-emerald-600' : 'text-rose-600'}" style="font-size:0.875rem;">${isIncome ? '+' : '-'} ${transaction.formatted_amount}</span>`;

        tableHtml += `
            <tr class="border-bottom">
                <td class="py-3 px-3 text-slate-500" style="font-size:0.875rem;white-space:nowrap;">${formattedDate}</td>
                <td class="py-3 px-3"><span class="text-slate-900 fw-medium" style="font-size:0.875rem;">${escapeHtml(transaction.description)}</span></td>
                <td class="py-3 px-3">${patientCell}</td>
                <td class="py-3 px-3"><span class="badge bg-slate-100 text-slate-700" style="font-size:0.75rem;">${escapeHtml(transaction.category)}</span></td>
                <td class="py-3 px-3">
                    <div class="d-flex align-items-center">
                        <span class="rounded-circle d-inline-block me-2" style="width:8px;height:8px;flex-shrink:0;background-color:${isIncome ? '#10b981' : '#f43f5e'};"></span>
                        <span class="text-slate-600" style="font-size:0.875rem;">${isIncome ? 'Receita' : 'Despesa'}</span>
                    </div>
                </td>
                <td class="py-3 px-3">${atendCell}</td>
                <td class="py-3 px-3 text-end">${displayAmount}</td>
                <td class="py-3 px-3 text-center">
                    <div class="d-flex align-items-center justify-content-center gap-2">
                        <button class="btn btn-sm btn-link text-slate-400 p-1" onclick="${isIncome ? 'viewIncome' : 'viewExpense'}(${transaction.id})" title="Editar" style="text-decoration:none;">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                        </button>
                        <button class="btn btn-sm btn-link text-rose-400 p-1" onclick="${isIncome ? 'deleteIncome' : 'deleteExpense'}(${transaction.id})" title="Excluir" style="text-decoration:none;">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                        </button>
                    </div>
                </td>
            </tr>`;
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

// Initialize Expenses by Category Chart (empty – used only when tab is shown before data loads)
function initializeExpensesCategoryChart() {
    const ctx = document.getElementById('expensesCategoryChart');
    if (!ctx) return;
    if (typeof Chart === 'undefined') return;
    if (expensesCategoryChart) return;
    expensesCategoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Sem despesas'],
            datasets: [{
                data: [0],
                backgroundColor: ['#e5e7eb'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            if (total === 0) return context.label + ': R$ 0,00';
                            const pct = ((context.parsed / total) * 100).toFixed(1);
                            return context.label + ': R$ ' + context.parsed.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ' (' + pct + '%)';
                        }
                    }
                }
            },
            cutout: '60%'
        }
    });
}

// Update Cash Flow Chart — 6 months ending at (anchorYear, anchorMonth)
function updateCashFlowChart(anchorYear, anchorMonth) {
    if (!cashFlowChart) {
        initializeCashFlowChart();
        if (!cashFlowChart) return;
    }
    const now = new Date();
    const year = anchorYear || now.getFullYear();
    const month = anchorMonth || (now.getMonth() + 1);
    fetchCashFlowData(year, month);
}

// Fetch 6 months of data ending at (anchorYear, anchorMonth)
async function fetchCashFlowData(anchorYear, anchorMonth) {
    const monthNames = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
    const now = new Date();
    const ay = anchorYear || now.getFullYear();
    const am = anchorMonth || (now.getMonth() + 1);

    // Build 6 months ending at anchor
    const months = [];
    const fetchPromises = [];

    for (let i = 5; i >= 0; i--) {
        // Go back i months from anchor
        let y = ay;
        let m = am - i;
        while (m <= 0) { m += 12; y--; }
        months.push(monthNames[m - 1] + ' ' + y);

        fetchPromises.push(
            Promise.all([
                fetch(`/dashboard/api/incomes/?year=${y}&month=${m}`).then(r => r.json()),
                fetch(`/dashboard/api/expenses/?year=${y}&month=${m}`).then(r => r.json())
            ]).then(([incomesData, expensesData]) => {
                const monthIncomes = incomesData.success ? (incomesData.incomes || []) : [];
                const monthExpenses = expensesData.success ? (expensesData.expenses || []) : [];
                const incomeTotal = monthIncomes.reduce((sum, inc) => sum + parseFloat(inc.amount || 0), 0);
                const expenseTotal = monthExpenses.reduce((sum, exp) => sum + parseFloat(exp.amount || 0), 0);
                return { incomeTotal, expenseTotal };
            })
        );
    }

    try {
        const results = await Promise.all(fetchPromises);
        const incomeData = results.map(r => r.incomeTotal);
        const expenseData = results.map(r => r.expenseTotal);
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
    const ctx = document.getElementById('expensesCategoryChart');
    if (!ctx) return;
    
    if (!expensesCategoryChart) {
        initializeExpensesCategoryChart();
        if (!expensesCategoryChart) return;
    }
    
    // Group expenses by category (API sends category = display name, category_value = raw)
    const categoryTotals = {};
    (expenses || []).forEach(expense => {
        const category = expense.category_display || expense.category || 'Outros';
        if (!categoryTotals[category]) {
            categoryTotals[category] = 0;
        }
        categoryTotals[category] += parseFloat(expense.amount || 0);
    });
    
    let labels = Object.keys(categoryTotals);
    let data = Object.values(categoryTotals);
    
    // Chart.js doughnut needs at least one segment; use placeholder when empty
    if (labels.length === 0) {
        labels = ['Sem despesas'];
        data = [0];
    }
    
    const palette = [
        '#ef4444', '#f97316', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4', '#f59e0b',
        '#84cc16', '#6366f1', '#14b8a6', '#e11d48'
    ];
    const backgroundColor = labels.map((_, i) => palette[i % palette.length]);
    
    expensesCategoryChart.data.labels = labels;
    expensesCategoryChart.data.datasets[0].data = data;
    expensesCategoryChart.data.datasets[0].backgroundColor = backgroundColor;
    expensesCategoryChart.update('none'); // 'none' to avoid animation when only data changed
    try {
        expensesCategoryChart.resize();
    } catch (e) { /* ignore */ }
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
    document.getElementById('expenseForm').reset();
    document.getElementById('expense-edit-id').value = '';
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('expense-date').value = today;
    document.getElementById('expense-modal-title-text').textContent = 'Nova Despesa';
    document.getElementById('expense-modal-icon').className = 'fas fa-plus me-2';
    document.getElementById('new-category-input-wrap').style.display = 'none';
    loadCustomExpenseCategories();
    const modal = new bootstrap.Modal(document.getElementById('expenseModal'));
    modal.show();
}

function showIncomeModal(appointmentId = null, patientId = null) {
    document.getElementById('incomeForm').reset();
    document.getElementById('income-edit-id').value = '';
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('income-date').value = today;
    document.getElementById('income-modal-title-text').textContent = 'Nova Receita';
    document.getElementById('income-modal-icon').className = 'fas fa-plus me-2';
    document.getElementById('income-patient-create-form').style.display = 'none';
    document.getElementById('income-is-free-return').checked = false;
    document.getElementById('income-amount').disabled = false;
    _updateIncomePatientRequired('');

    loadPatientsForIncome();

    if (appointmentId) {
        document.getElementById('income-appointment-id').value = appointmentId;
        if (patientId) {
            document.getElementById('income-patient').value = patientId;
        } else {
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

    const modal = new bootstrap.Modal(document.getElementById('incomeModal'));
    modal.show();
}

function _updateIncomePatientRequired(category) {
    const badge = document.getElementById('income-patient-required-badge');
    const hint = document.getElementById('income-patient-hint');
    if (category === 'consultation') {
        if (badge) badge.style.display = '';
        if (hint) hint.textContent = 'Obrigatório para Consultas';
    } else {
        if (badge) badge.style.display = 'none';
        if (hint) hint.textContent = 'Opcional';
    }
}

// Load and inject custom expense categories into the expense-category select
function loadCustomExpenseCategories() {
    return fetch('/dashboard/api/expenses/categories/')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            const select = document.getElementById('expense-category');
            if (!select) return;
            // Remove previously injected custom options
            select.querySelectorAll('option[data-custom]').forEach(o => o.remove());
            (data.categories || []).forEach(cat => {
                const opt = document.createElement('option');
                opt.value = 'custom__' + cat;
                opt.textContent = cat;
                opt.dataset.custom = '1';
                select.appendChild(opt);
            });
        })
        .catch(() => {});
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
        
        // Update charts — both follow the selected filter period
        if (typeof Chart !== 'undefined') {
            updateCashFlowChart(filterYear, filterMonth);
            updateExpensesCategoryChart(expenses);
        }

        // Update period labels on both charts
        _updatePeriodLabels(_getFilterPeriod().label);

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

// Handle form submissions and new UI controls
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

        // Toggle patient required badge when category changes
        const incomeCategory = document.getElementById('income-category');
        if (incomeCategory) {
            incomeCategory.addEventListener('change', function() {
                _updateIncomePatientRequired(this.value);
            });
        }

        // Free return checkbox: disable/zero amount field
        const freeReturnChk = document.getElementById('income-is-free-return');
        if (freeReturnChk) {
            freeReturnChk.addEventListener('change', function() {
                const amountInput = document.getElementById('income-amount');
                if (this.checked) {
                    amountInput.value = '0';
                    amountInput.disabled = true;
                } else {
                    amountInput.disabled = false;
                    if (amountInput.value === '0') amountInput.value = '';
                }
            });
        }

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

    // Custom expense category controls
    const addCatBtn = document.getElementById('add-custom-category-btn');
    const newCatWrap = document.getElementById('new-category-input-wrap');
    const saveCatBtn = document.getElementById('save-custom-category-btn');
    const cancelCatBtn = document.getElementById('cancel-custom-category-btn');

    if (addCatBtn && newCatWrap) {
        addCatBtn.addEventListener('click', function() {
            newCatWrap.style.display = newCatWrap.style.display === 'none' ? 'flex' : 'none';
            if (newCatWrap.style.display !== 'none') {
                document.getElementById('new-category-name').focus();
            }
        });
    }
    if (cancelCatBtn && newCatWrap) {
        cancelCatBtn.addEventListener('click', function() {
            newCatWrap.style.display = 'none';
            document.getElementById('new-category-name').value = '';
        });
    }
    // Category suggestion chips: click fills name input and triggers save
    document.querySelectorAll('.category-suggestion-chip').forEach(function(chip) {
        chip.addEventListener('click', function() {
            const nameInput = document.getElementById('new-category-name');
            if (nameInput) {
                nameInput.value = chip.dataset.name;
                if (saveCatBtn) saveCatBtn.click();
            }
        });
    });

    if (saveCatBtn) {
        saveCatBtn.addEventListener('click', function() {
            const name = document.getElementById('new-category-name').value.trim();
            if (!name) { showAlert('Digite um nome para a categoria.', 'warning'); return; }
            saveCatBtn.disabled = true;
            fetch('/dashboard/api/expenses/categories/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
                body: JSON.stringify({ name })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showAlert('Categoria criada com sucesso!', 'success');
                    document.getElementById('new-category-name').value = '';
                    newCatWrap.style.display = 'none';
                    loadCustomExpenseCategories().then(() => {
                        // Select the new category
                        const select = document.getElementById('expense-category');
                        if (select) select.value = 'custom__' + name;
                    });
                } else {
                    showAlert(data.error || 'Erro ao criar categoria.', 'danger');
                }
            })
            .catch(() => showAlert('Erro ao criar categoria.', 'danger'))
            .finally(() => { saveCatBtn.disabled = false; });
        });
    }
});


function createExpense() {
    const form = document.getElementById('expenseForm');
    const formData = new FormData(form);
    const editId = document.getElementById('expense-edit-id').value;

    // Handle custom category: strip the 'custom__' prefix
    const catSelect = document.getElementById('expense-category');
    if (catSelect && catSelect.value.startsWith('custom__')) {
        formData.set('category', catSelect.value.replace('custom__', ''));
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Salvando...';
    submitBtn.disabled = true;

    const url = editId
        ? `/dashboard/api/expenses/update/${editId}/`
        : '/dashboard/api/expenses/create/';

    fetch(url, {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('expenseModal')).hide();
            showAlert(editId ? 'Despesa atualizada com sucesso!' : 'Despesa criada com sucesso!', 'success');
            loadFinanceData();
        } else {
            showAlert(data.error || 'Erro ao salvar despesa', 'danger');
        }
    })
    .catch(() => showAlert('Erro ao salvar despesa', 'danger'))
    .finally(() => { submitBtn.innerHTML = originalText; submitBtn.disabled = false; });
}

function loadPatientsForIncome() {
    const patientSelect = document.getElementById('income-patient');
    if (!patientSelect) return Promise.resolve();

    patientSelect.innerHTML = '<option value="">Selecione um paciente</option>';

    return fetch('/dashboard/api/patients/')
        .then(r => r.json())
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
        .catch(error => console.error('Error loading patients:', error));
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
    const editId = document.getElementById('income-edit-id').value;

    // Validate patient required for consultation
    const category = document.getElementById('income-category').value;
    const patientId = document.getElementById('income-patient').value;
    const isFreeReturn = document.getElementById('income-is-free-return').checked;
    const isCreatingPatient = document.getElementById('income-patient-create-form').style.display !== 'none';

    if (category === 'consultation' && !patientId && !isCreatingPatient && !isFreeReturn) {
        showAlert('Consultas devem estar vinculadas a um paciente.', 'danger');
        return;
    }

    // Append is_free_return as string
    formData.set('is_free_return', isFreeReturn ? 'true' : 'false');
    if (isFreeReturn) {
        formData.set('amount', '0');
    }

    if (isCreatingPatient) {
        const firstName = document.getElementById('income-patient-first-name').value.trim();
        const lastName = document.getElementById('income-patient-last-name').value.trim();
        const dob = document.getElementById('income-patient-dob').value;
        const gender = document.getElementById('income-patient-gender').value;

        if (!firstName || !lastName || !dob || !gender) {
            showAlert('Preencha todos os campos obrigatórios do paciente', 'danger');
            return;
        }

        formData.append('create_patient', 'true');
        formData.set('patient_first_name', firstName);
        formData.set('patient_last_name', lastName);
        formData.set('patient_date_of_birth', dob);
        formData.set('patient_gender', gender);

        const email = document.getElementById('income-patient-email').value.trim();
        const phone = document.getElementById('income-patient-phone').value.trim();
        if (email) formData.set('patient_email', email);
        if (phone) formData.set('patient_phone', phone);
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Salvando...';
    submitBtn.disabled = true;

    const url = editId
        ? `/dashboard/api/incomes/update/${editId}/`
        : '/dashboard/api/incomes/create/';

    fetch(url, {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('incomeModal')).hide();
            showAlert(editId ? 'Receita atualizada com sucesso!' : 'Receita criada com sucesso!', 'success');
            loadFinanceData();
        } else {
            showAlert(data.error || 'Erro ao salvar receita', 'danger');
        }
    })
    .catch(() => showAlert('Erro ao salvar receita', 'danger'))
    .finally(() => { submitBtn.innerHTML = originalText; submitBtn.disabled = false; });
}


function viewExpense(expenseId) {
    fetch(`/dashboard/api/expenses/`)
        .then(r => r.json())
        .then(data => {
            if (!data.success) { showAlert('Erro ao carregar despesa.', 'danger'); return; }
            const expense = (data.expenses || []).find(e => e.id === expenseId);
            if (!expense) { showAlert('Despesa não encontrada.', 'warning'); return; }
            _openExpenseModalForEdit(expense);
        })
        .catch(() => showAlert('Erro ao carregar despesa.', 'danger'));
}

function _openExpenseModalForEdit(expense) {
    document.getElementById('expense-edit-id').value = expense.id;
    document.getElementById('expense-description').value = expense.description || '';
    document.getElementById('expense-amount').value = expense.amount || '';

    // Set category (handles both standard and custom values)
    const catSelect = document.getElementById('expense-category');
    // Try setting; if not found as an option, it falls back to blank
    catSelect.value = expense.category_value || expense.category || '';

    // Parse date from DD/MM/YYYY
    if (expense.expense_date) {
        const parts = expense.expense_date.split('/');
        if (parts.length === 3) {
            document.getElementById('expense-date').value = `${parts[2]}-${parts[1]}-${parts[0]}`;
        }
    }
    document.getElementById('expense-vendor').value = expense.vendor || '';
    document.getElementById('expense-receipt').value = expense.receipt_number || '';
    document.getElementById('expense-notes').value = expense.notes || '';

    document.getElementById('expense-modal-title-text').textContent = 'Editar Despesa';
    document.getElementById('expense-modal-icon').className = 'fas fa-edit me-2';

    loadCustomExpenseCategories().then(() => {
        // Retry setting category after custom cats are loaded
        catSelect.value = expense.category_value || expense.category || '';
    });

    const modal = new bootstrap.Modal(document.getElementById('expenseModal'));
    modal.show();
}

function viewIncome(incomeId) {
    fetch('/dashboard/api/incomes/')
        .then(r => r.json())
        .then(data => {
            if (!data.success) { showAlert('Erro ao carregar receita.', 'danger'); return; }
            const income = (data.incomes || []).find(i => i.id === incomeId);
            if (!income) { showAlert('Receita não encontrada.', 'warning'); return; }
            _openIncomeModalForEdit(income);
        })
        .catch(() => showAlert('Erro ao carregar receita.', 'danger'));
}

function _openIncomeModalForEdit(income) {
    document.getElementById('income-edit-id').value = income.id;
    document.getElementById('income-description').value = income.description || '';
    document.getElementById('income-amount').value = income.amount || '';
    document.getElementById('income-category').value = income.category || '';

    const isFreeReturn = income.is_free_return || false;
    document.getElementById('income-is-free-return').checked = isFreeReturn;
    document.getElementById('income-amount').disabled = isFreeReturn;

    if (income.income_date) {
        const parts = income.income_date.split('/');
        if (parts.length === 3) {
            document.getElementById('income-date').value = `${parts[2]}-${parts[1]}-${parts[0]}`;
        }
    }
    document.getElementById('income-payment-type').value = income.payment_type || '';
    document.getElementById('income-payment-method').value = income.payment_method || '';
    document.getElementById('income-appointment-id').value = income.appointment_id || '';
    document.getElementById('income-notes').value = income.notes || '';

    document.getElementById('income-modal-title-text').textContent = 'Editar Receita';
    document.getElementById('income-modal-icon').className = 'fas fa-edit me-2';

    // Toggle patient required badge
    _updateIncomePatientRequired(income.category);

    // Load patients then set selected; inject fallback option if patient not in list
    loadPatientsForIncome().then(() => {
        if (income.patient_id) {
            const patientSelect = document.getElementById('income-patient');
            const exists = patientSelect && Array.from(patientSelect.options).some(o => parseInt(o.value) === income.patient_id);
            if (!exists && patientSelect && income.patient_name) {
                const opt = document.createElement('option');
                opt.value = income.patient_id;
                opt.textContent = income.patient_name;
                patientSelect.appendChild(opt);
            }
            if (patientSelect) patientSelect.value = income.patient_id;
        }
    });

    document.getElementById('income-patient-create-form').style.display = 'none';

    const modal = new bootstrap.Modal(document.getElementById('incomeModal'));
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
