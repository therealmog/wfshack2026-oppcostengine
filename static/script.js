// --- INTRO & SPLASH REVEAL ---
window.addEventListener('DOMContentLoaded', () => {
    // Initialise Tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));

    // Handle Splash Timing
    setTimeout(() => {
        document.getElementById('splash').style.opacity = '0';
        document.getElementById('main-wrapper').classList.add('show-content');
        document.body.style.overflow = 'auto'; // Re-enable scrolling
        setTimeout(() => document.getElementById('splash').remove(), 1000);
    }, 2500);
});

// --- GLOBAL ELEMENTS ---
const companyInput = document.getElementById('companyInput');
const tickerInput = document.getElementById('ticker');
const yearsInput = document.getElementById('years');
let chart = null;

// --- INPUT LOGIC ---
yearsInput.oninput = () => document.getElementById('yrDisp').innerText = `${yearsInput.value} Years`;

companyInput.addEventListener('input', function() {
    const options = document.querySelectorAll('#companyList option');
    let found = false;
    for (let opt of options) {
        if (opt.value === this.value) {
            tickerInput.value = opt.getAttribute('data-ticker');
            this.setCustomValidity("");
            found = true;
            break;
        }
    }
    if (!found) {
        tickerInput.value = "";
        this.setCustomValidity("Please select a valid company from the list.");
    }
});

// --- SUBMISSION & CALCULATION ---
document.getElementById('calcForm').onsubmit = async (e) => {
    e.preventDefault();
    if (!tickerInput.value) {
        alert("Please select a company from the dropdown before running analytics.");
        return;
    }

    const res = await fetch('/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            item_name: document.getElementById('productName').value,
            price: parseFloat(document.getElementById('price').value),
            ticker: tickerInput.value,
            years: parseInt(yearsInput.value),
            is_subscription: document.getElementById('isSub').checked,
            model_type: document.getElementById('modelType').value // Sending model choice
        })
    });

    const data = await res.json();
    const gbp = { style: 'currency', currency: 'GBP' };

    // Update Outcome Boxes
    document.getElementById('eqOut').innerText = data.final_equity.toLocaleString('en-GB', gbp);
    document.getElementById('mileOut').innerText = data.milestone;
    
    // FIX: Show the final item in the asset_values array
    const finalAsset = data.asset_values[data.asset_values.length - 1];
    document.getElementById('assetOut').innerText = finalAsset.toLocaleString('en-GB', gbp);
    
    document.getElementById('vText').innerText = data.verdict;
    document.getElementById('vBox').classList.remove('d-none');

    // --- CHART UPDATE ---
    const ctx = document.getElementById('mainChart').getContext('2d');
    if (chart) chart.destroy();
    
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                { 
                    label: 'Invested Capital (£)', 
                    data: data.equity_values, 
                    borderColor: '#007aff', 
                    backgroundColor: 'rgba(0, 122, 255, 0.1)', 
                    fill: true, 
                    tension: 0.3 
                },
                { 
                    label: 'Physical Asset Value (£)', 
                    data: data.asset_values, 
                    borderColor: '#dc3545', 
                    borderDash: [5, 5], 
                    tension: 0.1 
                }
            ]
        },
        options: { 
            responsive: true,
            plugins: { legend: { labels: { color: '#8e96a3', font: { weight: '600' } } } },
            scales: { 
                y: { ticks: { color: '#8e96a3' }, grid: { color: 'rgba(255,255,255,0.05)' } }, 
                x: { ticks: { color: '#8e96a3' }, grid: { display: false } } 
            } 
        }
    });
};