// NetLogIQ Simulator & Testing Handlers

async function triggerScenarioSim(scenario) {
    try {
        const res = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: 1, scenario: scenario })
        }).then(r => r.json());

        if (res.status === 'success') {
            switchTab('dashboard');
            loadDashboardData();
        }
    } catch (e) {
        alert('Simulation error: ' + e);
    }
}

async function executeBatchSimulation() {
    const vendor = document.getElementById('simVendorSelect').value || null;
    const count = parseInt(document.getElementById('simCountInput').value) || 10;
    const mode = document.getElementById('simModeSelect').value;

    try {
        let endpoint = '/api/simulate';
        let body = { count: count, vendor: vendor };

        if (mode === 'udp') {
            endpoint = '/api/simulate/udp';
            body = { count: count, vendor: vendor };
        }

        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        }).then(r => r.json());

        if (res.status === 'success') {
            alert(`Successfully generated and ingested ${count} logs!`);
            switchTab('dashboard');
            loadDashboardData();
        }
    } catch (e) {
        alert('Batch simulation error: ' + e);
    }
}

async function submitManualLog() {
    const input = document.getElementById('manualLogInput');
    const msg = input.value.trim();
    if (!msg) return alert('Please enter a syslog string to test.');

    try {
        const res = await fetch('/api/logs/ingest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg, source_ip: '10.254.254.1' })
        }).then(r => r.json());

        if (res.status === 'success') {
            alert(`Log ingested successfully!\nDetected Vendor: ${res.log.vendor}\nSeverity: ${res.log.severity_name}\nCategory: ${res.log.event_category}\nIs Alert: ${res.log.is_alert}`);
            input.value = '';
            switchTab('logs');
            fetchLogs(0);
        }
    } catch (e) {
        alert('Ingestion error: ' + e);
    }
}
