// NetLogIQ Frontend Dashboard Logic

let currentTab = 'dashboard';
let ws = null;
let liveStreamActive = true;
let soundEnabled = true;
let currentLogOffset = 0;
const logPageLimit = 30;
let searchDebounceTimer = null;

// Chart Instances
let timelineChart = null;
let severityChart = null;
let categoryChart = null;
let vendorChart = null;

// Cached log list for modal inspection
let currentLoadedLogs = [];

// --- Theme Switcher Logic ---
const THEME_CONFIGS = {
    dark: {
        label: 'Dark NOC',
        icon: 'fa-solid fa-moon text-cyan-400',
        chartGrid: '#1e293b',
        chartText: '#94a3b8'
    },
    light: {
        label: 'Light Enterprise',
        icon: 'fa-solid fa-sun text-amber-500',
        chartGrid: '#e2e8f0',
        chartText: '#334155'
    },
    ocean: {
        label: 'Ocean Blue',
        icon: 'fa-solid fa-water text-blue-400',
        chartGrid: '#1a3250',
        chartText: '#94a3b8'
    },
    cyberpunk: {
        label: 'Cyber High-Contrast',
        icon: 'fa-solid fa-bolt text-emerald-400',
        chartGrid: '#1d2233',
        chartText: '#38bdf8'
    }
};

function initTheme() {
    const savedTheme = localStorage.getItem('netlogiq_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    applyThemeUI(savedTheme);

    // Listen for outside clicks to close dropdown
    window.addEventListener('click', (e) => {
        const dropdown = document.getElementById('themeDropdownMenu');
        const btn = document.getElementById('themeDropdownBtn');
        if (dropdown && !dropdown.contains(e.target) && !btn?.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });
}

function toggleThemeDropdown(event) {
    if (event) event.stopPropagation();
    const menu = document.getElementById('themeDropdownMenu');
    if (menu) menu.classList.toggle('hidden');
}

function setTheme(themeName) {
    localStorage.setItem('netlogiq_theme', themeName);
    document.documentElement.setAttribute('data-theme', themeName);
    applyThemeUI(themeName);
    const menu = document.getElementById('themeDropdownMenu');
    if (menu) menu.classList.add('hidden');
    updateChartTheme(themeName);
}

function applyThemeUI(themeName) {
    const cfg = THEME_CONFIGS[themeName] || THEME_CONFIGS['dark'];
    const icon = document.getElementById('themeCurrentIcon');
    const label = document.getElementById('themeCurrentLabel');

    if (icon) icon.className = cfg.icon;
    if (label) label.innerText = cfg.label;

    // Update checkmarks in dropdown
    ['dark', 'light', 'ocean', 'cyberpunk'].forEach(t => {
        const check = document.getElementById(`themeCheck-${t}`);
        if (check) {
            if (t === themeName) {
                check.classList.remove('hidden');
            } else {
                check.classList.add('hidden');
            }
        }
    });
}

function updateChartTheme(themeName) {
    const cfg = THEME_CONFIGS[themeName] || THEME_CONFIGS['dark'];
    const gridColor = cfg.chartGrid;
    const textColor = cfg.chartText;

    if (timelineChart) {
        if (timelineChart.options.plugins?.legend?.labels) {
            timelineChart.options.plugins.legend.labels.color = textColor;
        }
        if (timelineChart.options.scales?.x) {
            timelineChart.options.scales.x.grid.color = gridColor;
            timelineChart.options.scales.x.ticks.color = textColor;
        }
        if (timelineChart.options.scales?.y) {
            timelineChart.options.scales.y.grid.color = gridColor;
            timelineChart.options.scales.y.ticks.color = textColor;
        }
        timelineChart.update('none');
    }

    if (severityChart) {
        if (severityChart.options.plugins?.legend?.labels) {
            severityChart.options.plugins.legend.labels.color = textColor;
        }
        severityChart.update('none');
    }

    if (categoryChart) {
        if (categoryChart.options.scales?.x) {
            categoryChart.options.scales.x.grid.color = gridColor;
            categoryChart.options.scales.x.ticks.color = textColor;
        }
        if (categoryChart.options.scales?.y) {
            categoryChart.options.scales.y.ticks.color = textColor;
        }
        categoryChart.update('none');
    }

    if (vendorChart) {
        if (vendorChart.options.plugins?.legend?.labels) {
            vendorChart.options.plugins.legend.labels.color = textColor;
        }
        if (vendorChart.options.scales?.r) {
            vendorChart.options.scales.r.grid.color = gridColor;
        }
        vendorChart.update('none');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initWebSocket();
    initCharts();
    loadDashboardData();
    fetchLogs(0);
    fetchAlerts();
    loadNotificationConfig();

    // Auto refresh analytics every 10 seconds
    setInterval(() => {
        if (currentTab === 'dashboard' || currentTab === 'devices') {
            loadDashboardData();
        }
    }, 10000);
});

// --- Tab Switching ---
function switchTab(tabId) {
    currentTab = tabId;
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));

    const content = document.getElementById(`tabContent-${tabId}`);
    const btn = document.getElementById(`tabBtn-${tabId}`);
    if (content) content.classList.remove('hidden');
    if (btn) btn.classList.add('active');

    if (tabId === 'dashboard') {
        loadDashboardData();
    } else if (tabId === 'devices') {
        loadDeviceAndIPStats();
    } else if (tabId === 'logs') {
        fetchLogs(currentLogOffset);
    } else if (tabId === 'alerts') {
        fetchAlerts();
    }
}

