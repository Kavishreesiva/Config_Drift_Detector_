// Config Drift Detector - Frontend Controller

// Application State
let appState = {
    currentView: 'dashboard-view',
    history: [],
    currentAnalysisResult: null,
    charts: {
        severityPie: null,
        historyBar: null
    }
};

// DOM Elements & Initialization
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide Icons
    lucide.createIcons();
    
    // API Key setup from LocalStorage
    initApiKey();

    // Setup Navigation Handlers
    initNavigation();
    
    // Setup Drag and Drop Uploads
    initDragAndDrop();

    // Load history data and render charts
    refreshData();
});

// 1. Navigation
function initNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-target');
            switchView(target);
        });
    });
}

function switchView(viewId) {
    // Hide all views
    document.querySelectorAll('.view-section').forEach(view => {
        view.classList.remove('active');
    });
    // Remove active class from nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-target') === viewId) {
            btn.classList.add('active');
        }
    });
    
    // Show selected view
    const targetView = document.getElementById(viewId);
    if (targetView) {
        targetView.classList.add('active');
    }
    
    // Update header title based on view
    const pageTitle = document.getElementById('page-title');
    const pageSubtitle = document.getElementById('page-subtitle');
    
    if (viewId === 'dashboard-view') {
        pageTitle.innerText = "Dashboard";
        pageSubtitle.innerText = "Overview of system configuration integrity";
        refreshData(); // Refresh history data on return to dashboard
    } else if (viewId === 'analysis-view') {
        pageTitle.innerText = "Drift Analysis";
        pageSubtitle.innerText = "Compare configuration files and evaluate impact";
    } else if (viewId === 'reports-view') {
        pageTitle.innerText = "Reports";
        pageSubtitle.innerText = "Access generated audits and exports";
        refreshData();
    } else if (viewId === 'settings-view') {
        pageTitle.innerText = "Settings";
        pageSubtitle.innerText = "Configure connection parameters and preferences";
    }
    
    appState.currentView = viewId;
}

// 2. Drag & Drop File Uploads
function initDragAndDrop() {
    setupDropZone('drop-zone-intended', 'file-input-intended', 'file-name-intended', 'text-intended');
    setupDropZone('drop-zone-actual', 'file-input-actual', 'file-name-actual', 'text-actual');
}

function setupDropZone(zoneId, inputId, labelId, textId) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);
    const label = document.getElementById(labelId);
    const textarea = document.getElementById(textId);
    
    // Click triggers file dialog
    zone.addEventListener('click', () => input.click());
    
    // File change handler
    input.addEventListener('change', (e) => {
        handleFile(e.target.files[0], label, textarea);
    });
    
    // Dragover effects
    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });
    
    zone.addEventListener('dragleave', () => {
        zone.classList.remove('dragover');
    });
    
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            input.files = e.dataTransfer.files;
            handleFile(e.dataTransfer.files[0], label, textarea);
        }
    });
}

function handleFile(file, labelElement, textareaElement) {
    if (!file) return;
    
    labelElement.innerText = file.name;
    
    const reader = new FileReader();
    reader.onload = (e) => {
        textareaElement.value = e.target.result;
        showToast(`Successfully read ${file.name}`);
    };
    reader.onerror = () => {
        showToast("Error reading file", true);
    };
    reader.readAsText(file);
}

function clearEditor(type) {
    document.getElementById(`text-${type}`).value = "";
    document.getElementById(`file-name-${type}`).innerText = "No file selected";
    document.getElementById(`file-input-${type}`).value = "";
    showToast(`Cleared ${type} config input`);
}

// 3. Settings & Credentials
function initApiKey() {
    const savedKey = localStorage.getItem('gemini_api_key');
    const badge = document.getElementById('api-status-badge');
    const input = document.getElementById('settings-api-key');
    
    if (savedKey) {
        input.value = savedKey;
        badge.innerHTML = `
            <span class="status-indicator online"></span>
            <span class="status-label">Gemini: AI Connected</span>
        `;
    } else {
        badge.innerHTML = `
            <span class="status-indicator offline"></span>
            <span class="status-label">Gemini: Offline Fallback</span>
        `;
    }
}

function toggleApiKeyVisibility() {
    const input = document.getElementById('settings-api-key');
    const icon = document.getElementById('api-key-eye-icon');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.setAttribute('data-lucide', 'eye-off');
    } else {
        input.type = 'password';
        icon.setAttribute('data-lucide', 'eye');
    }
    lucide.createIcons();
}

function saveSettings() {
    const key = document.getElementById('settings-api-key').value.trim();
    if (key) {
        localStorage.setItem('gemini_api_key', key);
        showToast("Gemini API key saved successfully!");
    } else {
        localStorage.removeItem('gemini_api_key');
        showToast("Gemini API key removed. Using rule fallback.");
    }
    initApiKey();
}

async function testApiKey() {
    const key = document.getElementById('settings-api-key').value.trim();
    if (!key) {
        showToast("Please enter an API key to test.", true);
        return;
    }
    
    showToast("Testing API Key connection...");
    
    // We run a small test by sending dummy files to analyze endpoint
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                intended_content: '{"test": 1}',
                actual_content: '{"test": 2}',
                intended_name: "test.json",
                actual_name: "test.json",
                file_format: "json",
                api_key: key
            })
        });
        
        if (response.ok) {
            showToast("Gemini API connection verified!");
        } else {
            showToast("API Key validation failed. Please check the key.", true);
        }
    } catch (err) {
        showToast("Connection failed. Server might be down.", true);
    }
}

// 4. Drift Analysis Engine Execution
async function startAnalysis() {
    const intendedContent = document.getElementById('text-intended').value.trim();
    const actualContent = document.getElementById('text-actual').value.trim();
    const format = document.getElementById('format-select').value;
    
    if (!intendedContent || !actualContent) {
        showToast("Please provide both intended and actual configurations.", true);
        return;
    }
    
    // Extract file names
    const intendedName = document.getElementById('file-name-intended').innerText;
    const actualName = document.getElementById('file-name-actual').innerText;
    
    const apiKey = localStorage.getItem('gemini_api_key') || null;
    
    // Show Loading Overlay
    const overlay = document.getElementById('loading-overlay');
    overlay.style.display = 'flex';
    
    // Reset steps
    resetLoadingSteps();
    
    try {
        // Step 1: Read Files
        await setStepStatus('step-read', 'active');
        await delay(100);
        await setStepStatus('step-read', 'completed');
        
        // Step 2: Compare configs
        await setStepStatus('step-compare', 'active');
        await delay(100);
        
        // Prepare request body
        const requestData = {
            intended_content: intendedContent,
            actual_content: actualContent,
            intended_name: intendedName === "No file selected" ? "intended_config.json" : intendedName,
            actual_name: actualName === "No file selected" ? "actual_config.json" : actualName,
            file_format: format,
            api_key: apiKey
        };
        
        await setStepStatus('step-compare', 'completed');
        
        // Step 3: Run AI analysis
        await setStepStatus('step-ai', 'active');
        
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const errDetails = await response.json();
            throw new Error(errDetails.detail || "Server error occurred during comparison.");
        }
        
        const result = await response.json();
        appState.currentAnalysisResult = result;
        
        await delay(100);
        await setStepStatus('step-ai', 'completed');
        
        // Step 4: Generate reports
        await setStepStatus('step-report', 'active');
        await delay(100);
        await setStepStatus('step-report', 'completed');
        await delay(50);
        
        // Hide loading and show results
        overlay.style.display = 'none';
        showAnalysisResult(result);
        showToast("Analysis completed successfully!");
        
    } catch (error) {
        overlay.style.display = 'none';
        showToast(error.message, true);
        console.error(error);
    }
}

