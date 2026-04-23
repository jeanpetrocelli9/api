const API_BASE = "";
let pollInterval = null;
let autoDownloadedFiles = new Set(); // Track files already triggered for browser download

// Ensure logs auto-scroll
const logConsole = document.getElementById('logConsole');
function scrollToBottom() {
    logConsole.scrollTop = logConsole.scrollHeight;
}

// Update file input label
function updateFileName() {
    const input = document.getElementById('fileUpload');
    const label = document.getElementById('fileLabelText');
    if (input.files.length > 0) {
        label.innerHTML = `<i class="fa-solid fa-file-lines"></i> ${input.files[0].name}`;
        label.style.borderColor = "var(--primary-color)";
    } else {
        label.innerHTML = `<i class="fa-solid fa-upload"></i> Escolher arquivo`;
        label.style.borderColor = "var(--panel-border)";
    }
}

// Toast Notification
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.style.borderLeftColor = isError ? "var(--danger-color)" : "var(--primary-color)";
    toast.classList.remove('hidden');
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// API Calls
async function startDownloadRequest(endpoint, payload, isFormData = false) {
    try {
        const options = {
            method: 'POST',
        };

        if (isFormData) {
            options.body = payload;
        } else {
            options.headers = { 'Content-Type': 'application/json' };
            options.body = JSON.stringify(payload);
        }

        const response = await fetch(`${API_BASE}${endpoint}`, options);
        const data = await response.json();

        if (response.ok) {
            showToast(data.message);
            startPolling();
        } else {
            showToast(data.detail || "Erro ao iniciar download", true);
        }
    } catch (error) {
        console.error(error);
        showToast("Erro de conexão com o servidor. O backend está rodando?", true);
    }
}

function downloadProfile() {
    const url = document.getElementById('profileUrl').value;
    if (!url) return showToast("Insira o URL do perfil", true);
    startDownloadRequest('/download/profile', { url: url });
}

function downloadVideo() {
    const url = document.getElementById('videoUrl').value;
    if (!url) return showToast("Insira o URL do vídeo", true);
    startDownloadRequest('/download/video', { url: url });
}

function downloadList() {
    const fileInput = document.getElementById('fileUpload');
    if (fileInput.files.length === 0) return showToast("Selecione um arquivo .txt", true);

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    startDownloadRequest('/download/list', formData, true);
}

async function stopDownload() {
    try {
        const res = await fetch(`${API_BASE}/stop`, { method: 'POST' });
        if (res.ok) showToast("Parando downloads...");
    } catch (e) {
        showToast("Erro ao conectar", true);
    }
}



async function initializeApp() {
    try {
        const res = await fetch(`${API_BASE}/initialize`, { method: 'POST' });
        if (res.ok) {
            showToast("Aplicativo Inicializado!", false);
            const logConsole = document.getElementById('logConsole');
            if (logConsole) logConsole.innerHTML = "";
            document.getElementById('downloadedCount').textContent = "0";
            document.getElementById('urlText').textContent = "Aguardando tarefas...";
            document.getElementById('percentText').textContent = "0%";
            document.getElementById('progressBar').style.width = "0%";

            // clear inputs
            const pUrl = document.getElementById('profileUrl');
            if (pUrl) pUrl.value = '';
            const vUrl = document.getElementById('videoUrl');
            if (vUrl) vUrl.value = '';
            const fUp = document.getElementById('fileUpload');
            if (fUp) fUp.value = '';

            updateFileName();
            refreshFiles();
            autoDownloadedFiles.clear(); // Clear tracking on reset
        }
    } catch (e) {
        showToast("Erro ao inicializar o servidor", true);
    }
}

// Status Polling & UI Update
function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(fetchStatus, 1000);
    fetchStatus(); // immediate call
}

async function fetchStatus() {
    try {
        const res = await fetch(`${API_BASE}/status`);
        if (!res.ok) return;
        const data = await res.json();

        updateUI(data);

        // Optional: stop polling if completely idle (but keeping it running handles manual backend starts)
        // We'll just keep polling every second for a fluid UI sync
    } catch (e) {
        // Backend probably offline
        document.getElementById('statusIndicator').className = "status-badge idle";
        document.getElementById('statusIndicator').textContent = "Offline";
    }
}

