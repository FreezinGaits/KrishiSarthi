/**
 * Krishi-Sarthi — Hackathon Demo Frontend Controller
 *
 * Handles: chat messaging, image upload + diagnosis, voice recording,
 * location sharing, side panel tabs, and backend API communication.
 */

(() => {
    "use strict";

    // ── Config ──────────────────────────────────
    const API_BASE = "http://localhost:8000";
    const API_KEY = "krishi-sarthi-dev-key-2024";
    const HEADERS = {
        "X-API-Key": API_KEY,
    };

    // ── State ───────────────────────────────────
    let sessionId = crypto.randomUUID?.() || Date.now().toString(36);
    let userLocation = { lat: null, lng: null };
    let pendingImage = null; // { file, base64, dataUrl }
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;

    // ── DOM refs ────────────────────────────────
    const $ = (sel) => document.querySelector(sel);
    const chatMessages = $("#chatMessages");
    const chatInput = $("#chatInput");
    const sendBtn = $("#sendBtn");
    const micBtn = $("#micBtn");
    const imageBtn = $("#imageBtn");
    const imageInput = $("#imageInput");
    const locationBtn = $("#locationBtn");
    const recordingIndicator = $("#recordingIndicator");
    const statusDot = $("#statusDot");

    // Side panel
    const diagnosisCard = $("#diagnosisCard");
    const diagnosisEmpty = $("#diagnosisEmpty");
    const vendorList = $("#vendorList");
    const vendorsEmpty = $("#vendorsEmpty");

    // Modal
    const imageModal = $("#imageModal");
    const imagePreview = $("#imagePreview");
    const modalClose = $("#modalClose");
    const modalCancel = $("#modalCancel");
    const modalSend = $("#modalSend");

    // ─────────────────────────────────────────────
    // Utility
    // ─────────────────────────────────────────────
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function formatMarkdown(text) {
        // Very basic markdown → HTML (bold, bullets, newlines)
        return text
            .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.+?)\*/g, "<em>$1</em>")
            .replace(/^• /gm, "• ")
            .replace(/---/g, "<hr>")
            .replace(/\n/g, "<br>");
    }

    function addMessage(content, type = "bot", extras = {}) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${type}-message`;

        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.textContent = type === "bot" ? "🌿" : "👨‍🌾";

        const contentDiv = document.createElement("div");
        contentDiv.className = "message-content";

        if (extras.imageUrl) {
            contentDiv.innerHTML = `<img src="${extras.imageUrl}" class="chat-image" alt="Uploaded crop image"><br>`;
        }

        contentDiv.innerHTML += formatMarkdown(content);

        msgDiv.appendChild(avatar);
        msgDiv.appendChild(contentDiv);
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
        return msgDiv;
    }

    function addTypingIndicator() {
        const msgDiv = document.createElement("div");
        msgDiv.className = "message bot-message";
        msgDiv.id = "typingIndicator";
        msgDiv.innerHTML = `
            <div class="message-avatar">🌿</div>
            <div class="message-content typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>`;
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const el = document.getElementById("typingIndicator");
        if (el) el.remove();
    }

    // ─────────────────────────────────────────────
    // API Calls
    // ─────────────────────────────────────────────
    async function apiCall(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const fetchOptions = {
            ...options,
            headers: {
                ...HEADERS,
                ...(options.headers || {}),
            },
        };

        const resp = await fetch(url, fetchOptions);
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        return resp.json();
    }

    async function checkBackendHealth() {
        try {
            const data = await apiCall("/health");
            statusDot.classList.add("connected");
            statusDot.title = "Backend connected";
            if (data.demo_mode) {
                $("#demoBadge").style.display = "inline-block";
            } else {
                $("#demoBadge").style.display = "none";
            }
        } catch {
            statusDot.classList.remove("connected");
            statusDot.title = "Backend offline";
        }
    }

    // ─────────────────────────────────────────────
    // Chat
    // ─────────────────────────────────────────────
    async function sendChatMessage(text, imageBase64 = null) {
        if (!text.trim() && !imageBase64) return;

        // Show user message
        const extras = {};
        if (pendingImage) {
            extras.imageUrl = pendingImage.dataUrl;
        }
        addMessage(text || "📷 Crop image sent for diagnosis", "user", extras);
        chatInput.value = "";

        // Build request body
        const body = {
            message: text || "Please diagnose this crop image",
            session_id: sessionId,
        };
        if (imageBase64) body.image_base64 = imageBase64;
        if (userLocation.lat) {
            body.latitude = userLocation.lat;
            body.longitude = userLocation.lng;
        }

        addTypingIndicator();

        try {
            const data = await apiCall("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });

            removeTypingIndicator();

            // Show agent reply
            addMessage(data.reply || "No response received.");

            // Update session
            if (data.session_id) sessionId = data.session_id;

            // Update diagnosis panel
            if (data.diagnosis) {
                showDiagnosis(data.diagnosis);
            }

            // Update vendors panel
            if (data.vendors && data.vendors.vendors && data.vendors.vendors.length > 0) {
                showVendors(data.vendors.vendors);
            }

        } catch (err) {
            removeTypingIndicator();
            addMessage(`❌ Error: ${err.message}. Is the backend running?`);
        }

        pendingImage = null;
    }

    // ─────────────────────────────────────────────
    // Image Upload + Diagnosis
    // ─────────────────────────────────────────────
    function handleImageSelect(file) {
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            const dataUrl = e.target.result;
            const base64 = dataUrl.split(",")[1];

            pendingImage = { file, base64, dataUrl };

            // Show modal preview
            imagePreview.src = dataUrl;
            imageModal.classList.remove("hidden");
        };
        reader.readAsDataURL(file);
    }

    async function sendDiagnosisDirectly(file) {
        addMessage("📷 Analyzing crop image...", "user", { imageUrl: pendingImage?.dataUrl });
        addTypingIndicator();

        try {
            const formData = new FormData();
            formData.append("image", file);

            const data = await apiCall("/api/diagnose-image", {
                method: "POST",
                body: formData,
            });

            removeTypingIndicator();

            // Show diagnosis in chat
            const msg = `🔬 **Diagnosis Result:**\n` +
                `• **Disease:** ${data.top_disease}\n` +
                `• **Confidence:** ${(data.top_confidence * 100).toFixed(0)}%\n\n` +
                `**Treatment:** ${data.treatment}\n\n` +
                `**Pesticide:** ${data.pesticide}`;
            addMessage(msg);

            showDiagnosis(data);

        } catch (err) {
            removeTypingIndicator();
            addMessage(`❌ Diagnosis failed: ${err.message}`);
        }
    }

    function showDiagnosis(data) {
        diagnosisEmpty.classList.add("hidden");
        diagnosisCard.classList.remove("hidden");

        $("#diseaseName").textContent = data.top_disease || "Unknown";
        const conf = (data.top_confidence * 100).toFixed(0);
        const badge = $("#confidenceBadge");
        badge.textContent = `${conf}%`;
        badge.className = "confidence-badge" + (data.top_confidence < 0.5 ? " low" : "");

        $("#treatmentText").textContent = data.treatment || "—";
        $("#pesticideText").textContent = data.pesticide || "—";

        if (pendingImage?.dataUrl) {
            const preview = $("#diagnosisPreview");
            preview.innerHTML = `<img src="${pendingImage.dataUrl}" alt="Diagnosed crop">`;
        }

        // Switch to diagnosis tab
        switchTab("diagnosis");
    }

    // ─────────────────────────────────────────────
    // Voice Recording
    // ─────────────────────────────────────────────
    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
            audioChunks = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) audioChunks.push(e.data);
            };

            mediaRecorder.onstop = async () => {
                stream.getTracks().forEach((t) => t.stop());
                const blob = new Blob(audioChunks, { type: "audio/webm" });
                await sendAudioForTranscription(blob);
            };

            mediaRecorder.start();
            isRecording = true;
            micBtn.classList.add("recording");
            recordingIndicator.classList.add("visible");
        } catch (err) {
            addMessage(`❌ Microphone access denied: ${err.message}`);
        }
    }

    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            micBtn.classList.remove("recording");
            recordingIndicator.classList.remove("visible");
        }
    }

    async function sendAudioForTranscription(blob) {
        addMessage("🎙️ Voice message sent...", "user");
        addTypingIndicator();

        try {
            const formData = new FormData();
            formData.append("audio", blob, "recording.webm");

            const data = await apiCall("/api/speech-to-text", {
                method: "POST",
                body: formData,
            });

            removeTypingIndicator();

            const transcript = data.transcript || data.text || "";
            addMessage(`🎤 **You said:** "${transcript}"`);

            // Now send transcript to chat agent
            if (transcript) {
                await sendChatMessage(transcript);
            }
        } catch (err) {
            removeTypingIndicator();
            addMessage(`❌ Transcription failed: ${err.message}`);
        }
    }

    // ─────────────────────────────────────────────
    // Location
    // ─────────────────────────────────────────────
    function requestLocation() {
        if (!navigator.geolocation) {
            addMessage("❌ Geolocation not supported in this browser.");
            return;
        }

        locationBtn.classList.add("active");
        locationBtn.textContent = "⏳ Locating...";

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                userLocation.lat = pos.coords.latitude;
                userLocation.lng = pos.coords.longitude;
                locationBtn.textContent = "📍 Located ✓";
                locationBtn.classList.add("active");
                addMessage(`📍 Location shared: ${userLocation.lat.toFixed(4)}, ${userLocation.lng.toFixed(4)}`);

                // Auto-search vendors
                searchVendors();
            },
            (err) => {
                locationBtn.textContent = "📍 Location";
                locationBtn.classList.remove("active");
                // Use default Ludhiana location
                userLocation.lat = 30.9;
                userLocation.lng = 75.85;
                addMessage("⚠️ Location access denied. Using default location (Ludhiana, Punjab).");
                searchVendors();
            }
        );
    }

    async function searchVendors() {
        addTypingIndicator();
        try {
            const data = await apiCall("/api/find-vendors", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    latitude: userLocation.lat || 30.9,
                    longitude: userLocation.lng || 75.85,
                    query: "pesticide agricultural supply",
                    radius_km: 10,
                }),
            });

            removeTypingIndicator();

            if (data.vendors && data.vendors.length > 0) {
                showVendors(data.vendors);
                const vendorMsg = data.vendors.slice(0, 3).map((v, i) =>
                    `${i + 1}. **${v.name}** — ${v.distance_km} km\n   📞 ${v.phone || "N/A"}`
                ).join("\n");
                addMessage(`📍 **Nearby Shops Found:**\n${vendorMsg}`);
            } else {
                addMessage("📍 No vendors found nearby. Try expanding the search radius.");
            }

        } catch (err) {
            removeTypingIndicator();
            addMessage(`❌ Vendor search failed: ${err.message}`);
        }
    }

    function showVendors(vendors) {
        vendorsEmpty.classList.add("hidden");
        vendorList.classList.remove("hidden");
        vendorList.innerHTML = "";

        vendors.forEach((v) => {
            const card = document.createElement("div");
            card.className = "vendor-card";
            card.innerHTML = `
                <div class="vendor-name">${v.name}</div>
                <div class="vendor-detail">${v.address || "Address not available"}</div>
                ${v.phone ? `<div class="vendor-detail">📞 ${v.phone}</div>` : ""}
                ${v.rating ? `<div class="vendor-detail">⭐ ${v.rating}</div>` : ""}
                <span class="vendor-distance">📍 ${v.distance_km} km</span>`;
            vendorList.appendChild(card);
        });

        switchTab("vendors");
    }

    // ─────────────────────────────────────────────
    // Tabs
    // ─────────────────────────────────────────────
    function switchTab(tabName) {
        document.querySelectorAll(".tab-btn").forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.tab === tabName);
        });
        document.querySelectorAll(".tab-content").forEach((tc) => {
            tc.classList.remove("active");
        });
        $(`#${tabName}Tab`).classList.add("active");
    }

    // ─────────────────────────────────────────────
    // Event Listeners
    // ─────────────────────────────────────────────
    // Send message
    sendBtn.addEventListener("click", () => {
        const text = chatInput.value.trim();
        const img = pendingImage?.base64 || null;
        sendChatMessage(text, img);
    });

    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendBtn.click();
        }
    });

    // Image upload
    imageBtn.addEventListener("click", () => imageInput.click());
    imageInput.addEventListener("change", () => {
        if (imageInput.files[0]) handleImageSelect(imageInput.files[0]);
        imageInput.value = "";
    });

    // Modal
    modalClose.addEventListener("click", () => imageModal.classList.add("hidden"));
    modalCancel.addEventListener("click", () => {
        imageModal.classList.add("hidden");
        pendingImage = null;
    });
    modalSend.addEventListener("click", () => {
        imageModal.classList.add("hidden");
        if (pendingImage) {
            sendChatMessage(chatInput.value.trim() || "", pendingImage.base64);
        }
    });

    // Voice
    micBtn.addEventListener("click", () => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    });

    // Location
    locationBtn.addEventListener("click", requestLocation);

    // Tabs
    document.querySelectorAll(".tab-btn").forEach((btn) => {
        btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });

    // ─────────────────────────────────────────────
    // Init
    // ─────────────────────────────────────────────
    checkBackendHealth();
    setInterval(checkBackendHealth, 15000);
    chatInput.focus();

})();