// --- WebSocket Setup ---
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    const statusBadge = document.getElementById('wsStatusBadge');
    const statusText = document.getElementById('wsStatusText');

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            statusBadge.className = 'flex items-center space-x-1.5 text-xs px-2.5 py-1 rounded-md bg-emerald-950/40 text-emerald-400 border border-emerald-800/40';
            statusText.innerText = 'Live Feed Connected';
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'log') {
                    handleIncomingLog(msg.data);
                } else if (msg.type === 'alert') {
                    handleIncomingAlert(msg.data);
                }
            } catch (err) {
                console.error('Error parsing WS message', err);
            }
        };

        ws.onclose = () => {
            statusBadge.className = 'flex items-center space-x-1.5 text-xs px-2.5 py-1 rounded-md bg-rose-950/40 text-rose-400 border border-rose-800/40';
            statusText.innerText = 'Disconnected (Reconnecting...)';
            setTimeout(initWebSocket, 3000);
        };

        ws.onerror = () => {
            ws.close();
        };
    } catch (e) {
        console.error('WS init error', e);
        setTimeout(initWebSocket, 4000);
    }
}

function handleIncomingLog(log) {
    // Increment Total Logs KPI
    const kpiTotal = document.getElementById('kpiTotalLogs');
    if (kpiTotal) {
        let count = parseInt(kpiTotal.innerText.replace(/,/g, '')) || 0;
        kpiTotal.innerText = (count + 1).toLocaleString();
    }

    if (log.severity <= 2) {
        const kpiCrit = document.getElementById('kpiCriticalErrors');
        if (kpiCrit) {
            let count = parseInt(kpiCrit.innerText.replace(/,/g, '')) || 0;
            kpiCrit.innerText = (count + 1).toLocaleString();
        }
    }

    // If on Live Logs tab and streaming is active
    if (currentTab === 'logs' && liveStreamActive && currentLogOffset === 0) {
        const tbody = document.getElementById('logsTableBody');
        if (tbody) {
            currentLoadedLogs.unshift(log);
            if (currentLoadedLogs.length > logPageLimit) currentLoadedLogs.pop();
            const rowHtml = renderLogRow(log);
            tbody.insertAdjacentHTML('afterbegin', rowHtml);
            if (tbody.children.length > logPageLimit) {
                tbody.lastElementChild.remove();
            }
        }
    }
}