let lastLogCount = 0;
function updateUI(status) {
    const btnStop = document.getElementById('btnStop');
    const indicator = document.getElementById('statusIndicator');
    const urlText = document.getElementById('urlText');
    const percentText = document.getElementById('percentText');
    const progressBar = document.getElementById('progressBar');
    const downloadedCount = document.getElementById('downloadedCount');

    // Status Badge
    if (status.is_active) {
        indicator.className = "status-badge active";
        indicator.textContent = "Baixando";
        btnStop.disabled = false;

        urlText.textContent = status.current_url || "Processando...";
        percentText.textContent = `${status.progress}%`;
        progressBar.style.width = `${status.progress}%`;

        // Check for new finished files to trigger auto-download
        if (status.finished_files && status.finished_files.length > 0) {
            const autoEnabled = document.getElementById('autoDownloadToggle').checked;
            status.finished_files.forEach(filename => {
                if (!autoDownloadedFiles.has(filename)) {
                    autoDownloadedFiles.add(filename);
                    if (autoEnabled) {
                        triggerBrowserDownload(filename);
                    }
                }
            });
        }
    } else {
        indicator.className = "status-badge idle";
        indicator.textContent = "Inativo";
        btnStop.disabled = true;

        urlText.textContent = "Aguardando tarefas...";
        percentText.textContent = "0%";
        progressBar.style.width = "0%";

        // Refresh files list automatically when idle after a burst
        if (lastLogCount > 0 && status.logs.length === lastLogCount && !window.hasRefreshedOnceAfterIdle) {
            refreshFiles();
            window.hasRefreshedOnceAfterIdle = true;
        }
    }

    if (status.is_active) window.hasRefreshedOnceAfterIdle = false;

    // Stats
    downloadedCount.textContent = status.downloaded_count;

    // Logs
    if (status.logs.length !== lastLogCount) {
        // Find new logs
        const newLogs = status.logs.slice(lastLogCount);
        newLogs.forEach(entry => {
            const div = document.createElement('div');
            div.className = 'log-entry';

            const timeSpan = document.createElement('span');
            timeSpan.className = 'log-time';
            const now = new Date();
            timeSpan.textContent = `[${now.toLocaleTimeString()}]`;

            const textSpan = document.createElement('span');
            textSpan.textContent = entry;

            div.appendChild(timeSpan);
            div.appendChild(textSpan);
            logConsole.appendChild(div);
        });

        // Remove excess elements to prevent memory issues in DOM
        while (logConsole.children.length > 200) {
            logConsole.removeChild(logConsole.firstChild);
        }

        lastLogCount = status.logs.length;
        scrollToBottom();
    }
}

async function refreshFiles() {
    try {
        const res = await fetch(`${API_BASE}/files`);
        if (!res.ok) return;
        const files = await res.json();

        const list = document.getElementById('filesList');
        list.innerHTML = "";

        if (files.length === 0) {
            list.innerHTML = '<p class="empty-state">Nenhum arquivo baixado recentemente.</p>';
            return;
        }

        files.forEach(f => {
            const item = document.createElement('div');
            item.className = "file-item";
            item.innerHTML = `
                <div class="file-icon"><i class="fa-solid fa-play"></i></div>
                <div class="file-details" style="flex:1;">
                    <span class="file-name" title="${f.name}">${f.name}</span>
                    <span class="file-meta">${f.folder} • ${f.size_mb} MB</span>
                </div>
                <a href="${f.url}" download="${f.name}" target="_blank" class="btn-icon" style="color: var(--primary-color);">
                    <i class="fa-solid fa-download"></i>
                </a>
            `;
            list.appendChild(item);
        });

    } catch (e) {
        console.error("Failed to fetch files");
    }
}

function triggerBrowserDownload(filename) {
    const fileUrl = `/downloads/${filename}`;
    showToast(`Baixando para dispositivo: ${filename}`);

    // Create a temporary link and click it
    const link = document.createElement('a');
    link.href = fileUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Initialize
window.onload = () => {
    startPolling();
    refreshFiles();
};
