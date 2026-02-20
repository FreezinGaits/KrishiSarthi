/**
 * Krishi-Sarthi — Demo Frontend Controller
 * ==========================================
 * Handles chat messaging, multi-session management, image diagnosis,
 * voice recording, location sharing, and side-panel rendering.
 */

const API_BASE = '/api';
const STORAGE_KEY_SESSIONS = 'krishi_sessions';
const STORAGE_KEY_ACTIVE = 'krishi_active_session';

// ══════════════════════════════════════════════════
//  Chat Session Manager
// ══════════════════════════════════════════════════

class ChatSessionManager {
    constructor() {
        this.sessions = this._load();
        this.activeId = localStorage.getItem(STORAGE_KEY_ACTIVE) || null;

        // Ensure there's always at least one session
        if (this.sessions.length === 0) {
            this.createSession(false);
        } else if (!this.activeId || !this.sessions.find(s => s.id === this.activeId)) {
            this.activeId = this.sessions[0].id;
            this._saveActiveId();
        }
    }

    _load() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY_SESSIONS)) || [];
        } catch {
            return [];
        }
    }

    _save() {
        localStorage.setItem(STORAGE_KEY_SESSIONS, JSON.stringify(this.sessions));
    }

    _saveActiveId() {
        localStorage.setItem(STORAGE_KEY_ACTIVE, this.activeId);
    }

    createSession(render = true) {
        const id = 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
        const session = {
            id,
            title: `Chat ${this.sessions.length + 1}`,
            createdAt: new Date().toISOString(),
            messages: [],
        };
        this.sessions.unshift(session);
        this.activeId = id;
        this._save();
        this._saveActiveId();
        if (render) {
            renderSessionList();
            renderChatMessages();
        }
        return session;
    }

    getActive() {
        return this.sessions.find(s => s.id === this.activeId) || this.sessions[0];
    }

    switchSession(id) {
        if (id === this.activeId) return;
        const session = this.sessions.find(s => s.id === id);
        if (!session) return;
        this.activeId = id;
        this._saveActiveId();
        renderSessionList();
        renderChatMessages();
    }

    deleteSession(id) {
        this.sessions = this.sessions.filter(s => s.id !== id);
        if (this.sessions.length === 0) {
            this.createSession(false);
        }
        if (this.activeId === id) {
            this.activeId = this.sessions[0].id;
            this._saveActiveId();
        }
        this._save();
        renderSessionList();
        renderChatMessages();

        // Also delete on backend (fire-and-forget)
        fetch(`${API_BASE}/sessions/${id}`, { method: 'DELETE' }).catch(() => {});
    }

    renameSession(id, newTitle) {
        const session = this.sessions.find(s => s.id === id);
        if (session) {
            session.title = newTitle.trim() || session.title;
            this._save();
            renderSessionList();
        }
    }

    addMessage(role, content, extra = {}) {
        const session = this.getActive();
        if (!session) return;
        session.messages.push({
            role,
            content,
            timestamp: Date.now(),
            ...extra,
        });
        this._save();
    }

    getMessages() {
        const session = this.getActive();
        return session ? session.messages : [];
    }
}

// Singleton
const sessionManager = new ChatSessionManager();

// ══════════════════════════════════════════════════
//  DOM References
// ══════════════════════════════════════════════════

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const chatMessages = $('#chatMessages');
const chatInput = $('#chatInput');
const sendBtn = $('#sendBtn');
const micBtn = $('#micBtn');
const imageBtn = $('#imageBtn');
const imageInput = $('#imageInput');
const locationBtn = $('#locationBtn');
const statusDot = $('#statusDot');
const recordingIndicator = $('#recordingIndicator');

// Side panel
const tabBtns = $$('.tab-btn');
const tabContents = $$('.tab-content');

// Modal
const imageModal = $('#imageModal');
const imagePreview = $('#imagePreview');
const modalClose = $('#modalClose');
const modalCancel = $('#modalCancel');
const modalSend = $('#modalSend');