function handleIncomingAlert(alert) {
    // Play alert sound
    if (soundEnabled) {
        try {
            const audio = document.getElementById('alertAudio');
            if (audio) {
                audio.currentTime = 0;
                audio.play().catch(e => console.log('Audio autoplay prevented'));
            }
        } catch (e) {}
    }

    // Increment Active Alerts KPI
    const kpiAlerts = document.getElementById('kpiActiveAlerts');
    if (kpiAlerts) {
        let count = parseInt(kpiAlerts.innerText.replace(/,/g, '')) || 0;
        kpiAlerts.innerText = (count + 1).toLocaleString();
    }

    // Update nav tab badge
    const badge = document.getElementById('activeAlertCountBadge');
    if (badge) {
        let count = parseInt(badge.innerText) || 0;
        badge.innerText = count + 1;
        badge.classList.remove('hidden');
    }

    // Show floating toast
    showToastAlert(alert);

    // If currently on Alerts tab, refresh alerts list
    if (currentTab === 'alerts') {
        fetchAlerts();
    }
}

function showToastAlert(alert) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'pointer-events-auto bg-[#182234] border border-rose-600/80 rounded-xl p-3.5 shadow-2xl text-xs space-y-1 transform transition-all duration-300 translate-y-2 opacity-0 flex items-start space-x-3';
    toast.innerHTML = `
        <div class="h-7 w-7 rounded bg-rose-600/20 text-rose-400 flex items-center justify-center shrink-0 mt-0.5">
            <i class="fa-solid fa-triangle-exclamation"></i>
        </div>
        <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between">
                <span class="font-bold text-rose-400 uppercase tracking-wider text-[10px]">${alert.category}</span>
                <span class="text-[10px] text-gray-400">${new Date(alert.timestamp).toLocaleTimeString()}</span>
            </div>
            <div class="font-semibold text-white truncate">${alert.rule_name}</div>
            <div class="text-gray-300 font-mono text-[11px] truncate">${alert.hostname} (${alert.source_ip})</div>
            <div class="text-gray-400 text-[10px] truncate mt-0.5">${alert.message}</div>
        </div>
        <button onclick="this.parentElement.remove()" class="text-gray-500 hover:text-white text-xs">&times;</button>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    }, 50);

    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 300);
    }, 8000);
}

function toggleSoundAlert() {
    soundEnabled = !soundEnabled;
    const icon = document.getElementById('soundIcon');
    if (soundEnabled) {
        icon.className = 'fa-solid fa-volume-high text-cyan-400';
    } else {
        icon.className = 'fa-solid fa-volume-xmark text-gray-500';
    }
}

function toggleLiveStream() {
    liveStreamActive = !liveStreamActive;
    const btn = document.getElementById('liveStreamBtn');
    const icon = document.getElementById('liveStreamIcon');
    const text = document.getElementById('liveStreamText');

    if (liveStreamActive) {
        btn.className = 'flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-1.5 px-3 rounded-lg text-xs flex items-center justify-center space-x-1.5 shadow';
        icon.className = 'fa-solid fa-pause';
        text.innerText = 'Live';
    } else {
        btn.className = 'flex-1 bg-amber-600 hover:bg-amber-500 text-white font-medium py-1.5 px-3 rounded-lg text-xs flex items-center justify-center space-x-1.5 shadow';
        icon.className = 'fa-solid fa-play';
        text.innerText = 'Paused';
    }
}

// --- Data Fetching & Chart Rendering ---
async function loadDashboardData() {
    try {
        const [summary, severity, categories, vendors, timeline, devices] = await Promise.all([
            fetch('/api/stats/summary').then(r => r.json()),
            fetch('/api/stats/severity').then(r => r.json()),
            fetch('/api/stats/categories').then(r => r.json()),
            fetch('/api/stats/vendors').then(r => r.json()),
            fetch('/api/stats/timeline').then(r => r.json()),
            fetch('/api/stats/devices?limit=6').then(r => r.json())
        ]);

        // KPIs
        document.getElementById('kpiTotalLogs').innerText = (summary.total_logs || 0).toLocaleString();
        document.getElementById('kpiActiveAlerts').innerText = (summary.active_alerts || 0).toLocaleString();
        document.getElementById('kpiCriticalErrors').innerText = (summary.critical_errors || 0).toLocaleString();
        document.getElementById('kpiTotalDevices').innerText = (summary.total_devices || 0).toLocaleString();

        // Calculate Hardware faults (Reboots + PSU)
        const hwCount = categories
            .filter(c => ['REBOOT', 'POWER_SUPPLY', 'FAN_TEMPERATURE', 'HARDWARE_FAULT'].includes(c.event_category))
            .reduce((sum, c) => sum + c.count, 0);
        document.getElementById('kpiHardwareFaults').innerText = hwCount.toLocaleString();

        const alertBadge = document.getElementById('activeAlertCountBadge');
        if (summary.active_alerts > 0) {
            alertBadge.innerText = summary.active_alerts;
            alertBadge.classList.remove('hidden');
        } else {
            alertBadge.classList.add('hidden');
        }

        // Update Charts
        updateCharts(timeline, severity, categories, vendors);

        // Render Top Problematic Devices
        renderTopProblemDevices(devices);
    } catch (e) {
        console.error('Error loading dashboard data:', e);
    }
}

function initCharts() {
    // 1. Timeline Chart
    const ctxTimeline = document.getElementById('timelineChart').getContext('2d');
    timelineChart = new Chart(ctxTimeline, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Total Logs',
                    data: [],
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.1)',
                    fill: true,
                    tension: 0.3,
                    borderWidth: 2
                },
                {
                    label: 'Errors & Alerts',
                    data: [],
                    borderColor: '#f43f5e',
                    backgroundColor: 'rgba(244, 63, 94, 0.15)',
                    fill: true,
                    tension: 0.3,
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8', font: { size: 11 } } }
            },
            scales: {
                x: { grid: { color: '#1e293b' }, ticks: { color: '#64748b', font: { size: 10 } } },
                y: { grid: { color: '#1e293b' }, ticks: { color: '#64748b', font: { size: 10 } }, beginAtZero: true }
            }
        }
    });

    // 2. Severity Donut Chart
    const ctxSeverity = document.getElementById('severityChart').getContext('2d');
    severityChart = new Chart(ctxSeverity, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#ef4444', // 0 Emergency
                    '#dc2626', // 1 Alert
                    '#b91c1c', // 2 Critical
                    '#f97316', // 3 Error
                    '#eab308', // 4 Warning
                    '#3b82f6', // 5 Notice
                    '#06b6d4', // 6 Info
                    '#64748b'  // 7 Debug
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { color: '#94a3b8', font: { size: 10 } } }
            },
            cutout: '65%'
        }
    });

    // 3. Category Bar Chart
    const ctxCategory = document.getElementById('categoryChart').getContext('2d');
    categoryChart = new Chart(ctxCategory, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Events',
                data: [],
                backgroundColor: '#8b5cf6',
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: '#1e293b' }, ticks: { color: '#64748b', font: { size: 10 } }, beginAtZero: true },
                y: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10 } } }
            }
        }
    });

    // 4. Vendor Polar / Doughnut Chart
    const ctxVendor = document.getElementById('vendorChart').getContext('2d');
    vendorChart = new Chart(ctxVendor, {
        type: 'polarArea',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    'rgba(239, 68, 68, 0.7)',  // Huawei
                    'rgba(59, 130, 246, 0.7)',  // Cisco
                    'rgba(16, 185, 129, 0.7)',  // Juniper
                    'rgba(245, 158, 11, 0.7)',  // ZTE
                    'rgba(139, 92, 246, 0.7)',  // Nokia
                    'rgba(100, 116, 139, 0.7)'  // Generic
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { color: '#94a3b8', font: { size: 10 } } }
            },
            scales: {
                r: { grid: { color: '#1e293b' }, ticks: { display: false } }
            }
        }
    });

    // Apply active theme colors to charts
    updateChartTheme(localStorage.getItem('netlogiq_theme') || 'dark');
}

function updateCharts(timeline, severity, categories, vendors) {
    // 1. Timeline
    if (timeline && timelineChart) {
        timelineChart.data.labels = timeline.map(t => t.time_bucket.split('T')[1] || t.time_bucket);
        timelineChart.data.datasets[0].data = timeline.map(t => t.total);
        timelineChart.data.datasets[1].data = timeline.map(t => t.errors);
        timelineChart.update('none');
    }

    // 2. Severity
    if (severity && severityChart) {
        severityChart.data.labels = severity.map(s => `${s.severity} - ${s.severity_name}`);
        severityChart.data.datasets[0].data = severity.map(s => s.count);
        severityChart.update('none');
    }

    // 3. Category
    if (categories && categoryChart) {
        categoryChart.data.labels = categories.map(c => c.event_category);
        categoryChart.data.datasets[0].data = categories.map(c => c.count);
        categoryChart.update('none');
    }

    // 4. Vendor
    if (vendors && vendorChart) {
        vendorChart.data.labels = vendors.map(v => v.vendor);
        vendorChart.data.datasets[0].data = vendors.map(v => v.count);
        vendorChart.update('none');
    }
}

function renderTopProblemDevices(devices) {
    const tbody = document.getElementById('topProblemDevicesBody');
    if (!tbody) return;

    if (!devices || devices.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-gray-500 font-sans">No device logs recorded yet. Use the Simulator to send sample logs!</td></tr>`;
        return;
    }

    tbody.innerHTML = devices.map(d => `
        <tr class="hover:bg-gray-800/40 transition">
            <td class="py-2.5 px-3 font-semibold text-white">${d.hostname}</td>
            <td class="py-2.5 px-3 text-cyan-400">${d.source_ip}</td>
            <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded text-[10px] bg-gray-800 text-gray-300 border border-gray-700">${d.vendor}</span></td>
            <td class="py-2.5 px-3 text-gray-200">${d.total_logs}</td>
            <td class="py-2.5 px-3 font-bold ${d.error_count > 0 ? 'text-amber-400' : 'text-gray-400'}">${d.error_count}</td>
            <td class="py-2.5 px-3 font-bold ${d.alert_count > 0 ? 'text-rose-400' : 'text-gray-400'}">${d.alert_count}</td>
            <td class="py-2.5 px-3 text-gray-400 text-[10px]">${new Date(d.last_seen).toLocaleTimeString()}</td>
            <td class="py-2.5 px-3">
                <button onclick="filterLogsByDevice('${d.hostname}')" class="text-[11px] text-cyan-400 hover:text-cyan-300 font-sans">Inspect Logs &rarr;</button>
            </td>
        </tr>
    `).join('');
}

