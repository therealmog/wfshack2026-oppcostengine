// --- GLOBAL ELEMENTS ---
const companyInput = document.getElementById('companyInput');
const tickerInput = document.getElementById('ticker');
const yearsInput = document.getElementById('years');
let chart = null;

/*const sectorSelect = document.getElementById('sectorSelect');
const similarBox = document.getElementById('similarBox');
const similarResults = document.getElementById('similarResults'); */

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
    }, 1);

    /*// Load sectors dynamically
    fetch('/sectors')
        .then(res => res.json())
        .then(data => {
            data.forEach(sec => {
                const opt = document.createElement('option');
                opt.value = sec;
                opt.textContent = sec;
                sectorSelect.appendChild(opt);
            });
    });*/

});

/*sectorSelect.addEventListener('change', async function() {

    if (!this.value) {
        similarBox.classList.add('d-none');
        return;
    }

    const res = await fetch('/similar_trades', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            sector: this.value,
            price: parseFloat(document.getElementById('price').value),
            years: parseFloat(yearsInput.value)
        })
    });

    const trades = await res.json();

    if (!trades.length) return;

    similarResults.innerHTML = "";

    trades.forEach(trade => {
        const div = document.createElement('div');
        div.classList.add('mb-3');

        div.innerHTML = `
            <strong>${trade.ticker}</strong><br>
            Free Milestone: ${trade.milestone}<br>
            Opportunity Cost: £${trade.profit.toLocaleString()}<br>
            Final Value: £${trade.final_value.toLocaleString()}
        `;

        similarResults.appendChild(div);
    });

    similarBox.classList.remove('d-none');
}); */

// --- INPUT LOGIC ---
yearsInput.oninput = () => document.getElementById('yrDisp').innerText = `${yearsInput.value} Years`;

function validateAISelection() {
    const options = document.querySelectorAll('#companyList option');
    const currentModel = document.getElementById('modelType').value;
    const currentCompany = companyInput.value;
    let found = false;

    if (!currentCompany) return; 

    for (let opt of options) {
        if (opt.value === currentCompany) {
            const hasNews = opt.getAttribute('data-has-news') === 'true';
            
            if (currentModel === 'NB_AI' && !hasNews) {
                companyInput.setCustomValidity("Invalid selection: This company has no recent news articles required for the AI Prediction model.");
                companyInput.reportValidity(); 
                tickerInput.value = ""; 
                return false;
            }

            tickerInput.value = opt.getAttribute('data-ticker');
            companyInput.setCustomValidity(""); 
            found = true;
            break;
        }
    }
    
    if (!found) {
        tickerInput.value = "";
        companyInput.setCustomValidity("Please select a valid company from the list.");
        companyInput.reportValidity();
        return false;
    }
    
    return true;
}

// Attach the validation to both the company text box AND the model dropdown
companyInput.addEventListener('input', validateAISelection);
document.getElementById('modelType').addEventListener('change', validateAISelection);





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

    document.getElementById('extraText').innerText = data.full_context;
    document.getElementById('extraBox').classList.remove('d-none');

    const extraText = document.getElementById('extraText');
    const extraBox = document.getElementById('extraBox');
    
    if (data.full_context && data.full_context !== "") {
        extraText.innerText = data.full_context;
        extraBox.classList.remove('d-none');
    } else {
        extraBox.classList.add('d-none'); // optional fallback
    }


// --- CHART UPDATE ---
    const ctx = document.getElementById('mainChart').getContext('2d');
    if (chart) chart.destroy();
    document.getElementById('chartPlaceholder').style.display = 'none';

    setTimeout(() => {
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
                maintainAspectRatio: false, // <--- ADD THIS LINE
                plugins: { legend: { labels: { color: '#8e96a3', font: { weight: '600' } } } },
                scales: { 
                // ... rest of your code ...
                    y: { ticks: { color: '#8e96a3' }, grid: { color: 'rgba(255,255,255,0.05)' } }, 
                    x: { 
                        ticks: { 
                            color: '#8e96a3', // FIX: Removed the invalid curly braces here
                            callback: function(val, index) {
                                let rawlabel = this.getLabelForValue(val);
                                if (!rawlabel) return "";

                                let num = parseFloat(rawlabel.replace('Yr', ''));
                                let yrs = Math.floor(num);
                                let mos = Math.round((num-yrs) * 12);

                                let label = "";
                                // FIX: Updated to spell out "Years" and "Months" with plurals
                                if (yrs > 0) label += `${yrs} yr${yrs > 1 ? 's' : ''}`;
                                if (mos > 0) label += (yrs > 0 ? " " : "") + `${mos} mo${mos > 1 ? 's' : ''}`;

                                return label || "Start";
                            }
                        },
                        grid: { display: false } // FIX: Moved grid outside of the ticks block
                    } 
                } 
            }
        });
},5);

    
};