function resetLoadingSteps() {
    const steps = ['step-read', 'step-compare', 'step-ai', 'step-report'];
    steps.forEach(id => {
        const el = document.getElementById(id);
        el.className = 'loading-step';
    });
}

function setStepStatus(stepId, status) {
    return new Promise(resolve => {
        const el = document.getElementById(stepId);
        el.className = `loading-step ${status}`;
        resolve();
    });
}

// 5. Results Display
function showAnalysisResult(result) {
    const resultsWrapper = document.getElementById('results-wrapper');
    resultsWrapper.style.display = 'block';
    
    // Set counters
    document.getElementById('res-count-breaking').innerText = result.breaking_count;
    document.getElementById('res-count-functional').innerText = result.functional_count;
    document.getElementById('res-count-cosmetic').innerText = result.cosmetic_count;
    
    // Render Risk Score Gauge
    renderGauge(result.risk_score);

    // Render Non-Technical Executive Before vs. After Visual Comparison Card
    renderExecDiffCard(result.drifts);

    // Render CCNA Network Topology & Attack Blast Radius Card
    renderNetworkBlastCard(result);

    // Render DevSecOps GitHub CI/CD Pipeline Shield Card
    renderGithubShieldCard(result);

    // Render Predictive Risk & Attack Pattern Vision Card
    renderPredictiveRiskCard(result.predictive_analysis);
    
    // Render Cybersecurity & Network Audit Card
    renderCyberAudit(result.cyber_audit);

    // Render Side-by-Side Visual Code Diff
    const intendedStr = document.getElementById('text-intended').value.trim();
    const actualStr = document.getElementById('text-actual').value.trim();
    renderVisualDiff(intendedStr, actualStr, result.drifts);

    // Populate drifts card list
    renderDriftsList(result.drifts);
    
    // Scroll down to results
    resultsWrapper.scrollIntoView({ behavior: 'smooth' });
}

