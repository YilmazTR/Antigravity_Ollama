/**
 * Google Antigravity & Ollama Installation Doctor - Frontend Logic
 */

let pendingAction = null;

function logTerminal(message) {
    const term = document.getElementById("terminal-log");
    const now = new Date().toLocaleTimeString();
    term.textContent += `\n[${now}] ${message}`;
    term.scrollTop = term.scrollHeight;
}

// -------------------------------------------------------------
// Fetch & Render Diagnostics
// -------------------------------------------------------------
async function fetchDiagnostics() {
    logTerminal("Running diagnostic analysis...");
    const checklistContainer = document.getElementById("checklist-container");
    checklistContainer.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p style="text-align:center; color: var(--text-muted); font-size: 0.85rem;">Running diagnostic checks...</p>
        </div>
    `;

    try {
        const res = await fetch("/api/status");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        renderDiagnostics(data);
        logTerminal(`Diagnostics complete: ${data.summary.passed} Passed, ${data.summary.warnings} Warnings, ${data.summary.failed} Failed.`);
    } catch (err) {
        logTerminal(`Error fetching diagnostics: ${err.message}`);
        checklistContainer.innerHTML = `
            <div class="check-item status-FAIL">
                <div class="check-name">Diagnostics Error</div>
                <div class="check-msg">Failed to connect to Doctor backend API: ${err.message}</div>
            </div>
        `;
    }
}

function renderDiagnostics(data) {
    const { system, checks, models, summary, selected_model } = data;

    // 1. Metric Counts
    document.getElementById("count-passed").textContent = summary.passed;
    document.getElementById("count-warn").textContent = summary.warnings;
    document.getElementById("count-fail").textContent = summary.failed;

    // 2. Global Status Dot & Headline
    const dot = document.getElementById("global-status-dot");
    const title = document.getElementById("global-status-title");
    const desc = document.getElementById("global-status-desc");

    dot.className = "status-indicator-dot";
    if (summary.ready) {
        dot.classList.add("ready");
        title.textContent = "Google Antigravity is Ready for Local Ollama";
        desc.textContent = "All critical components, hardware accelerators, and model configurations passed validation.";
    } else if (summary.failed > 0) {
        dot.classList.add("error");
        title.textContent = `${summary.failed} Critical Configuration Error(s) Detected`;
        desc.textContent = "Google Antigravity cannot start local Ollama sessions until these issues are resolved.";
    } else {
        title.textContent = "Configuration Warnings Detected";
        desc.textContent = "System can run, but some performance or isolation recommendations are unfulfilled.";
    }

    // 3. Hardware Specs
    document.getElementById("spec-cpu").textContent = `${system.cpu || system.arch} (${system.os})`;
    document.getElementById("spec-ram").textContent = `${system.ram_gb || "--"} GB`;
    document.getElementById("spec-accel").textContent = system.metal_support ? "Metal Acceleration" : (system.arch === "arm64" ? "Apple Silicon" : "Standard GPU/CPU");
    document.getElementById("spec-python").textContent = `Python ${system.python_version || "--"}`;

    // 4. Checklist Items
    const container = document.getElementById("checklist-container");
    container.innerHTML = "";

    const fixableItems = [];

    checks.forEach(check => {
        const itemEl = document.createElement("div");
        itemEl.className = `check-item status-${check.status}`;

        let remediationHtml = "";
        if (check.remediation) {
            let actionBtnHtml = "";
            if (check.can_auto_fix && check.fix_action) {
                fixableItems.push(check);
                actionBtnHtml = `<button class="btn btn-sm btn-primary" onclick="requestFixConfirmation('${check.fix_action}', '${check.name}', '${escapeHtml(check.remediation)}')">Fix Now</button>`;
            }
            remediationHtml = `
                <div class="check-remediation">
                    <span><strong>Recommendation:</strong> ${escapeHtml(check.remediation)}</span>
                    ${actionBtnHtml}
                </div>
            `;
        }

        itemEl.innerHTML = `
            <div class="check-top">
                <span class="check-name">${escapeHtml(check.name)}</span>
                <span class="check-badge badge-${check.status}">${check.status}</span>
            </div>
            <div class="check-msg">${escapeHtml(check.message)}</div>
            ${check.details ? `<div class="check-details">${escapeHtml(check.details)}</div>` : ""}
            ${remediationHtml}
        `;
        container.appendChild(itemEl);
    });

    // 5. Remediation Action Bar
    const remediationSection = document.getElementById("remediation-section");
    const actionsContainer = document.getElementById("remediation-actions-container");

    if (fixableItems.length > 0) {
        remediationSection.style.display = "block";
        actionsContainer.innerHTML = "";
        fixableItems.forEach(item => {
            const btn = document.createElement("button");
            btn.className = "action-fix-btn";
            let label = "Resolve Issue";
            if (item.fix_action === "start_ollama") label = "🚀 Start Ollama Daemon";
            else if (item.fix_action === "install_sdk") label = "📦 Install google-antigravity SDK";
            else if (item.fix_action === "create_venv") label = "📁 Create .venv Virtual Environment";
            else if (item.fix_action === "pull_model" || item.fix_action === "pull_gemma") label = "📥 Pull Gemma 4 26B";

            btn.textContent = label;
            btn.onclick = () => requestFixConfirmation(item.fix_action, item.name, item.remediation);
            actionsContainer.appendChild(btn);
        });
    } else {
        remediationSection.style.display = "none";
    }

    // 6. Populate Models List & Select Dropdown
    renderModels(models, selected_model);
}

function renderModels(models, selected) {
    const listEl = document.getElementById("models-list");
    const selectEl = document.getElementById("select-test-model");

    if (!models || models.length === 0) {
        listEl.innerHTML = `<span class="loading-text" style="color: var(--status-fail);">No models found in Ollama registry.</span>`;
        selectEl.innerHTML = `<option value="">No models installed</option>`;
        return;
    }

    listEl.innerHTML = "";
    selectEl.innerHTML = "";

    models.forEach(m => {
        const isGemma4 = m.includes("gemma4:26b") || m.includes("gemma-4");
        const tag = document.createElement("span");
        tag.className = `model-tag ${m === selected ? "active" : ""}`;
        tag.innerHTML = `${isGemma4 ? '<span class="star">★</span> ' : ""}${m}`;
        tag.onclick = () => {
            selectEl.value = m;
            document.querySelectorAll(".model-tag").forEach(el => el.classList.remove("active"));
            tag.classList.add("active");
        };
        listEl.appendChild(tag);

        const opt = document.createElement("option");
        opt.value = m;
        opt.textContent = `${m}${isGemma4 ? " (Recommended)" : ""}`;
        if (m === selected) opt.selected = true;
        selectEl.appendChild(opt);
    });
}

// -------------------------------------------------------------
// Confirmation Modal Flow
// -------------------------------------------------------------
function requestFixConfirmation(action, checkName, remediation) {
    pendingAction = { action, checkName, remediation };

    const modal = document.getElementById("confirmation-modal");
    const title = document.getElementById("modal-title");
    const msg = document.getElementById("modal-message");
    const cmdBox = document.getElementById("modal-command-box");
    const code = cmdBox.querySelector("code");

    title.textContent = `Confirm: ${checkName}`;
    msg.textContent = `The doctor will execute the following remediation action on your machine:`;
    cmdBox.style.display = "block";

    if (action === "start_ollama") {
        code.textContent = "open -a Ollama (or 'ollama serve' in background)";
    } else if (action === "install_sdk") {
        code.textContent = "pip install google-antigravity";
    } else if (action === "create_venv") {
        code.textContent = "python3 -m venv .venv";
    } else if (action === "pull_model" || action === "pull_gemma") {
        code.textContent = "ollama pull gemma4:26b";
    } else {
        code.textContent = remediation;
    }

    modal.showModal();
}

async function executePendingAction() {
    if (!pendingAction) return;
    const { action } = pendingAction;
    const modal = document.getElementById("confirmation-modal");
    modal.close();

    logTerminal(`Executing confirmed action: ${action}...`);

    try {
        const res = await fetch("/api/action", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: action, confirmed: true })
        });
        const data = await res.json();
        if (data.success) {
            logTerminal(`Action '${action}' succeeded! Output: ${data.output || "Done"}`);
        } else {
            logTerminal(`Action '${action}' failed: ${data.output || data.error}`);
        }
    } catch (err) {
        logTerminal(`Execution error: ${err.message}`);
    } finally {
        pendingAction = null;
        // Refresh diagnostics after action
        setTimeout(fetchDiagnostics, 1500);
    }
}

// -------------------------------------------------------------
// Pull Model Modal
// -------------------------------------------------------------
function openPullModelModal() {
    document.getElementById("pull-model-modal").showModal();
}

async function executePullModel() {
    const input = document.getElementById("input-pull-model");
    const modelName = input.value.trim();
    if (!modelName) return;

    document.getElementById("pull-model-modal").close();
    logTerminal(`Initiating pull for model: ${modelName} (this may take several minutes)...`);

    try {
        const res = await fetch("/api/action", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "pull_model", model: modelName, confirmed: true })
        });
        const data = await res.json();
        if (data.success) {
            logTerminal(`Model ${modelName} pulled successfully!`);
        } else {
            logTerminal(`Failed to pull ${modelName}: ${data.output || data.error}`);
        }
    } catch (err) {
        logTerminal(`Pull error: ${err.message}`);
    } finally {
        fetchDiagnostics();
    }
}

// -------------------------------------------------------------
// Live Agent Verification Runner
// -------------------------------------------------------------
async function executeAgentTest() {
    const select = document.getElementById("select-test-model");
    const model = select.value;
    const prompt = document.getElementById("input-prompt").value.trim();
    const outputBox = document.getElementById("agent-output");
    const statusText = document.getElementById("output-status");
    const btn = document.getElementById("btn-run-test");

    if (!model) {
        alert("Please ensure at least one model is installed in Ollama.");
        return;
    }

    btn.disabled = true;
    statusText.textContent = "Connecting to agent...";
    outputBox.textContent = `Connecting to model '${model}' via LocalOpenAIAgentConfig...`;
    logTerminal(`Triggered verification test on model '${model}'...`);

    try {
        const res = await fetch("/api/test_agent", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                model: model,
                base_url: "http://localhost:11434/v1",
                prompt: prompt
            })
        });

        const data = await res.json();
        if (data.success) {
            statusText.textContent = "Complete (200 OK)";
            statusText.style.color = "var(--status-pass)";
            outputBox.textContent = data.response;
            logTerminal(`Agent verified successfully using ${data.engine}!`);
        } else {
            statusText.textContent = "Execution Failed";
            statusText.style.color = "var(--status-fail)";
            outputBox.textContent = `Error: ${data.error || "Agent returned non-zero status"}`;
            logTerminal(`Verification failed: ${data.error}`);
        }
    } catch (err) {
        statusText.textContent = "Network Error";
        statusText.style.color = "var(--status-fail)";
        outputBox.textContent = `Communication error: ${err.message}`;
        logTerminal(`Agent test network error: ${err.message}`);
    } finally {
        btn.disabled = false;
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// -------------------------------------------------------------
// Event Listeners
// -------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    // Initial fetch
    fetchDiagnostics();

    // Refresh button
    document.getElementById("btn-refresh").addEventListener("click", fetchDiagnostics);

    // Modal buttons
    document.getElementById("modal-btn-confirm").addEventListener("click", executePendingAction);
    document.getElementById("modal-btn-cancel").addEventListener("click", () => {
        document.getElementById("confirmation-modal").close();
        pendingAction = null;
    });

    // Pull modal
    document.getElementById("btn-pull-modal").addEventListener("click", openPullModelModal);
    document.getElementById("modal-pull-cancel").addEventListener("click", () => {
        document.getElementById("pull-model-modal").close();
    });
    document.getElementById("modal-pull-confirm").addEventListener("click", executePullModel);

    // Test Agent
    document.getElementById("btn-run-test").addEventListener("click", executeAgentTest);

    // Clear logs
    document.getElementById("btn-clear-logs").addEventListener("click", () => {
        document.getElementById("terminal-log").textContent = "[Logs cleared]";
    });
});
