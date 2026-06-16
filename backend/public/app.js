// ── Session check ─────────────────────────────────────────────────────────────
(function() {
    const user = localStorage.getItem('listiq_user');
    if (!user) {
        window.location.href = '/';
    }
})();

// ── Navigation ────────────────────────────────────────────────────────────────
function showPage(name, el) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById(`page-${name}`).classList.add('active');
    el.classList.add('active');

    if (name === 'analytics') loadAnalytics();
    if (name === 'historical') loadHistorical();
}

// ── Predict ───────────────────────────────────────────────────────────────────
async function predict() {
    const btn = document.querySelector('.btn-predict');
    btn.textContent = 'Generating...';
    btn.disabled = true;

    const payload = {
        issue_price:     parseFloat(document.getElementById('issue_price').value),
        issue_amount_cr: parseFloat(document.getElementById('issue_amount_cr').value),
        lot_size:        parseFloat(document.getElementById('lot_size').value),
        qib_x:           parseFloat(document.getElementById('qib_x').value),
        nii_x:           parseFloat(document.getElementById('nii_x').value),
        retail_x:        parseFloat(document.getElementById('retail_x').value),
        total_x:         parseFloat(document.getElementById('total_x').value),
        gmp:             parseFloat(document.getElementById('gmp').value),
        gmp_percent:     parseFloat(document.getElementById('gmp_percent').value),
        is_mainboard:    parseInt(document.getElementById('is_mainboard').value),
        listing_year:    parseInt(document.getElementById('listing_year').value),
        listing_month:   parseInt(document.getElementById('listing_month').value)
    };

    try {
        const res = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        renderResult(data, payload.issue_price);
    } catch (err) {
        alert('Prediction failed. Make sure the Python API is running.');
    } finally {
        btn.textContent = 'Generate prediction';
        btn.disabled = false;
    }
}

function renderResult(data, issuePrice) {
    const result = document.getElementById('result');
    result.classList.remove('hidden');

    // Gain
    const gainEl = document.getElementById('pred-gain');
    gainEl.textContent = `${data.prediction > 0 ? '+' : ''}${data.prediction}%`;
    gainEl.style.color = data.prediction > 0 ? '#B8D9EA' : '#5a7fa0';

    // Price
    document.getElementById('pred-price').textContent = `Rs. ${data.expected_listing_price}`;

    // Signal
    const signalEl = document.getElementById('pred-signal');
    const signalMap = {
        strong:   { text: 'Strong — apply',       cls: 'signal-strong' },
        moderate: { text: 'Moderate — apply',     cls: 'signal-moderate' },
        weak:     { text: 'Weak — risky',          cls: 'signal-weak' },
        avoid:    { text: 'Avoid — expected loss', cls: 'signal-avoid' }
    };
    const s = signalMap[data.signal];
    signalEl.innerHTML = `<span class="signal-badge ${s.cls}">${s.text}</span>`;

    // SHAP bars
    const shapContainer = document.getElementById('shap-bars');
    shapContainer.innerHTML = '';

    const maxImpact = Math.max(...data.shap_contributions.map(c => Math.abs(c.impact)));

    data.shap_contributions.forEach(c => {
        const pct = Math.round((Math.abs(c.impact) / maxImpact) * 100);
        const isPos = c.impact > 0;
        const color = isPos ? '#7EB8D4' : '#3a5f7a';
        const valText = `${isPos ? '+' : ''}${c.impact.toFixed(2)}`;
        const valColor = isPos ? '#B8D9EA' : '#5a7fa0';

        shapContainer.innerHTML += `
            <div class="shap-row">
                <div class="shap-name">${c.feature}</div>
                <div class="shap-track">
                    <div class="shap-fill" style="width:${pct}%;background:${color};"></div>
                </div>
                <span class="shap-val" style="color:${valColor};">${valText}</span>
            </div>
        `;
    });

    result.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Analytics ─────────────────────────────────────────────────────────────────
async function loadAnalytics() {
    try {
        const res = await fetch('/api/analytics');
        const data = await res.json();

        // Summary metrics
        const summaryEl = document.getElementById('analytics-summary');
        summaryEl.innerHTML = `
            <div class="metric"><div class="metric-label">Total IPOs</div><div class="metric-value" style="font-size:26px;">${data.total_ipos}</div></div>
            <div class="metric"><div class="metric-label">Average gain</div><div class="metric-value" style="font-size:26px;">${data.avg_gain}%</div></div>
            <div class="metric"><div class="metric-label">Best gain</div><div class="metric-value" style="font-size:26px;color:#B8D9EA;">${data.best_gain}%</div></div>
            <div class="metric"><div class="metric-label">Worst loss</div><div class="metric-value" style="font-size:26px;color:#5a7fa0;">${data.worst_loss}%</div></div>
        `;

        // Yearly bar chart
        const chartEl = document.getElementById('yearly-chart');
        const maxGain = Math.max(...data.yearly.map(y => Math.abs(y.avg_gain)));

        let barsHTML = '<div class="bar-chart">';
        data.yearly.forEach(y => {
            const height = Math.round((Math.abs(y.avg_gain) / maxGain) * 140);
            const color = y.avg_gain > 0 ? '#7EB8D4' : '#3a5f7a';
            barsHTML += `
                <div class="bar-col">
                    <div class="bar-val">${y.avg_gain.toFixed(1)}%</div>
                    <div class="bar" style="height:${height}px;background:${color};"></div>
                    <div class="bar-year">${parseInt(y.year)}</div>
                </div>
            `;
        });
        barsHTML += '</div>';
        chartEl.innerHTML = barsHTML;

    } catch (err) {
        console.error('Analytics load failed:', err);
    }
}

// ── Historical ────────────────────────────────────────────────────────────────
let historicalData = [];

async function loadHistorical() {
    try {
        const res = await fetch('/api/historical?limit=500');
        const data = await res.json();
        historicalData = data.data;
        renderTable(historicalData);
    } catch (err) {
        console.error('Historical load failed:', err);
    }
}

function renderTable(data) {
    const tbody = document.getElementById('historical-body');
    tbody.innerHTML = '';

    data.forEach(row => {
        const gain = parseFloat(row.listing_gain_pct);
        const gainClass = gain > 0 ? 'gain-positive' : 'gain-negative';
        const gainText = `${gain > 0 ? '+' : ''}${gain.toFixed(2)}%`;

        tbody.innerHTML += `
            <tr>
                <td>${row.ipo_name || '-'}</td>
                <td>${row.listing_date ? row.listing_date.split('T')[0] : '-'}</td>
                <td>Rs. ${row.issue_price || '-'}</td>
                <td>${row.qib_x || '-'}</td>
                <td>${row.nii_x || '-'}</td>
                <td>${row.retail_x || '-'}</td>
                <td>${row.gmp_percent || '-'}%</td>
                <td class="${gainClass}">${gainText}</td>
            </tr>
        `;
    });
}

function filterTable() {
    const query = document.getElementById('search-input').value.toLowerCase();
    const filtered = historicalData.filter(row =>
        row.ipo_name && row.ipo_name.toLowerCase().includes(query)
    );
    renderTable(filtered);
}

function handleLogout() {
    localStorage.removeItem('listiq_user');
    window.location.href = '/';
}