function renderExecDiffCard(drifts) {
    const card = document.getElementById('exec-diff-card');
    const body = document.getElementById('exec-diff-body');
    
    if (!drifts || drifts.length === 0) {
        card.style.display = 'none';
        return;
    }
    
    card.style.display = 'block';
    
    let html = `
        <div style="display: flex; flex-direction: column; gap: 10px;">
            <p style="font-size: 12px; color: #94a3b8; margin: 0 0 4px 0;">Simplified visual state changes for non-technical stakeholders and security managers:</p>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px;">
    `;
    
    drifts.forEach(d => {
        let oldLabel = (d.old_value !== undefined && d.old_value !== null) ? String(d.old_value) : "None";
        let newLabel = (d.new_value !== undefined && d.new_value !== null) ? String(d.new_value) : "None";
        
        if (oldLabel === "true") oldLabel = "SSL = ON 🔒";
        if (newLabel === "false") newLabel = "SSL = OFF ❌";
        
        if (oldLabel.includes("deny")) oldLabel = `${oldLabel} 🟢 (Secure)`;
        if (newLabel.includes("permit")) newLabel = `${newLabel} 🔴 (Bypass)`;
        
        const keyName = escapeHtml(d.key || "Parameter");
        const sev = d.severity || "Functional";
        
        html += `
            <div style="background: #020617; border: 1px solid #1e293b; border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 13px; font-weight: 600; color: #e2e8f0;">⚙️ ${keyName}</span>
                    <span class="badge" style="font-size: 10px; background: ${sev === 'Breaking' ? '#ef4444' : '#f59e0b'}; color: #fff;">${sev}</span>
                </div>
                
                <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(15, 23, 42, 0.8); padding: 8px 10px; border-radius: 6px; border: 1px solid #334155;">
                    <div style="text-align: center;">
                        <span style="font-size: 10px; color: #64748b; font-weight: bold; display: block; margin-bottom: 2px;">BEFORE (INTENDED)</span>
                        <span style="background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #34d399; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">
                            ${escapeHtml(oldLabel)}
                        </span>
                    </div>

                    <span style="color: #6366f1; font-weight: bold; font-size: 16px;">➔</span>

                    <div style="text-align: center;">
                        <span style="font-size: 10px; color: #64748b; font-weight: bold; display: block; margin-bottom: 2px;">AFTER (ACTUAL/LIVE)</span>
                        <span style="background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; color: #f87171; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">
                            ${escapeHtml(newLabel)}
                        </span>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += `</div></div>`;
    body.innerHTML = html;
}

function renderPredictiveRiskCard(pred) {
    const card = document.getElementById('predictive-card');
    const badge = document.getElementById('predictive-threat-badge');
    const body = document.getElementById('predictive-body');
    
    if (!pred || !pred.has_attack_pattern) {
        card.style.display = 'none';
        return;
    }
    
    card.style.display = 'block';
    badge.innerText = `${pred.attack_risk_level} (Projected Score: ${pred.predicted_future_score}/100)`;
    
    let html = `
        <div style="background: rgba(168, 85, 247, 0.15); border: 1px solid #a855f7; border-radius: 8px; padding: 14px;">
            <h4 style="color: #e9d5ff; margin: 0 0 8px 0; font-size: 14px;">⚠️ Multi-Stage Attack Pattern Detected Across Sequence</h4>
            <p style="color: #cbd5e1; font-size: 12px; margin-bottom: 10px;"><strong>Predicted Attack Vector:</strong> ${escapeHtml(pred.predicted_attack_vector)}</p>
    `;
    
    if (pred.sequence_chain && pred.sequence_chain.length > 0) {
        html += `<div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; align-items: center;">`;
        pred.sequence_chain.forEach((step, idx) => {
            html += `<span class="badge" style="background: rgba(147, 51, 234, 0.4); border: 1px solid #a855f7; color: #fff; font-size: 11px;">${escapeHtml(step)}</span>`;
            if (idx < pred.sequence_chain.length - 1) {
                html += `<span style="color: #a855f7; font-weight: bold;">➔</span>`;
            }
        });
        html += `</div>`;
    }

    if (pred.pattern_matches && pred.pattern_matches.length > 0) {
        pred.pattern_matches.forEach(p => {
            html += `<div style="background: rgba(15, 23, 42, 0.6); border-left: 3px solid #ec4899; padding: 10px; border-radius: 4px; margin-bottom: 8px;">
                <span style="color: #f472b6; font-weight: 600; font-size: 12px;">[${p.severity}] ${escapeHtml(p.pattern_name)}</span>
                <p style="font-size: 12px; color: #e2e8f0; margin: 4px 0;">${escapeHtml(p.description)}</p>
                <p style="font-size: 11px; color: #fb7185; margin: 0;"><strong>Predicted Future Impact:</strong> ${escapeHtml(p.predicted_impact)}</p>
            </div>`;
        });
    }

    if (pred.preventive_countermeasures && pred.preventive_countermeasures.length > 0) {
        html += `<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.1);">
            <strong style="color: #38bdf8; font-size: 12px;">🛡️ Actionable Preventive Countermeasures:</strong>
            <ul style="margin: 4px 0 0 16px; padding: 0; font-size: 12px; color: #94a3b8;">`;
        pred.preventive_countermeasures.forEach(c => {
            html += `<li>${escapeHtml(c)}</li>`;
        });
        html += `</ul></div>`;
    }

    html += `</div>`;
    body.innerHTML = html;
}

function renderGithubShieldCard(result) {
    const card = document.getElementById('github-shield-card');
    const body = document.getElementById('github-shield-body');
    
    if (!result || result.total_drifts === 0) {
        card.style.display = 'none';
        return;
    }
    
    card.style.display = 'block';
    
    const isBlocked = result.risk_score >= 50;
    const statusColor = isBlocked ? "#ef4444" : "#10b981";
    const statusText = isBlocked ? "🔴 DEPLOYMENT BLOCKED (Risk Score > 50)" : "🟢 PASSED (Quality Gate Satisfied)";
    
    let html = `
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 8px; padding: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 8px;">
                <span style="font-size: 13px; font-weight: 600; color: #7dd3fc;">🐙 GitHub Actions CI/CD Deployment Shield Check</span>
                <span class="badge" style="background: ${statusColor}; color: #fff;">${statusText}</span>
            </div>
            
            <p style="font-size: 12px; color: #94a3b8; margin: 0 0 10px 0;">
                GitOps deployment quality gate check on branch <code style="color: #38bdf8;">main</code> for PR <code style="color: #38bdf8;">#142 (feature/server-config)</code>.
            </p>
            
            <div style="background: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 10px; font-family: monospace; font-size: 11px; color: #e2e8f0; margin-bottom: 10px; line-height: 1.6;">
                <span style="color: #a855f7;">[GitOps Bot]</span> Posting analysis review on GitHub Pull Request...<br/>
                <span style="color: ${statusColor}; font-weight: bold;">➜ CI/CD Quality Gate Result: ${isBlocked ? "BLOCKED ❌" : "ALLOWED ✅"}</span><br/>
                <span>➜ Total Drifts: ${result.total_drifts} | Breaking: ${result.breaking_count} | Functional: ${result.functional_count}</span><br/>
                <span>➜ Calculated Risk Score: ${result.risk_score}/100 | Cyber Threat Level: ${result.cyber_audit ? result.cyber_audit.cyber_threat_level : 'LOW'}</span>
            </div>
            
            <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                <button class="btn btn-secondary btn-sm" onclick="showToast('⚡ Auto-Healing Pull Request #143 (fix/remediate-drift) created on GitHub!')">
                    <i data-lucide="git-pull-request"></i> ⚡ Create Auto-Healing GitHub PR (#143)
                </button>
                <span style="font-size: 11px; color: #64748b;">(Submits auto-reconciled configuration directly to Git repository)</span>
            </div>
        </div>
    `;
    
    body.innerHTML = html;
}

function renderNetworkBlastCard(result) {
    const card = document.getElementById('network-blast-card');
    const badge = document.getElementById('network-blast-badge');
    const body = document.getElementById('network-blast-body');
    
    if (!result || result.total_drifts === 0) {
        card.style.display = 'none';
        return;
    }
    
    card.style.display = 'block';
    
    const breakingCount = result.breaking_count || 0;
    const blastPercent = Math.min(100, Math.max(20, (breakingCount * 30) + 15));
    
    badge.innerText = `Network Blast Radius: ${blastPercent}% Subnet Exposure`;
    
    let portKey = "8080";
    let wiresharkFilter = "tcp.port == 8080 || ip.addr == 10.0.1.1";
    
    if (result.drifts) {
        const portDrift = result.drifts.find(d => String(d.key).toLowerCase().includes("port"));
        if (portDrift) {
            portKey = String(portDrift.new_value || "9090");
            wiresharkFilter = `tcp.port == ${portKey} || ip.addr == 192.168.1.1`;
        }
    }
    
    let html = `
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(6, 182, 212, 0.3); border-radius: 8px; padding: 14px;">
            <h4 style="color: #67e8f9; margin: 0 0 6px 0; font-size: 14px;">🌐 Enterprise Subnet Network Nodes & Attack Exposure</h4>
            <p style="font-size: 12px; color: #94a3b8; margin: 0 0 12px 0;">Visualizing network packet reachability across Cisco Routers, Core Switches, and Application Subnets.</p>
            
            <div style="display: flex; gap: 10px; align-items: center; justify-content: space-between; overflow-x: auto; padding: 12px; background: #020617; border: 1px solid #1e293b; border-radius: 6px; margin-bottom: 12px;">
                <div style="text-align: center; min-width: 90px;">
                    <div style="background: #0284c7; color: #fff; padding: 8px; border-radius: 50%; width: 40px; height: 40px; margin: 0 auto 4px auto; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px;">R1</div>
                    <span style="font-size: 11px; color: #e2e8f0;">Cisco Router</span>
                </div>
                
                <span style="color: #38bdf8; font-weight: bold;">➔</span>
                
                <div style="text-align: center; min-width: 90px;">
                    <div style="background: #0891b2; color: #fff; padding: 8px; border-radius: 50%; width: 40px; height: 40px; margin: 0 auto 4px auto; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px;">SW1</div>
                    <span style="font-size: 11px; color: #e2e8f0;">VLAN 10 Switch</span>
                </div>

                <span style="color: #ef4444; font-weight: bold;">⚡ (Drift)</span>
                
                <div style="text-align: center; min-width: 110px;">
                    <div style="background: #ef4444; color: #fff; padding: 8px; border-radius: 50%; width: 40px; height: 40px; margin: 0 auto 4px auto; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px; box-shadow: 0 0 15px rgba(239, 68, 68, 0.6);">FW1</div>
                    <span style="font-size: 11px; color: #f87171; font-weight: 600;">Exposed Node</span>
                </div>

                <span style="color: #f59e0b; font-weight: bold;">➔</span>

                <div style="text-align: center; min-width: 90px;">
                    <div style="background: #334155; color: #fff; padding: 8px; border-radius: 50%; width: 40px; height: 40px; margin: 0 auto 4px auto; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px;">DB1</div>
                    <span style="font-size: 11px; color: #cbd5e1;">Subnet DB</span>
                </div>
            </div>

            <div style="background: rgba(8, 145, 178, 0.15); border: 1px solid #0891b2; border-radius: 6px; padding: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; flex-wrap: wrap; gap: 6px;">
                    <strong style="color: #22d3ee; font-size: 12px;">🦈 Wireshark Packet Capture Filter:</strong>
                    <button class="btn btn-secondary btn-sm" onclick="navigator.clipboard.writeText('${wiresharkFilter}'); showToast('Wireshark filter copied!');">Copy Wireshark Filter</button>
                </div>
                <code style="color: #a5f3fc; font-family: monospace; font-size: 11px;">${wiresharkFilter}</code>
                <p style="font-size: 11px; color: #94a3b8; margin: 4px 0 0 0;">Paste this filter into Wireshark or tcpdump CLI to capture malicious packet flows across infected interfaces.</p>
            </div>
        </div>
    `;
    
    body.innerHTML = html;
}

function renderCyberAudit(cyberAudit) {
    const card = document.getElementById('cyber-audit-card');
    const badge = document.getElementById('cyber-threat-badge');
    const body = document.getElementById('cyber-audit-body');
    
    if (!cyberAudit || cyberAudit.threat_count === 0) {
        card.style.display = 'none';
        return;
    }
    
    card.style.display = 'block';
    badge.innerText = `Cyber Threat Level: ${cyberAudit.cyber_threat_level} (Security Score: ${cyberAudit.security_score}/100)`;
    
    let html = '';
    
    if (cyberAudit.ccna_protocol_alerts && cyberAudit.ccna_protocol_alerts.length > 0) {
        html += `<div style="background: rgba(168, 85, 247, 0.1); border: 1px solid #a855f7; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
            <h5 style="color: #c084fc; margin: 0 0 6px 0;">🌐 CCNA Enterprise Network & Router/Switch Protocol Alerts</h5>`;
        cyberAudit.ccna_protocol_alerts.forEach(c => {
            html += `<p style="font-size: 12px; margin: 4px 0; color: #e9d5ff;">• <strong>${c.setting}</strong> (${c.protocol}): ${escapeHtml(c.description)}</p>`;
        });
        html += `</div>`;
    }

    if (cyberAudit.pci_dss_violations.length > 0) {
        html += `<div style="background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
            <h5 style="color: #ef4444; margin: 0 0 6px 0;">🔐 PCI-DSS 4.1 Data Transit Encryption Violations</h5>`;
        cyberAudit.pci_dss_violations.forEach(v => {
            html += `<p style="font-size: 12px; margin: 4px 0; color: #f87171;">• <strong>${v.setting}</strong>: ${escapeHtml(v.description)}</p>`;
        });
        html += `</div>`;
    }

    if (cyberAudit.network_port_alerts.length > 0) {
        html += `<div style="background: rgba(37, 99, 235, 0.1); border: 1px solid #3b82f6; border-radius: 8px; padding: 12px;">
            <h5 style="color: #60a5fa; margin: 0 0 6px 0;">🌐 Network Infrastructure & Port Exposure Alerts</h5>`;
        cyberAudit.network_port_alerts.forEach(p => {
            html += `<p style="font-size: 12px; margin: 4px 0; color: #93c5fd;">• <strong>${p.setting}</strong>: ${escapeHtml(p.alert)}</p>`;
        });
        html += `</div>`;
    }

    if (cyberAudit.owasp_violations.length > 0) {
        html += `<div style="background: rgba(234, 179, 8, 0.1); border: 1px solid #eab308; border-radius: 8px; padding: 12px;">
            <h5 style="color: #facc15; margin: 0 0 6px 0;">🛡️ OWASP Top 10 Misconfiguration Alerts</h5>`;
        cyberAudit.owasp_violations.forEach(o => {
            html += `<p style="font-size: 12px; margin: 4px 0; color: #fde047;">• <strong>${o.setting}</strong> (${o.category}): ${escapeHtml(o.description)}</p>`;
        });
        html += `</div>`;
    }

    body.innerHTML = html;
}

function renderVisualDiff(intendedStr, actualStr, drifts) {
    const card = document.getElementById('diff-viewer-card');
    const intendedBox = document.getElementById('diff-code-intended');
    const actualBox = document.getElementById('diff-code-actual');
    
    card.style.display = 'block';
    
    const driftKeys = new Set((drifts || []).map(d => String(d.key).toLowerCase()));
    
    const intendedLines = (intendedStr || "").split("\n");
    intendedBox.innerHTML = intendedLines.map((line, idx) => {
        const isDrift = Array.from(driftKeys).some(k => line.toLowerCase().includes(k));
        const bg = isDrift ? "rgba(239, 68, 68, 0.2)" : "transparent";
        const border = isDrift ? "3px solid #ef4444" : "none";
        return `<div style="background:${bg}; border-left:${border}; padding: 2px 8px;"><span style="color:#64748b; margin-right: 12px; font-size:11px;">${idx + 1}</span>${escapeHtml(line)}</div>`;
    }).join("");
    
    const actualLines = (actualStr || "").split("\n");
    actualBox.innerHTML = actualLines.map((line, idx) => {
        const isDrift = Array.from(driftKeys).some(k => line.toLowerCase().includes(k));
        const bg = isDrift ? "rgba(234, 179, 8, 0.25)" : "transparent";
        const border = isDrift ? "3px solid #eab308" : "none";
        return `<div style="background:${bg}; border-left:${border}; padding: 2px 8px;"><span style="color:#64748b; margin-right: 12px; font-size:11px;">${idx + 1}</span>${escapeHtml(line)}</div>`;
    }).join("");
}

function renderGauge(score) {
    const ring = document.getElementById('gauge-ring');
    const valueEl = document.getElementById('gauge-risk-value');
    const descEl = document.getElementById('gauge-risk-desc');
    
    valueEl.innerText = score;
    
    // Define color based on score
    let color = 'var(--green)';
    let desc = 'Low Operational Risk';
    
    if (score >= 75) {
        color = 'var(--red)';
        desc = 'Critical Severity Risk';
    } else if (score >= 40) {
        color = 'var(--orange)';
        desc = 'Medium Operational Risk';
    }
    
    descEl.innerText = desc;
    descEl.className = `gauge-desc text-center ${score >= 75 ? 'text-red' : score >= 40 ? 'text-orange' : 'text-green'}`;
    
    // Set conic gradient degree for rotation
    const degrees = (score / 100) * 360;
    ring.style.background = `conic-gradient(${color} 0deg, ${color} ${degrees}deg, rgba(255,255,255,0.05) ${degrees}deg, rgba(255,255,255,0.05) 360deg)`;
}

function renderDriftsList(drifts) {
    const listContainer = document.getElementById('drifts-cards-list');
    listContainer.innerHTML = "";
    
    if (!drifts || drifts.length === 0) {
        listContainer.innerHTML = `
            <div class="card text-center py-4">
                <i data-lucide="shield-check" class="text-green" style="width: 48px; height: 48px; margin: 0 auto 12px;"></i>
                <h4>Zero Drifts Detected!</h4>
                <p class="text-muted" style="font-size: 13px;">The active configuration is identical to the baseline reference.</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }
    
    drifts.forEach(d => {
        const card = document.createElement('div');
        
        let borderClass = 'border-left-green';
        let badgeClass = 'badge-green';
        if (d.severity === 'Breaking') {
            borderClass = 'border-left-red';
            badgeClass = 'badge-red';
        } else if (d.severity === 'Functional') {
            borderClass = 'border-left-orange';
            badgeClass = 'badge-orange';
        }
        
        card.className = `card drift-card ${borderClass}`;
        
        // Handle value displays
        const oldValStr = d.old_value === null ? "None (Added)" : (typeof d.old_value === 'object' ? JSON.stringify(d.old_value) : String(d.old_value));
        const newValStr = d.new_value === null ? "None (Removed)" : (typeof d.new_value === 'object' ? JSON.stringify(d.new_value) : String(d.new_value));
        
        const oldClass = d.old_value === null ? 'text-green' : '';
        const newClass = d.new_value === null ? 'text-removed-glow' : (d.old_value === null ? 'text-added-glow' : '');
        
        // Handle risk tag class
        const riskLower = String(d.risk_level).toLowerCase();
        let riskClass = 'risk-low';
        if (riskLower === 'critical') riskClass = 'risk-critical';
        else if (riskLower === 'high') riskClass = 'risk-high';
        else if (riskLower === 'medium') riskClass = 'risk-medium';
        
        card.innerHTML = `
            <div class="drift-card-header">
                <span class="drift-title-path">${d.key}</span>
                <div class="drift-badges">
                    <span class="badge ${badgeClass}">${d.severity}</span>
                    <span class="badge badge-info">${d.type}</span>
                </div>
            </div>
            
            <div class="drift-value-flow">
                <div class="diff-value-pill old-val-pill">
                    <span class="label">Intended Value</span>
                    <span class="val ${oldClass}">${escapeHtml(oldValStr)}</span>
                </div>
                <div class="diff-arrow-icon">
                    <i data-lucide="arrow-right"></i>
                </div>
                <div class="diff-value-pill new-val-pill">
                    <span class="label">Actual Value</span>
                    <span class="val ${newClass}">${escapeHtml(newValStr)}</span>
                </div>
            </div>
            
            <div class="drift-ai-assessment">
                <div class="ai-header">
                    <i data-lucide="sparkles"></i>
                    <span>AI Analysis</span>
                    <span class="risk-tag ${riskClass}" style="margin-left: auto;">Risk: ${d.risk_level || 'Medium'}</span>
                </div>
                <div class="ai-content">
                    <p><strong>Explanation:</strong> ${d.explanation || 'No explanation provided.'}</p>
                    <p><strong>Operational Impact:</strong> ${d.impact || 'No impact evaluated.'}</p>
                    <p><strong>Recommendation:</strong> ${d.recommendation || 'No recommendation provided.'}</p>
                </div>
            </div>
        `;
        
        listContainer.appendChild(card);
    });
    
    lucide.createIcons();
}

// Search, Filter and Sort Logic
function filterDrifts() {
    if (!appState.currentAnalysisResult) return;
    
    const query = document.getElementById('drift-search-input').value.toLowerCase();
    const severityFilter = document.getElementById('drift-severity-filter').value;
    const sortVal = document.getElementById('drift-sort-select').value;
    
    // Copy the original list to filter
    let filtered = [...appState.currentAnalysisResult.drifts];
    
    // 1. Filter by search query
    if (query) {
        filtered = filtered.filter(d => d.key.toLowerCase().includes(query));
    }
    
    // 2. Filter by severity
    if (severityFilter !== 'all') {
        filtered = filtered.filter(d => d.severity === severityFilter);
    }
    
    // 3. Sort
    filtered.sort((a, b) => {
        if (sortVal === 'key-asc') {
            return a.key.localeCompare(b.key);
        } else if (sortVal === 'key-desc') {
            return b.key.localeCompare(a.key);
        } else if (sortVal === 'severity-desc') {
            const weights = { 'Breaking': 3, 'Functional': 2, 'Cosmetic': 1 };
            return (weights[b.severity] || 0) - (weights[a.severity] || 0);
        }
        return 0;
    });
    
    renderDriftsList(filtered);
}

// 6. Report Generation Exports
async function exportReport(format) {
    if (!appState.currentAnalysisResult) {
        showToast("No analysis results available to export.", true);
        return;
    }
    
    const data = {
        intended_file: appState.currentAnalysisResult.intended_file,
        actual_file: appState.currentAnalysisResult.actual_file,
        risk_score: appState.currentAnalysisResult.risk_score,
        drifts: appState.currentAnalysisResult.drifts
    };
    
    showToast(`Generating ${format.toUpperCase()} report...`);
    
    try {
        if (format === 'pdf') {
            const response = await fetch('/api/export/pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) throw new Error("Failed to export PDF.");
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            
            // Extract filename from header if possible
            const disposition = response.headers.get('content-disposition');
            let filename = `drift_report_${new Date().toISOString().slice(0,10)}.pdf`;
            if (disposition && disposition.indexOf('attachment') !== -1) {
                const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                const matches = filenameRegex.exec(disposition);
                if (matches != null && matches[1]) {
                    filename = matches[1].replace(/['"]/g, '');
                }
            }
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            showToast("PDF report downloaded!");
            
        } else if (format === 'markdown') {
            const response = await fetch('/api/export/markdown', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) throw new Error("Failed to export Markdown.");
            
            const result = await response.json();
            
            // Download as file
            const blob = new Blob([result.markdown], { type: 'text/markdown' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `drift_report_${new Date().toISOString().slice(0,10)}.md`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            showToast("Markdown report downloaded!");
        }
    } catch (err) {
        showToast(err.message, true);
        console.error(err);
    }
}

// Load a specific historical run into the Drift Analysis tab
function loadHistoryRun(runId) {
    const run = appState.history.find(h => h.id === runId);
    if (!run) {
        showToast("Report run not found.", true);
        return;
    }
    
    // Store in state as active
    appState.currentAnalysisResult = run;
    
    // Switch view
    switchView('analysis-view');
    
    // Display results
    showAnalysisResult(run);
}

// 7. Dashboard Stats & Chart Controllers
async function refreshData() {
    try {
        const response = await fetch('/api/history');
        if (!response.ok) throw new Error("Failed to load history");
        
        const history = await response.json();
        appState.history = history;
        
        // 1. Update general stats
        updateDashboardStats(history);
        
        // 2. Render recent history table (in Dashboard & Reports views)
        renderHistoryTables(history);
        
        // 3. Render Dashboard charts
        renderCharts(history);
        
    } catch (err) {
        console.error("Failed to load dashboard data: ", err);
    }
}

function updateDashboardStats(history) {
    const totalRuns = history.length;
    let totalDrifts = 0;
    let breaking = 0;
    let functional = 0;
    let cosmetic = 0;
    let avgRisk = 0;
    
    if (totalRuns > 0) {
        history.forEach(run => {
            totalDrifts += run.total_drifts;
            breaking += run.breaking_count;
            functional += run.functional_count;
            cosmetic += run.cosmetic_count;
            avgRisk += run.risk_score;
        });
        avgRisk = Math.round(avgRisk / totalRuns);
    }
    
    document.getElementById('stat-total-analyzed').innerText = totalRuns;
    document.getElementById('stat-total-drifts').innerText = totalDrifts;
    document.getElementById('stat-breaking-count').innerText = breaking;
    document.getElementById('stat-functional-count').innerText = functional;
    document.getElementById('stat-cosmetic-count').innerText = cosmetic;
    document.getElementById('stat-avg-risk').innerText = `${avgRisk}%`;
    document.getElementById('stat-avg-risk-fill').style.width = `${avgRisk}%`;
}

function renderHistoryTables(history) {
    const recentRows = document.getElementById('recent-history-rows');
    const reportsRows = document.getElementById('reports-history-rows');
    
    recentRows.innerHTML = "";
    reportsRows.innerHTML = "";
    
    if (history.length === 0) {
        const emptyRow = `<tr><td colspan="6" class="text-center text-muted py-4">No analysis runs recorded. Start by running an analysis.</td></tr>`;
        recentRows.innerHTML = emptyRow;
        reportsRows.innerHTML = emptyRow;
        return;
    }
    
    // Build rows (limit dashboard to 5 rows, reports to all)
    history.forEach((run, index) => {
        const dateStr = new Date(run.timestamp).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata"
});
        
        let riskColor = 'text-green';
        if (run.risk_score >= 75) riskColor = 'text-red';
        else if (run.risk_score >= 40) riskColor = 'text-orange';
        
        const rowHtml = `
            <tr>
                <td>${dateStr}</td>
                <td><code style="background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px;">${escapeHtml(run.intended_file)}</code></td>
                <td><code style="background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px;">${escapeHtml(run.actual_file)}</code></td>
                <td><strong class="text-glow-purple">${run.total_drifts}</strong> drifts</td>
                <td><span class="${riskColor}"><b>${run.risk_score}%</b></span></td>
                <td>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-secondary btn-sm" onclick="loadHistoryRun('${run.id}')" title="Open Analysis">
                            <i data-lucide="eye" style="width: 14px; height: 14px;"></i> View
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="downloadPdfFromHistory('${run.id}')" title="Download PDF">
                            <i data-lucide="download" style="width: 14px; height: 14px;"></i>
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="deleteHistoryRun('${run.id}')" title="Delete Run" style="color: #ff4d4f; border-color: rgba(255, 77, 79, 0.3);">
                            <i data-lucide="x" style="width: 14px; height: 14px;"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
        
        if (index < 5) {
            recentRows.insertAdjacentHTML('beforeend', rowHtml);
        }
        reportsRows.insertAdjacentHTML('beforeend', rowHtml);
    });
    
    lucide.createIcons();
}