// --- Device & IP Wise Tables ---
async function loadDeviceAndIPStats() {
    try {
        const [devices, ips] = await Promise.all([
            fetch('/api/stats/devices?limit=50').then(r => r.json()),
            fetch('/api/stats/ips?limit=50').then(r => r.json())
        ]);

        const devBody = document.getElementById('deviceWiseTableBody');
        if (devBody) {
            devBody.innerHTML = devices.map(d => `
                <tr class="hover:bg-gray-800/40 transition">
                    <td class="py-2 px-3 text-white font-medium">${d.hostname}</td>
                    <td class="py-2 px-3"><span class="px-1.5 py-0.5 text-[9px] bg-gray-800 text-gray-300 rounded">${d.vendor}</span></td>
                    <td class="py-2 px-3 text-right text-gray-300">${d.total_logs}</td>
                    <td class="py-2 px-3 text-right font-bold ${d.error_count > 0 ? 'text-amber-400' : 'text-gray-400'}">${d.error_count}</td>
                    <td class="py-2 px-3 text-right font-bold ${d.alert_count > 0 ? 'text-rose-400' : 'text-gray-400'}">${d.alert_count}</td>
                    <td class="py-2 px-3 text-center">
                        <button onclick="filterLogsByDevice('${d.hostname}')" class="text-cyan-400 hover:underline text-[10px] font-sans">Filter</button>
                    </td>
                </tr>
            `).join('');
        }

        const ipBody = document.getElementById('ipWiseTableBody');
        if (ipBody) {
            ipBody.innerHTML = ips.map(i => `
                <tr class="hover:bg-gray-800/40 transition">
                    <td class="py-2 px-3 text-cyan-400 font-medium">${i.source_ip}</td>
                    <td class="py-2 px-3 text-white">${i.hostname}</td>
                    <td class="py-2 px-3 text-gray-400">${i.vendor}</td>
                    <td class="py-2 px-3 text-right text-gray-300">${i.total_logs}</td>
                    <td class="py-2 px-3 text-right font-bold ${i.error_count > 0 ? 'text-amber-400' : 'text-gray-400'}">${i.error_count}</td>
                    <td class="py-2 px-3 text-center">
                        <button onclick="filterLogsByIP('${i.source_ip}')" class="text-cyan-400 hover:underline text-[10px] font-sans">Filter</button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (e) {
        console.error('Error loading device/IP stats', e);
    }
}

function filterLogsByDevice(hostname) {
    switchTab('logs');
    document.getElementById('logSearchInput').value = hostname;
    fetchLogs(0);
}

function filterLogsByIP(ip) {
    switchTab('logs');
    document.getElementById('logSearchInput').value = ip;
    fetchLogs(0);
}

// --- Logs Explorer & Pagination ---
function debounceLogSearch() {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => fetchLogs(0), 300);
}

async function fetchLogs(offset = 0) {
    currentLogOffset = offset;
    const search = document.getElementById('logSearchInput').value;
    const vendor = document.getElementById('logVendorFilter').value;
    const severity = document.getElementById('logSeverityFilter').value;
    const category = document.getElementById('logCategoryFilter').value;
    const isAlert = document.getElementById('logAlertOnlyCheck').checked;

    let url = `/api/logs?limit=${logPageLimit}&offset=${offset}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (vendor && vendor !== 'ALL') url += `&vendor=${encodeURIComponent(vendor)}`;
    if (severity && severity !== '-1') url += `&severity=${encodeURIComponent(severity)}`;
    if (category && category !== 'ALL') url += `&category=${encodeURIComponent(category)}`;
    if (isAlert) url += `&is_alert_only=true`;

    try {
        const res = await fetch(url).then(r => r.json());
        currentLoadedLogs = res.logs || [];
        renderLogsTable(currentLoadedLogs);

        // Pagination controls
        const total = res.total || 0;
        const from = total > 0 ? offset + 1 : 0;
        const to = Math.min(offset + currentLoadedLogs.length, total);
        document.getElementById('paginationInfo').innerText = `Showing ${from} - ${to} of ${total.toLocaleString()} logs`;

        document.getElementById('prevPageBtn').disabled = offset <= 0;
        document.getElementById('nextPageBtn').disabled = offset + logPageLimit >= total;
    } catch (e) {
        console.error('Error fetching logs', e);
    }
}

function prevLogPage() {
    if (currentLogOffset >= logPageLimit) {
        fetchLogs(currentLogOffset - logPageLimit);
    }
}

function nextLogPage() {
    fetchLogs(currentLogOffset + logPageLimit);
}

function renderLogsTable(logs) {
    const tbody = document.getElementById('logsTableBody');
    if (!tbody) return;

    if (!logs || logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-gray-500 font-sans">No matching syslog entries found.</td></tr>`;
        return;
    }

    tbody.innerHTML = logs.map(renderLogRow).join('');
}

function renderLogRow(log) {
    const sevBadgeClass = `sev-badge-${log.severity}`;
    const catBadgeClass = `cat-badge-${log.event_category}`;

    return `
        <tr class="hover:bg-gray-800/40 transition border-b border-gray-800/40 ${log.is_alert ? 'bg-rose-950/15' : ''}">
            <td class="py-2 px-3 text-gray-400 whitespace-nowrap">${new Date(log.timestamp).toLocaleTimeString()}</td>
            <td class="py-2 px-3 whitespace-nowrap">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold ${sevBadgeClass}">
                    ${log.severity} - ${log.severity_name}
                </span>
            </td>
            <td class="py-2 px-3 text-gray-300 font-sans font-medium whitespace-nowrap">${log.vendor}</td>
            <td class="py-2 px-3 whitespace-nowrap">
                <span class="text-white font-medium">${log.hostname}</span>
                <span class="text-gray-500 text-[10px] block">${log.source_ip}</span>
            </td>
            <td class="py-2 px-3 whitespace-nowrap">
                <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${catBadgeClass}">
                    ${log.event_category}
                </span>
            </td>
            <td class="py-2 px-3 text-cyan-400 truncate max-w-[140px]">${log.mnemonic}</td>
            <td class="py-2 px-3 text-gray-200 truncate max-w-xs" title="${log.clean_message}">${log.clean_message}</td>
            <td class="py-2 px-3 text-center">
                <button onclick="viewLogDetail(${log.id})" class="text-gray-400 hover:text-cyan-400 p-1">
                    <i class="fa-solid fa-eye"></i>
                </button>
            </td>
        </tr>
    `;
}

function viewLogDetail(logId) {
    const log = currentLoadedLogs.find(l => l.id === logId);
    if (!log) return;

    document.getElementById('modalTitle').innerText = `${log.vendor} Syslog Entry #${log.id}`;
    document.getElementById('modalHost').innerText = log.hostname;
    document.getElementById('modalIP').innerText = log.source_ip;
    document.getElementById('modalVendor').innerText = log.vendor;
    document.getElementById('modalCategory').innerText = log.event_category;
    document.getElementById('modalMnemonic').innerText = log.mnemonic;
    document.getElementById('modalTimestamp').innerText = new Date(log.timestamp).toUTCString();
    document.getElementById('modalCleanMsg').innerText = log.clean_message;
    document.getElementById('modalRawMsg').innerText = log.raw_message;

    const sevBadge = document.getElementById('modalSevBadge');
    sevBadge.className = `px-2 py-0.5 rounded text-xs font-bold sev-badge-${log.severity}`;
    sevBadge.innerText = `${log.severity} - ${log.severity_name}`;

    document.getElementById('logDetailModal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('logDetailModal').classList.add('hidden');
}

function exportLogsCSV() {
    if (!currentLoadedLogs.length) return alert('No logs to export');
    const headers = ['ID', 'Timestamp', 'Vendor', 'Hostname', 'IP', 'Severity', 'Category', 'Mnemonic', 'Message'];
    const rows = currentLoadedLogs.map(l => [
        l.id,
        `"${l.timestamp}"`,
        `"${l.vendor}"`,
        `"${l.hostname}"`,
        `"${l.source_ip}"`,
        l.severity,
        `"${l.event_category}"`,
        `"${l.mnemonic}"`,
        `"${(l.clean_message || '').replace(/"/g, '""')}"`
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `syslog_export_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
}

// --- Critical Alerts View & Ack ---
async function fetchAlerts() {
    const status = document.getElementById('alertStatusFilter').value;
    try {
        const alerts = await fetch(`/api/alerts?status=${status}&limit=50`).then(r => r.json());
        const container = document.getElementById('alertsContainer');

        if (!alerts || alerts.length === 0) {
            container.innerHTML = `
                <div class="bg-[#111827] border border-gray-800 rounded-xl p-8 text-center text-gray-500">
                    <i class="fa-solid fa-circle-check text-emerald-400 text-3xl mb-2"></i>
                    <p class="font-medium text-white">No active network alerts found!</p>
                    <p class="text-xs text-gray-400 mt-1">All monitored Huawei, Cisco, Juniper, ZTE, and Nokia devices are operating normally.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = alerts.map(a => {
            const isAct = a.status === 'ACTIVE';
            return `
                <div class="bg-[#111827] border ${isAct ? 'border-rose-800/80 critical-alert-card' : 'border-gray-800'} rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 transition shadow-md">
                    <div class="flex items-start space-x-3.5">
                        <div class="h-10 w-10 rounded-xl ${isAct ? 'bg-rose-600/20 text-rose-400' : 'bg-gray-800 text-gray-400'} flex items-center justify-center shrink-0 mt-1">
                            <i class="fa-solid fa-triangle-exclamation text-lg"></i>
                        </div>
                        <div>
                            <div class="flex items-center space-x-2">
                                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-600 text-white">${a.category}</span>
                                <span class="font-bold text-sm text-white">${a.rule_name}</span>
                                <span class="text-xs text-gray-400">on <strong class="text-cyan-400 font-mono">${a.hostname}</strong> (${a.source_ip})</span>
                            </div>
                            <div class="text-xs text-gray-300 font-mono mt-1.5 break-words bg-gray-900/80 p-2 rounded border border-gray-800/80">
                                ${a.message}
                            </div>
                            <div class="flex items-center space-x-4 text-[11px] text-gray-500 mt-2">
                                <span><i class="fa-solid fa-building mr-1"></i>Vendor: <strong>${a.vendor}</strong></span>
                                <span><i class="fa-solid fa-clock mr-1"></i>${new Date(a.timestamp).toUTCString()}</span>
                                ${a.notified_channels ? `<span><i class="fa-solid fa-paper-plane mr-1 text-cyan-400"></i>Notified: ${a.notified_channels}</span>` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2 self-end md:self-center shrink-0">
                        ${isAct ? `
                            <button onclick="acknowledgeAlert(${a.id})" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow transition flex items-center space-x-1.5">
                                <i class="fa-solid fa-check"></i>
                                <span>Acknowledge</span>
                            </button>
                        ` : `
                            <span class="px-2.5 py-1 bg-gray-800 text-gray-400 rounded-lg text-xs font-medium border border-gray-700">
                                <i class="fa-solid fa-check-double text-emerald-400 mr-1"></i> Acknowledged
                            </span>
                        `}
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Error fetching alerts', e);
    }
}

async function acknowledgeAlert(alertId) {
    try {
        await fetch(`/api/alerts/${alertId}/acknowledge`, { method: 'POST' });
        fetchAlerts();
        loadDashboardData();
    } catch (e) {
        alert('Failed to acknowledge alert');
    }
}

// --- Notification Config Management ---
async function loadNotificationConfig() {
    try {
        const cfg = await fetch('/api/config').then(r => r.json());
        const notif = cfg.notifications || {};

        // Telegram
        if (notif.telegram) {
            document.getElementById('notifTgEnabled').checked = notif.telegram.enabled || false;
            document.getElementById('notifTgToken').value = notif.telegram.bot_token || '';
            document.getElementById('notifTgChatId').value = notif.telegram.chat_id || '';
        }

        // Slack
        if (notif.slack) {
            document.getElementById('notifSlackEnabled').checked = notif.slack.enabled || false;
            document.getElementById('notifSlackUrl').value = notif.slack.webhook_url || '';
            document.getElementById('notifSlackChannel').value = notif.slack.channel || '';
        }

        // Teams
        if (notif.ms_teams) {
            document.getElementById('notifTeamsEnabled').checked = notif.ms_teams.enabled || false;
            document.getElementById('notifTeamsUrl').value = notif.ms_teams.webhook_url || '';
        }

        // Email
        if (notif.email) {
            document.getElementById('notifEmailEnabled').checked = notif.email.enabled || false;
            document.getElementById('notifEmailSmtp').value = notif.email.smtp_server || '';
            document.getElementById('notifEmailPort').value = notif.email.smtp_port || 587;
            document.getElementById('notifEmailRecipients').value = (notif.email.to_emails || []).join(', ');
        }
    } catch (e) {
        console.error('Error loading config', e);
    }
}

async function saveNotificationSettings() {
    const payload = {
        telegram: {
            enabled: document.getElementById('notifTgEnabled').checked,
            bot_token: document.getElementById('notifTgToken').value.trim(),
            chat_id: document.getElementById('notifTgChatId').value.trim()
        },
        slack: {
            enabled: document.getElementById('notifSlackEnabled').checked,
            webhook_url: document.getElementById('notifSlackUrl').value.trim(),
            channel: document.getElementById('notifSlackChannel').value.trim()
        },
        ms_teams: {
            enabled: document.getElementById('notifTeamsEnabled').checked,
            webhook_url: document.getElementById('notifTeamsUrl').value.trim()
        },
        email: {
            enabled: document.getElementById('notifEmailEnabled').checked,
            smtp_server: document.getElementById('notifEmailSmtp').value.trim(),
            smtp_port: parseInt(document.getElementById('notifEmailPort').value) || 587,
            to_emails: document.getElementById('notifEmailRecipients').value.split(',').map(s => s.trim()).filter(Boolean)
        }
    };

    try {
        const res = await fetch('/api/config/notifications', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(r => r.json());

        alert(res.message || 'Settings saved successfully!');
    } catch (e) {
        alert('Failed to save settings: ' + e);
    }
}

async function testNotificationChannel(channel) {
    try {
        const res = await fetch('/api/config/test-notification', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channel: channel })
        }).then(r => r.json());

        alert(res.message);
    } catch (e) {
        alert('Test failed: ' + e);
    }
}