// Diagnosis
const diagnosisEmpty = $('#diagnosisEmpty');
const diagnosisCard = $('#diagnosisCard');
const diseaseName = $('#diseaseName');
const confidenceBadge = $('#confidenceBadge');
const treatmentText = $('#treatmentText');
const pesticideText = $('#pesticideText');
const diagnosisPreview = $('#diagnosisPreview');

// Vendors
const vendorsEmpty = $('#vendorsEmpty');
const vendorList = $('#vendorList');

// ══════════════════════════════════════════════════
//  Tab Switching
// ══════════════════════════════════════════════════

tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(tc => tc.classList.remove('active'));
        btn.classList.add('active');
        const target = document.getElementById(tab + 'Tab');
        if (target) target.classList.add('active');
    });
});

// ══════════════════════════════════════════════════
//  Session List Rendering
// ══════════════════════════════════════════════════

function renderSessionList() {
    const container = $('#sessionList');
    if (!container) return;

    const sessions = sessionManager.sessions;

    if (sessions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">💬</span>
                <p>No chats yet</p>
                <p class="hint">Start a new conversation</p>
            </div>`;
        return;
    }

    container.innerHTML = sessions.map(s => {
        const isActive = s.id === sessionManager.activeId;
        const msgCount = s.messages.length;
        const lastMsg = s.messages.length > 0
            ? s.messages[s.messages.length - 1].content.slice(0, 40) + (s.messages[s.messages.length - 1].content.length > 40 ? '…' : '')
            : 'No messages yet';
        const timeAgo = getTimeAgo(s.createdAt);

        return `
            <div class="session-item ${isActive ? 'active' : ''}" data-id="${s.id}">
                <div class="session-item-main" onclick="sessionManager.switchSession('${s.id}')">
                    <div class="session-item-header">
                        <span class="session-title" id="title-${s.id}">${escapeHtml(s.title)}</span>
                        <span class="session-time">${timeAgo}</span>
                    </div>
                    <div class="session-item-preview">${escapeHtml(lastMsg)}</div>
                    <div class="session-item-meta">${msgCount} message${msgCount !== 1 ? 's' : ''}</div>
                </div>
                <div class="session-item-actions">
                    <button class="session-action-btn rename-btn" onclick="startRename('${s.id}')" title="Rename">✏️</button>
                    <button class="session-action-btn delete-btn" onclick="confirmDelete('${s.id}')" title="Delete">🗑️</button>
                </div>
            </div>`;
    }).join('');
}

function startRename(id) {
    const titleEl = document.getElementById(`title-${id}`);
    if (!titleEl) return;
    const currentTitle = titleEl.textContent;
    titleEl.outerHTML = `<input class="session-title-input" id="rename-${id}" value="${escapeHtml(currentTitle)}"
        onblur="finishRename('${id}')" onkeydown="if(event.key==='Enter')finishRename('${id}')" autofocus>`;
    const input = document.getElementById(`rename-${id}`);
    if (input) {
        input.focus();
        input.select();
    }
}

function finishRename(id) {
    const input = document.getElementById(`rename-${id}`);
    if (!input) return;
    sessionManager.renameSession(id, input.value);
}

function confirmDelete(id) {
    const session = sessionManager.sessions.find(s => s.id === id);
    if (!session) return;
    if (sessionManager.sessions.length === 1) {
        // Last session — clear it instead
        session.messages = [];
        sessionManager._save();
        renderSessionList();
        renderChatMessages();
        return;
    }
    sessionManager.deleteSession(id);
}

// ══════════════════════════════════════════════════
//  Chat Message Rendering
// ══════════════════════════════════════════════════

const WELCOME_HTML = `
    <div class="message bot-message">
        <div class="message-avatar">🌿</div>
        <div class="message-content">
            <p><strong>🙏 नमस्ते! मैं कृषि-सारथी हूँ।</strong></p>
            <p>मैं आपकी मदद कर सकता हूँ:</p>
            <ul>
                <li>🌱 <strong>फसल रोग पहचान</strong> — फोटो भेजें</li>
                <li>🎤 <strong>आवाज़ में बात करें</strong> — माइक दबाएं</li>
                <li>📍 <strong>नज़दीकी दुकान</strong> — कीटनाशक दुकान ढूंढें</li>
            </ul>
            <p class="hint">Try: "Meri tamatar ki fasal mein kale dhabbe hain"</p>
        </div>
    </div>`;

function renderChatMessages() {
    const messages = sessionManager.getMessages();
    if (messages.length === 0) {
        chatMessages.innerHTML = WELCOME_HTML;
    } else {
        chatMessages.innerHTML = messages.map(m => {
            if (m.role === 'user') {
                return `
                    <div class="message user-message">
                        <div class="message-avatar">👤</div>
                        <div class="message-content">
                            <p>${escapeHtml(m.content)}</p>
                            ${m.imageUrl ? `<img class="chat-image" src="${m.imageUrl}" alt="Uploaded crop image">` : ''}
                        </div>
                    </div>`;
            } else {
                return `
                    <div class="message bot-message">
                        <div class="message-avatar">🌿</div>
                        <div class="message-content">
                            ${formatBotMessage(m.content)}
                        </div>
                    </div>`;
            }
        }).join('');
    }
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addMessageToUI(role, content, extra = {}) {
    // Remove welcome on first message
    const welcome = chatMessages.querySelector('.bot-message:first-child');
    if (sessionManager.getMessages().length <= 1 && welcome) {
        chatMessages.innerHTML = '';
    }

    const div = document.createElement('div');
    div.className = `message ${role === 'user' ? 'user-message' : 'bot-message'}`;

    if (role === 'user') {
        div.innerHTML = `
            <div class="message-avatar">👤</div>
            <div class="message-content">
                <p>${escapeHtml(content)}</p>
                ${extra.imageUrl ? `<img class="chat-image" src="${extra.imageUrl}" alt="Uploaded crop image">` : ''}
            </div>`;
    } else {
        div.innerHTML = `
            <div class="message-avatar">🌿</div>
            <div class="message-content">
                ${formatBotMessage(content)}
            </div>`;
    }

    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTypingIndicator() {
    const div = document.createElement('div');
    div.className = 'message bot-message typing-msg';
    div.innerHTML = `
        <div class="message-avatar">🌿</div>
        <div class="message-content">
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>`;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const el = chatMessages.querySelector('.typing-msg');
    if (el) el.remove();
}

// ══════════════════════════════════════════════════
//  Send Message
// ══════════════════════════════════════════════════

let pendingImage = null;

async function sendMessage(text, imageBase64 = null) {
    const message = (text || '').trim();
    if (!message && !imageBase64) return;

    // Disable input
    chatInput.disabled = true;
    sendBtn.disabled = true;

    // Add user message to session
    const extra = imageBase64 ? { imageUrl: `data:image/jpeg;base64,${imageBase64.slice(0, 50)}...` } : {};
    sessionManager.addMessage('user', message, extra);
    addMessageToUI('user', message, extra);

    // Auto-title: use first message as session title
    const active = sessionManager.getActive();
    if (active.messages.length === 1 && message) {
        const autoTitle = message.slice(0, 30) + (message.length > 30 ? '…' : '');
        sessionManager.renameSession(active.id, autoTitle);
    }

    showTypingIndicator();

    try {
        const body = {
            message,
            session_id: sessionManager.activeId,
            language: 'hi',
        };
        if (imageBase64) body.image_base64 = imageBase64;

        const resp = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-API-Key': 'krishi-sarthi-api-key-change-this' },
            body: JSON.stringify(body),
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        removeTypingIndicator();

        // Store and render bot reply
        sessionManager.addMessage('assistant', data.reply);
        addMessageToUI('assistant', data.reply);

        // Handle diagnosis data
        if (data.diagnosis) {
            showDiagnosis(data.diagnosis);
        }

        // Handle vendor data
        if (data.vendors) {
            showVendors(data.vendors);
        }

        // Update session list (preview text change)
        renderSessionList();

    } catch (err) {
        removeTypingIndicator();
        const errMsg = '❌ कुछ गड़बड़ हो गई। कृपया दोबारा कोशिश करें। (Something went wrong)';
        sessionManager.addMessage('assistant', errMsg);
        addMessageToUI('assistant', errMsg);
        console.error('Chat error:', err);
    } finally {
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

// ══════════════════════════════════════════════════
//  Event Listeners — Chat Input
// ══════════════════════════════════════════════════

sendBtn.addEventListener('click', () => {
    sendMessage(chatInput.value, pendingImage);
    chatInput.value = '';
    pendingImage = null;
});

chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendBtn.click();
    }
});

// ══════════════════════════════════════════════════
//  Image Upload
// ══════════════════════════════════════════════════

imageBtn.addEventListener('click', () => imageInput.click());

imageInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
        const base64 = reader.result.split(',')[1];
        imagePreview.src = reader.result;
        pendingImage = base64;
        imageModal.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
    imageInput.value = '';
});

modalClose.addEventListener('click', () => {
    imageModal.classList.add('hidden');
    pendingImage = null;
});
modalCancel.addEventListener('click', () => {
    imageModal.classList.add('hidden');
    pendingImage = null;
});
modalSend.addEventListener('click', () => {
    imageModal.classList.add('hidden');
    sendMessage(chatInput.value || 'Diagnose this crop image', pendingImage);
    chatInput.value = '';
    pendingImage = null;
});

// ══════════════════════════════════════════════════
//  Voice Recording (Web Speech API)
// ══════════════════════════════════════════════════

let isRecording = false;
let recognition = null;

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'hi-IN';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        chatInput.value = transcript;
        stopRecording();
    };

    recognition.onerror = () => stopRecording();
    recognition.onend = () => stopRecording();
}

micBtn.addEventListener('click', () => {
    if (!recognition) {
        alert('Voice recognition is not supported in this browser.');
        return;
    }
    if (isRecording) {
        recognition.stop();
        stopRecording();
    } else {
        recognition.start();
        startRecording();
    }
});

function startRecording() {
    isRecording = true;
    micBtn.classList.add('recording');
    recordingIndicator.classList.add('visible');
}

function stopRecording() {
    isRecording = false;
    micBtn.classList.remove('recording');
    recordingIndicator.classList.remove('visible');
}

// ══════════════════════════════════════════════════
//  Location Sharing
// ══════════════════════════════════════════════════

locationBtn.addEventListener('click', () => {
    if (!navigator.geolocation) {
        alert('Geolocation is not supported.');
        return;
    }

    locationBtn.disabled = true;
    locationBtn.textContent = '📍 Getting...';

    navigator.geolocation.getCurrentPosition(
        async (pos) => {
            const { latitude, longitude } = pos.coords;
            locationBtn.textContent = '📍 Location';
            locationBtn.disabled = false;

            // Search for vendors near this location
            try {
                const resp = await fetch(`${API_BASE}/find-vendors`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-API-Key': 'krishi-sarthi-api-key-change-this' },
                    body: JSON.stringify({
                        latitude,
                        longitude,
                        query: 'pesticide shop',
                        radius_km: 10,
                    }),
                });
                if (resp.ok) {
                    const data = await resp.json();
                    showVendors(data);
                    // Switch to vendors tab
                    tabBtns.forEach(b => b.classList.remove('active'));
                    tabContents.forEach(tc => tc.classList.remove('active'));
                    const vendorTabBtn = document.querySelector('[data-tab="vendors"]');
                    if (vendorTabBtn) vendorTabBtn.classList.add('active');
                    const vendorsTab = document.getElementById('vendorsTab');
                    if (vendorsTab) vendorsTab.classList.add('active');
                }
            } catch (err) {
                console.error('Vendor search error:', err);
            }
        },
        () => {
            locationBtn.textContent = '📍 Location';
            locationBtn.disabled = false;
            alert('Location access denied.');
        }
    );
});

// ══════════════════════════════════════════════════
//  Diagnosis Display
// ══════════════════════════════════════════════════

function showDiagnosis(data) {
    if (!diagnosisCard) return;
    diagnosisEmpty.classList.add('hidden');
    diagnosisCard.classList.remove('hidden');

    const top = data.predictions?.[0] || data;
    diseaseName.textContent = data.top_disease || top.disease_name || '—';
    const conf = Math.round((data.top_confidence || top.confidence || 0) * 100);
    confidenceBadge.textContent = `${conf}%`;
    confidenceBadge.className = `confidence-badge ${conf >= 80 ? 'high' : conf >= 50 ? 'medium' : 'low'}`;
    treatmentText.textContent = data.treatment || top.treatment || '—';
    pesticideText.textContent = data.pesticide || top.pesticide || '—';

    // Switch to diagnosis tab
    tabBtns.forEach(b => b.classList.remove('active'));
    tabContents.forEach(tc => tc.classList.remove('active'));
    const diagTabBtn = document.querySelector('[data-tab="diagnosis"]');
    if (diagTabBtn) diagTabBtn.classList.add('active');
    const diagTab = document.getElementById('diagnosisTab');
    if (diagTab) diagTab.classList.add('active');
}

// ══════════════════════════════════════════════════
//  Vendor List Display
// ══════════════════════════════════════════════════

function showVendors(data) {
    if (!vendorList) return;
    const vendors = data.vendors || [];
    if (vendors.length === 0) return;

    vendorsEmpty.classList.add('hidden');
    vendorList.classList.remove('hidden');

    vendorList.innerHTML = vendors.map(v => `
        <div class="vendor-card">
            <div class="vendor-name">${escapeHtml(v.name)}</div>
            <div class="vendor-address">${escapeHtml(v.address || '')}</div>
            <div class="vendor-meta">
                ${v.distance_km ? `<span>📍 ${v.distance_km.toFixed(1)} km</span>` : ''}
                ${v.phone ? `<span>📞 ${escapeHtml(v.phone)}</span>` : ''}
                ${v.rating ? `<span>⭐ ${v.rating}</span>` : ''}
            </div>
        </div>
    `).join('');
}

// ══════════════════════════════════════════════════
//  Health Check
// ══════════════════════════════════════════════════

async function checkHealth() {
    try {
        const resp = await fetch(`${API_BASE}/health`, {
            headers: { 'X-API-Key': 'krishi-sarthi-api-key-change-this' },
        });
        if (resp.ok) {
            statusDot.classList.add('connected');
            statusDot.title = 'Backend connected';
        } else {
            statusDot.classList.remove('connected');
            statusDot.title = 'Backend offline';
        }
    } catch {
        statusDot.classList.remove('connected');
        statusDot.title = 'Backend offline';
    }
}

// ══════════════════════════════════════════════════
//  Utility Functions
// ══════════════════════════════════════════════════

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatBotMessage(text) {
    if (!text) return '<p>—</p>';
    // Convert markdown-like bold and newlines
    return text
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .split('\n')
        .filter(l => l.trim() !== '')
        .map(line => {
            if (line.trim().startsWith('- ') || line.trim().startsWith('• ')) {
                return `<li>${line.trim().slice(2)}</li>`;
            }
            return `<p>${line}</p>`;
        })
        .join('')
        .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
}

function getTimeAgo(isoString) {
    const now = Date.now();
    const then = new Date(isoString).getTime();
    const diff = Math.floor((now - then) / 1000);

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return new Date(isoString).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
}

// ══════════════════════════════════════════════════
//  Initialize
// ══════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    renderChatMessages();
    renderSessionList();
    checkHealth();
    setInterval(checkHealth, 15000);
});