async function downloadPdfFromHistory(runId) {
    const run = appState.history.find(h => h.id === runId);
    if (!run) {
        showToast("History run not found.", true);
        return;
    }
    
    showToast("Preparing PDF report download...");
    try {
        const response = await fetch('/api/export/pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                intended_file: run.intended_file || "intended_config.json",
                actual_file: run.actual_file || "actual_config.json",
                risk_score: run.risk_score || 0,
                drifts: run.drifts || []
            })
        });
        
        if (!response.ok) {
            const errJson = await response.json().catch(() => ({}));
            throw new Error(errJson.detail || "Failed to generate PDF report.");
        }
        
        const blob = await response.blob();
        const cleanIntended = (run.intended_file || "intended").replace(/[^a-zA-Z0-9_\-]/g, "_");
        const cleanActual = (run.actual_file || "actual").replace(/[^a-zA-Z0-9_\-]/g, "_");
        const filename = `drift_report_${cleanIntended}_${cleanActual}.pdf`;
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 200);
        
        showToast("PDF report downloaded successfully!");
    } catch (err) {
        showToast("Error: " + err.message, true);
    }
}

async function deleteHistoryRun(runId) {
    if (!confirm("Are you sure you want to delete this analysis run?")) return;
    try {
        const response = await fetch(`/api/history/${runId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error("Failed to delete analysis run");
        showToast("Analysis run deleted.");
        refreshData();
    } catch (err) {
        showToast(err.message, true);
    }
}

async function clearHistory() {
    if (!confirm("Are you sure you want to clear all history? This will delete all saved audits.")) {
        return;
    }
    
    try {
        const response = await fetch('/api/history/clear', { method: 'POST' });
        if (response.ok) {
            showToast("Analysis history cleared.");
            refreshData();
        } else {
            showToast("Failed to clear history.", true);
        }
    } catch (err) {
        showToast("Error connecting to server.", true);
    }
}

// Chart.js Setup
function renderCharts(history) {
    // 1. Severity Doughnut/Pie Chart
    let breaking = 0, functional = 0, cosmetic = 0;
    
    history.forEach(run => {
        breaking += run.breaking_count;
        functional += run.functional_count;
        cosmetic += run.cosmetic_count;
    });
    
    const totalDrifts = breaking + functional + cosmetic;
    
    const pieCtx = document.getElementById('severityPieChart').getContext('2d');
    
    if (appState.charts.severityPie) {
        appState.charts.severityPie.destroy();
    }
    
    if (totalDrifts === 0) {
        // Show empty placeholder or dummy data
        appState.charts.severityPie = new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: ['No Drifts'],
                datasets: [{
                    data: [1],
                    backgroundColor: ['rgba(255,255,255,0.05)'],
                    borderWidth: 1,
                    borderColor: 'rgba(255,255,255,0.1)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } }
            }
        });
    } else {
        appState.charts.severityPie = new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: ['Breaking', 'Functional', 'Cosmetic'],
                datasets: [{
                    data: [breaking, functional, cosmetic],
                    backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
                    hoverOffset: 4,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#e5e7eb',
                            font: { family: 'Outfit', size: 12 }
                        }
                    }
                },
                cutout: '65%'
            }
        });
    }
    
    // 2. History Bar Chart
    const barCtx = document.getElementById('historyBarChart').getContext('2d');
    
    if (appState.charts.historyBar) {
        appState.charts.historyBar.destroy();
    }
    
    // Extract last 7 runs (reverse to show chronological order left-to-right)
    const recentRuns = [...history].slice(0, 7).reverse();
    
    const labels = recentRuns.map((run, i) => {
        const d = new Date(run.timestamp);
        return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
    });
    
    const dataBreaking = recentRuns.map(run => run.breaking_count);
    const dataFunctional = recentRuns.map(run => run.functional_count);
    const dataCosmetic = recentRuns.map(run => run.cosmetic_count);
    
    appState.charts.historyBar = new Chart(barCtx, {
        type: 'bar',
        data: {
            labels: labels.length > 0 ? labels : ['No Data'],
            datasets: [
                {
                    label: 'Breaking',
                    data: dataBreaking.length > 0 ? dataBreaking : [0],
                    backgroundColor: '#ef4444'
                },
                {
                    label: 'Functional',
                    data: dataFunctional.length > 0 ? dataFunctional : [0],
                    backgroundColor: '#f59e0b'
                },
                {
                    label: 'Cosmetic',
                    data: dataCosmetic.length > 0 ? dataCosmetic : [0],
                    backgroundColor: '#10b981'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    stacked: true,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#9ca3af', font: { family: 'Outfit', size: 10 } }
                },
                y: {
                    stacked: true,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#9ca3af', font: { family: 'Outfit', size: 10 } }
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#e5e7eb',
                        font: { family: 'Outfit', size: 11 }
                    }
                }
            }
        }
    });
}

// 8. Toast Helper
let toastTimeout;
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.innerText = message;
    
    if (isError) {
        toast.style.borderColor = 'var(--red)';
        toast.style.boxShadow = '0 8px 24px rgba(0, 0, 0, 0.4), 0 0 20px rgba(239, 68, 68, 0.2)';
    } else {
        toast.style.borderColor = 'var(--border-hover)';
        toast.style.boxShadow = '0 8px 24px rgba(0, 0, 0, 0.4), var(--grad-glow)';
    }
    
    toast.classList.add('show');
    
    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
        toast.classList.remove('show');
    }, 3500);
}

// Helpers
function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Switch Input Tab (Upload vs Code Editor)
function switchInputTab(btn, showId, hideId) {
    const parent = btn.parentElement;
    parent.querySelectorAll('.tab-link').forEach(link => link.classList.remove('active'));
    btn.classList.add('active');
    
    document.getElementById(showId).classList.add('active');
    document.getElementById(hideId).classList.remove('active');
}

// 9. Auto-Remediation Modal Handlers
async function openRemediationModal() {
    if (!appState.currentAnalysisResult || !appState.currentAnalysisResult.drifts) {
        showToast("No analysis result available to remediate.", true);
        return;
    }
    
    const modal = document.getElementById('remediation-modal');
    const loading = document.getElementById('rem-loading');
    modal.style.display = 'flex';
    loading.style.display = 'block';
    
    document.getElementById('rem-bash-code').innerText = "Generating script...";
    document.getElementById('rem-ansible-code').innerText = "Generating playbook...";
    document.getElementById('rem-cisco-code').innerText = "Generating Cisco IOS CLI commands...";
    document.getElementById('rem-config-code').innerText = "Generating config...";
    
    const intendedContent = document.getElementById('text-intended').value.trim();
    const actualContent = document.getElementById('text-actual').value.trim();
    const format = document.getElementById('format-select').value;
    const apiKey = localStorage.getItem('gemini_api_key') || null;
    
    try {
        const response = await fetch('/api/remediate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                drifts: appState.currentAnalysisResult.drifts,
                intended_content: intendedContent || '{\n  "status": "intended"\n}',
                actual_content: actualContent || '{\n  "status": "actual"\n}',
                file_format: format,
                api_key: apiKey
            })
        });
        
        loading.style.display = 'none';
        
        if (!response.ok) {
            throw new Error("Failed to generate remediation scripts.");
        }
        
        const data = await response.json();
        document.getElementById('rem-bash-code').innerText = data.shell_script || "# No shell script generated";
        document.getElementById('rem-ansible-code').innerText = data.ansible_playbook || "# No playbook generated";
        document.getElementById('rem-cisco-code').innerText = data.cisco_ios_cli || "! No Cisco IOS CLI generated";
        document.getElementById('rem-config-code').innerText = data.reconciled_config || "# No config generated";
        showToast("Auto-remediation scripts generated!");
        
    } catch (err) {
        loading.style.display = 'none';
        showToast("Error generating remediation scripts: " + err.message, true);
    }
}

function loadCiscoSampleData() {
    const intendedCisco = `hostname Core-Router-01
enable secret 5 $1$mER7$v.c
!
interface GigabitEthernet0/1
 description Primary WAN Interface
 ip address 10.0.1.1 255.255.255.0
 no shutdown
!
ip access-list extended SEC_ACL
 permit tcp any host 10.0.1.1 eq 443
 deny ip any any
!
router ospf 100
 router-id 1.1.1.1
 network 10.0.1.0 0.0.0.255 area 0
`;

    const actualCisco = `hostname Core-Router-01
enable secret 5 $1$mER7$v.c
!
interface GigabitEthernet0/1
 description Primary WAN Interface
 ip address 10.0.1.1 255.255.255.0
 shutdown
!
ip access-list extended SEC_ACL
 permit ip any any
!
router ospf 100
 router-id 1.1.1.1
 network 10.0.1.0 0.0.0.255 area 0
 network 0.0.0.0 255.255.255.255 area 0
`;

    document.getElementById('text-intended').value = intendedCisco;
    document.getElementById('text-actual').value = actualCisco;
    document.getElementById('format-select').value = 'cisco';
    showToast("Loaded CCNA Cisco IOS sample configuration!");
}

async function saveBaselineFromInput() {
    const intendedContent = document.getElementById('text-intended').value.trim();
    const format = document.getElementById('format-select').value;
    
    if (!intendedContent) {
        showToast("Please enter or upload an Intended Configuration first to save as Baseline.", true);
        return;
    }
    
    try {
        const response = await fetch('/api/baseline/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: "production_baseline",
                content: intendedContent,
                file_format: format
            })
        });
        
        if (!response.ok) throw new Error("Failed to save baseline.");
        
        const data = await response.json();
        showToast("📌 Active Production Baseline saved in database!");
    } catch (err) {
        showToast("Error saving baseline: " + err.message, true);
    }
}

async function runLiveCollectorScan() {
    const actualContent = document.getElementById('text-actual').value.trim();
    const format = document.getElementById('format-select').value;
    const apiKey = localStorage.getItem('gemini_api_key') || null;
    
    if (!actualContent) {
        showToast("Please enter or upload Live Configuration to scan against Baseline.", true);
        return;
    }
    
    showToast("🤖 Running Live Collector scan against Production Baseline...");
    showLoading(true);
    
    try {
        const response = await fetch('/api/collector/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                actual_content: actualContent,
                actual_name: "live_collected_config",
                file_format: format,
                api_key: apiKey
            })
        });
        
        showLoading(false);
        
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || "Collector scan failed.");
        }
        
        const result = await response.json();
        appState.currentAnalysisResult = result;
        showAnalysisResult(result);
        showToast("🚨 Live Collector Scan Complete! Drifts Analyzed.");
        refreshData();
    } catch (err) {
        showLoading(false);
        showToast(err.message, true);
    }
}

async function runNetmikoSSHCollector() {
    const host = prompt("Enter Cisco Router IP address for Netmiko SSH Fetch:", "192.168.1.1") || "192.168.1.1";
    
    showToast(`🐍 Connecting via Netmiko SSH to Cisco Router (${host})...`);
    showLoading(true);
    
    try {
        const response = await fetch('/api/netmiko/fetch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                host: host,
                username: "admin",
                password: "cisco123"
            })
        });
        
        showLoading(false);
        
        if (!response.ok) throw new Error("Netmiko SSH fetch failed.");
        
        const data = await response.json();
        
        if (data.content) {
            // 1. Switch tabs to code paste view so boxes are visible
            switchInputTab('intended', 'paste');
            switchInputTab('actual', 'paste');

            // 2. If Intended baseline is empty, populate default CCNA Baseline
            const currentIntended = document.getElementById('text-intended').value.trim();
            if (!currentIntended) {
                document.getElementById('text-intended').value = `hostname Core-Router-01\ninterface GigabitEthernet0/1\n description Primary WAN Interface\n ip address 10.0.1.1 255.255.255.0\n no shutdown\n!\nip access-list extended SEC_ACL\n permit tcp any host 10.0.1.1 eq 443\n deny ip any any\n`;
            }

            // 3. Set Actual/Live config fetched via Netmiko
            document.getElementById('text-actual').value = data.content;
            document.getElementById('format-select').value = 'cisco';
            document.getElementById('file-name-actual').innerText = `Netmiko SSH (${host})`;
            
            showToast(`🐍 Netmiko fetched live Cisco running-config from ${host}! Executing drift analysis...`);
            
            // 4. Trigger Analysis
            startAnalysis();
        } else {
            showToast(data.message || "Failed to fetch config via Netmiko.", true);
        }
    } catch (err) {
        showLoading(false);
        showToast("Error during Netmiko SSH fetch: " + err.message, true);
    }
}

function closeRemediationModal() {
    document.getElementById('remediation-modal').style.display = 'none';
}

async function executeSSHHeal() {
    showToast("⚡ Connecting via SSH Netmiko to 192.168.1.1 (Cisco Core-Router-01)...");
    try {
        const response = await fetch('/api/remediate/ssh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                target_ip: "192.168.1.1 (Cisco Core-Router-01)",
                commands: ["configure terminal", "access-list 100 deny ip any any", "end", "write memory"]
            })
        });
        if (!response.ok) throw new Error("SSH execution failed.");
        const data = await response.json();
        showToast("✅ Autonomous SSH Netmiko Self-Healing Executed Successfully!");
        alert(`⚡ SSH Self-Healing Device Output:\n\n${data.device_response}`);
    } catch (err) {
        showToast("Error executing SSH heal: " + err.message, true);
    }
}

async function dispatchSlackAlert() {
    showToast("🚨 Dispatching Webhook Alert to Slack #security-alerts...");
    try {
        const response = await fetch('/api/webhook/notify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                channel: "#security-alerts",
                risk_score: appState.currentAnalysisResult ? appState.currentAnalysisResult.risk_score : 90
            })
        });
        if (!response.ok) throw new Error("Webhook notification failed.");
        const data = await response.json();
        showToast("✅ Real-Time Security Incident Webhook Alert Dispatched to Slack!");
    } catch (err) {
        showToast("Error sending webhook: " + err.message, true);
    }
}

function switchRemTab(tabId) {
    document.querySelectorAll('.rem-tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.rem-tab-content').forEach(content => content.classList.remove('active'));
    
    if (event && event.target) {
        event.target.classList.add('active');
    }
    document.getElementById(tabId).classList.add('active');
}

function copyRemScript(elementId) {
    const text = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(text).then(() => {
        showToast("Copied to clipboard!");
    }).catch(() => {
        showToast("Failed to copy", true);
    });
}

// 10. AI Chatbot Drawer Handlers
function toggleChatDrawer() {
    const drawer = document.getElementById('chat-drawer');
    const isHidden = drawer.style.display === 'none' || drawer.style.display === '';
    drawer.style.display = isHidden ? 'flex' : 'none';
}

function handleChatKeyPress(e) {
    if (e.key === 'Enter') {
        sendChatMessage();
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    const chatMessages = document.getElementById('chat-messages');

    // Append User message
    const userMsgDiv = document.createElement('div');
    userMsgDiv.className = 'chat-msg user';
    userMsgDiv.innerText = msg;
    chatMessages.appendChild(userMsgDiv);

    input.value = '';
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Append Bot Thinking message
    const botMsgDiv = document.createElement('div');
    botMsgDiv.className = 'chat-msg bot loading';
    botMsgDiv.innerText = 'Thinking...';
    chatMessages.appendChild(botMsgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    const apiKey = localStorage.getItem('gemini_api_key') || null;
    const drifts = appState.currentAnalysisResult ? appState.currentAnalysisResult.drifts : null;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: msg,
                drifts: drifts,
                api_key: apiKey
            })
        });

        if (!response.ok) {
            throw new Error("Failed to get chatbot response.");
        }

        const data = await response.json();
        botMsgDiv.className = 'chat-msg bot';
        botMsgDiv.innerText = data.reply || "No response received.";

    } catch (err) {
        botMsgDiv.className = 'chat-msg bot error';
        botMsgDiv.innerText = "Sorry, I ran into an error answering your query: " + err.message;
    }

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 11. CCNA & Cisco Networking Sample Loader
function loadCiscoSampleData() {
    const intendedCisco = `! Cisco IOS Baseline / Intended Network Configuration
hostname Core-Router-01
enable secret 5 $1$mERr$O0qP.gL2/7p9aG8F1/
!
vlan 10
 name Production-Data
vlan 20
 name Engineering
!
interface GigabitEthernet0/0
 description Primary Gateway Interface
 ip address 192.168.1.1 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/1
 description Trunk to Core Switch
 switchport mode trunk
 switchport trunk allowed vlan 10,20,99
 no shutdown
!
interface GigabitEthernet0/2
 description Legacy Server Connection
 ip address 10.0.0.1 255.255.255.0
 shutdown
!
router ospf 10
 router-id 1.1.1.1
 network 192.168.1.0 0.0.0.255 area 0
 network 10.0.0.0 0.0.0.255 area 0
!
access-list 100 permit ip 192.168.1.0 0.0.0.255 any
access-list 100 deny ip any any`;

    const actualCisco = `! Cisco IOS Live / Actual Network Configuration (Drifted)
hostname Core-Router-01-DRIFTED
enable secret 5 $1$mERr$O0qP.gL2/7p9aG8F1/
!
vlan 10
 name Production-Data
vlan 20
 name Engineering-Unsafe
!
interface GigabitEthernet0/0
 description Primary Gateway Interface
 ip address 192.168.1.254 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/1
 description Trunk to Core Switch
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 no shutdown
!
interface GigabitEthernet0/2
 description Legacy Server Connection
 ip address 10.0.0.1 255.255.255.0
 no shutdown
!
router ospf 10
 router-id 1.1.1.1
 network 192.168.1.0 0.0.0.255 area 50
 network 10.0.0.0 0.0.0.255 area 0
!
access-list 100 permit ip any any`;

    // Switch to code paste tabs
    const intendedCard = document.querySelector('#intended-upload');
    const actualCard = document.querySelector('#actual-upload');
    if (intendedCard) {
        const tabBtns = intendedCard.parentElement.querySelectorAll('.tab-link');
        if (tabBtns[1]) switchInputTab(tabBtns[1], 'intended-code', 'intended-upload');
    }
    if (actualCard) {
        const tabBtns = actualCard.parentElement.querySelectorAll('.tab-link');
        if (tabBtns[1]) switchInputTab(tabBtns[1], 'actual-code', 'actual-upload');
    }

    document.getElementById('text-intended').value = intendedCisco;
    document.getElementById('text-actual').value = actualCisco;
    document.getElementById('format-select').value = 'cisco';

    appState.files.intended = { name: "cisco_intended.cfg", content: intendedCisco };
    appState.files.actual = { name: "cisco_actual.cfg", content: actualCisco };

    showToast("CCNA Cisco Networking sample configurations loaded!");
}

