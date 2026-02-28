const companyInput = document.getElementById('companyInput');
const tickerInput = document.getElementById('ticker');
const yearsInput = document.getElementById('years');

yearsInput.oninput = () => document.getElementById('yrDisp').innerText = `${yearsInput.value} Years`;

companyInput.addEventListener('input', function() {
    const options = document.querySelectorAll('#companyList option');
    for (let opt of options) {
        if (opt.value === this.value) {
            tickerInput.value = opt.getAttribute('data-ticker');
            this.setCustomValidity("");
            return;
        }
    }
    tickerInput.value = "";
    this.setCustomValidity("Please select a valid company from the list.");
});

let chart = null;

document.getElementById('calcForm').onsubmit = async (e) => {
    e.preventDefault();
    if (!tickerInput.value) {
        alert("Selection required from dropdown.");
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
            is_subscription: document.getElementById('isSub').checked
        })
    });

    const data = await res.json();
    document.getElementById('eqOut').innerText = data.final_equity.toLocaleString('en-GB', { style: 'currency', currency: 'GBP' });
    document.getElementById('mileOut').innerText = data.milestone;
    document.getElementById('vText').innerText = data.verdict;
    document.getElementById('vBox').classList.remove('d-none');

    const ctx = document.getElementById('mainChart').getContext('2d');
    if (chart) chart.destroy();
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                { label: 'Equity Growth (£)', data: data.equity_values, borderColor: '#007aff', backgroundColor: 'rgba(0,122,255,0.1)', fill: true, tension: 0.3 },
                { label: 'Asset Value (£)', data: data.asset_values, borderColor: '#dc3545', borderDash: [5,5], tension: 0.1 }
            ]
        },
        options: { plugins: { legend: { labels: { color: '#8e96a3' } } }, scales: { y: { ticks: { color: '#8e96a3' } }, x: { ticks: { color: '#8e96a3' } } } }
    });
};