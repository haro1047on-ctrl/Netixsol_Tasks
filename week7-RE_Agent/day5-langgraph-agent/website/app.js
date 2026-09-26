// RealEstate Hub - Vapi AI Voice & Chat Assistant Frontend Integration

let API_KEY = "public_read_only_key";
let VAPI_PUBLIC_KEY = "9496558c-f290-42ee-8c13-caafb05e4052";
let ASSISTANT_ID = "31e5250a-6a50-47bf-89db-615fb6090422";
let BACKEND_PUBLIC_URL = window.location.origin;

let vapiInstance = null;
let isCallActive = false;
let isMuted = false;
let callTimerInterval = null;
let callStartTime = null;
let currentPropertyInquiry = null;

// DOM Element References
const grid = document.getElementById('properties-grid');
const countLabel = document.getElementById('results-count');
const searchBtn = document.getElementById('search-btn');
const resetFiltersBtn = document.getElementById('reset-filters-btn');
const vapiVoiceBtn = document.getElementById('vapi-voice-btn');

// Vapi Modal Elements
const vapiModal = document.getElementById('vapi-modal');
const closeVapiModalBtn = document.getElementById('close-vapi-modal');
const vapiStatusText = document.getElementById('vapi-status-text');
const vapiStatusBadge = document.getElementById('vapi-status-badge');
const vapiCallTimer = document.getElementById('vapi-call-timer');
const vapiTranscriptBox = document.getElementById('vapi-transcript-box');
const vapiMuteBtn = document.getElementById('vapi-mute-btn');
const vapiEndCallBtn = document.getElementById('vapi-end-call-btn');
const vapiMainOrb = document.getElementById('vapi-main-orb');
const orbWave1 = document.getElementById('orb-wave-1');
const orbWave2 = document.getElementById('orb-wave-2');
const orbWave3 = document.getElementById('orb-wave-3');
const vapiPropertyContext = document.getElementById('vapi-property-context');
const vapiContextText = document.getElementById('vapi-context-text');

// Chat Input Elements
const vapiChatInput = document.getElementById('vapi-chat-input');
const vapiSendMsgBtn = document.getElementById('vapi-send-msg-btn');

// Floating Pill Elements
const floatingVoiceBtn = document.getElementById('floating-voice-btn');
const floatingChatBtn = document.getElementById('floating-chat-btn');

// Property Detail Modal Elements
const propModal = document.getElementById('property-modal');
const closePropModalBtn = document.getElementById('close-prop-modal');
const propModalContent = document.getElementById('prop-modal-content');

// ==========================================
// Initial Configuration & Fetching
// ==========================================
async function loadConfig() {
    try {
        const res = await fetch('/api/config');
        if (res.ok) {
            const data = await res.json();
            if (data.vapi_public_key) VAPI_PUBLIC_KEY = data.vapi_public_key;
            if (data.vapi_assistant_id) ASSISTANT_ID = data.vapi_assistant_id;
            if (data.website_public_key) API_KEY = data.website_public_key;
            if (data.backend_public_url) BACKEND_PUBLIC_URL = data.backend_public_url;
        }
    } catch (err) {
        console.warn("Using default static config fallback:", err);
    }
}

// Fetch properties from backend
async function fetchProperties() {
    if (!grid) return;
    grid.innerHTML = '<div class="loader"></div>';
    
    const city = document.getElementById('filter-city').value;
    const type = document.getElementById('filter-type').value;
    const budget = document.getElementById('filter-budget').value;
    const bedrooms = document.getElementById('filter-bedrooms').value;
    
    let url = new URL('/api/properties', window.location.origin);
    if (city) url.searchParams.append('city', city);
    if (type) url.searchParams.append('type', type);
    if (budget) url.searchParams.append('budget', budget);
    if (bedrooms) url.searchParams.append('bedrooms', bedrooms);
    
    if (city || type || budget || bedrooms) {
        resetFiltersBtn.style.display = 'inline-block';
    } else {
        resetFiltersBtn.style.display = 'none';
    }

    try {
        const res = await fetch(url, { headers: { 'X-API-Key': API_KEY } });
        if (!res.ok) throw new Error('Failed to fetch properties');
        const data = await res.json();
        renderProperties(data.properties || []);
    } catch (err) {
        console.error("Fetch properties error:", err);
        grid.innerHTML = '<p style="color: #ff6b6b; grid-column: 1/-1; text-align: center; padding: 2rem;">Error loading property listings. Please make sure backend server is running.</p>';
    }
}

// Fetch statistics
async function fetchStats() {
    try {
        const res = await fetch('/api/stats', { headers: { 'X-API-Key': API_KEY } });
        const data = await res.json();
        if (data.success) {
            document.getElementById('stat-total').innerText = data.total_properties.toLocaleString();
            
            const lhr = data.by_city.find(c => c.city.toLowerCase() === 'lahore');
            document.getElementById('stat-lahore').innerText = lhr ? lhr.c.toLocaleString() : '0';
            
            const isb = data.by_city.find(c => c.city.toLowerCase() === 'islamabad');
            document.getElementById('stat-isb').innerText = isb ? isb.c.toLocaleString() : '0';
            
            document.querySelectorAll('.stat-value').forEach(el => el.classList.remove('shimmer'));
        }
    } catch (err) {
        console.error("Failed to fetch stats:", err);
    }
}

// Format price into PKR Crore / Lakh
function formatPrice(price) {
    if (!price) return 'PKR Price on Request';
    if (price >= 10000000) {
        return `PKR ${(price / 10000000).toFixed(2)} Crore`;
    } else if (price >= 100000) {
        return `PKR ${(price / 100000).toFixed(2)} Lakh`;
    }
    return `PKR ${price.toLocaleString()}`;
}

// Render property cards
function renderProperties(properties) {
    countLabel.innerText = `Showing ${properties.length} available properties`;
    
    if (properties.length === 0) {
        grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--text-secondary); padding: 3rem;">No properties matched your search criteria. Try clearing filters or searching another city.</p>';
        return;
    }
    
    grid.innerHTML = properties.map(p => `
        <div class="prop-card" onclick="openPropertyDetail('${p.id || p.property_id}')">
            <div class="prop-img-placeholder">
                <span style="opacity: 0.4; font-size: 3.5rem;">${p.property_type === 'Flat' ? '🏢' : p.property_type === 'Plot' ? '🏞️' : '🏠'}</span>
                <div class="prop-badge">${p.property_type || 'Residential'}</div>
            </div>
            <div class="prop-content">
                <div class="prop-price">${formatPrice(p.price)}</div>
                <h3 class="prop-title">${p.area_marla} Marla ${p.property_type} in ${p.locality || 'Prime Sector'}</h3>
                <div class="prop-location">📍 ${p.city || 'Pakistan'}</div>
                <div class="prop-features">
                    ${p.bedrooms ? `<div class="feature">🛏️ ${p.bedrooms} Beds</div>` : ''}
                    ${p.baths ? `<div class="feature">🚿 ${p.baths} Baths</div>` : ''}
                    <div class="feature">📐 ${p.area_marla} Marla</div>
                </div>
                <div class="prop-footer">
                    <div class="agent-info">
                        <div class="agent-avatar">${p.agent ? p.agent[0] : 'A'}</div>
                        <span>${p.agent || 'Official Agent'}</span>
                    </div>
                    <button class="glow-btn" style="padding: 0.4rem 1rem; font-size: 0.85rem;" 
                            onclick="event.stopPropagation(); startInquiryCall('${p.id || p.property_id}', '${p.area_marla} Marla ${p.property_type} in ${p.locality}, ${p.city}')">
                        Inquire
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// ==========================================
// Property Detail Modal
// ==========================================
window.openPropertyDetail = async function(propId) {
    propModal.style.display = 'flex';
    propModalContent.innerHTML = '<div class="loader"></div>';
    
    try {
        const res = await fetch(`/api/properties`, { headers: { 'X-API-Key': API_KEY } });
        const data = await res.json();
        const property = (data.properties || []).find(p => String(p.id || p.property_id) === String(propId));
        
        if (property) {
            const title = `${property.area_marla} Marla ${property.property_type} in ${property.locality}`;
            propModalContent.innerHTML = `
                <div style="text-align: center; margin-bottom: 1.5rem;">
                    <span style="font-size: 4rem;">${property.property_type === 'Flat' ? '🏢' : '🏠'}</span>
                    <h2 style="font-size: 1.8rem; margin-top: 0.5rem;">${title}</h2>
                    <p style="color: var(--text-secondary);">📍 ${property.locality}, ${property.city}</p>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 1.2rem; border-radius: 16px; margin-bottom: 1.5rem;">
                    <div style="font-size: 2rem; font-weight: 700; color: var(--accent-primary); margin-bottom: 1rem;">${formatPrice(property.price)}</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; font-size: 0.95rem;">
                        <div>📐 <strong>Area:</strong> ${property.area_marla} Marla</div>
                        <div>🏠 <strong>Type:</strong> ${property.property_type}</div>
                        ${property.bedrooms ? `<div>🛏️ <strong>Bedrooms:</strong> ${property.bedrooms}</div>` : ''}
                        ${property.baths ? `<div>🚿 <strong>Bathrooms:</strong> ${property.baths}</div>` : ''}
                    </div>
                </div>
                <div style="display: flex; gap: 1rem;">
                    <button class="glow-btn full-width" style="padding: 0.8rem;" onclick="closePropModal(); startInquiryCall('${property.id || property.property_id}', '${title}')">
                        🎙️ Speak to AI Agent About This Property
                    </button>
                </div>
            `;
        } else {
            propModalContent.innerHTML = '<p>Property details not found.</p>';
        }
    } catch (err) {
        propModalContent.innerHTML = '<p style="color: #ff6b6b;">Error loading details.</p>';
    }
};

window.closePropModal = function() {
    propModal.style.display = 'none';
};
if (closePropModalBtn) closePropModalBtn.addEventListener('click', closePropModal);

// ==========================================
// Tab Navigation Interactivity
// ==========================================
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const tab = link.getAttribute('data-tab');
        
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        
        document.querySelectorAll('.tab-section').forEach(s => s.classList.remove('active'));
        const targetSection = document.getElementById(`section-${tab}`);
        if (targetSection) targetSection.classList.add('active');
    });
});

document.getElementById('nav-logo').addEventListener('click', () => {
    document.querySelector('.nav-link[data-tab="discover"]').click();
});

// Quick Filters
document.querySelectorAll('.quick-tag-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const city = btn.getAttribute('data-city') || '';
        const type = btn.getAttribute('data-type') || '';
        const budget = btn.getAttribute('data-budget') || '';
        
        document.getElementById('filter-city').value = city;
        document.getElementById('filter-type').value = type;
        document.getElementById('filter-budget').value = budget;
        
        fetchProperties();
    });
});

if (resetFiltersBtn) {
    resetFiltersBtn.addEventListener('click', () => {
        document.getElementById('filter-city').value = '';
        document.getElementById('filter-type').value = '';
        document.getElementById('filter-budget').value = '';
        document.getElementById('filter-bedrooms').value = '';
        fetchProperties();
    });
}

window.filterBySociety = function(societyName) {
    document.querySelector('.nav-link[data-tab="discover"]').click();
    document.getElementById('filter-city').value = societyName === 'DHA' || societyName === 'Gulberg' ? 'Lahore' : 'Islamabad';
    fetchProperties();
};

if (searchBtn) searchBtn.addEventListener('click', fetchProperties);

// ==========================================
// PURE VAPI AGENT INTEGRATION
// ==========================================

function setupVapiEventListeners(instance) {
    if (!instance || typeof instance.on !== 'function') return;

    instance.on('call-start', () => {
        console.log("Vapi Assistant Connected Directly");
        isCallActive = true;
        updateCallStatus("Live Voice Call", "pulsing");
        startTimer();
        addTranscriptMessage("system", "Connected to Vapi Assistant.");
    });

    instance.on('call-end', () => {
        console.log("Vapi Assistant Disconnected");
        isCallActive = false;
        updateCallStatus("Session Ended", "");
        stopTimer();
        resetOrbAnimation();
        addTranscriptMessage("system", "Session ended.");
    });

    instance.on('speech-start', () => {
        updateCallStatus("Agent Speaking...", "pulsing");
        if (vapiMainOrb) vapiMainOrb.style.transform = 'scale(1.25)';
    });

    instance.on('speech-end', () => {
        updateCallStatus("Listening...", "pulsing");
        if (vapiMainOrb) vapiMainOrb.style.transform = 'scale(1)';
        resetOrbAnimation();
    });

    instance.on('volume-level', (volume) => {
        const scale = 1 + (volume * 0.6);
        if (orbWave1) orbWave1.style.transform = `scale(${scale * 1.1})`;
        if (orbWave2) orbWave2.style.transform = `scale(${scale * 1.35})`;
        if (orbWave3) orbWave3.style.transform = `scale(${scale * 1.6})`;
    });

    instance.on('message', (message) => {
        console.log("Vapi Event Message:", message);
        if (message.type === 'transcript') {
            if (message.transcriptType === 'final') {
                const role = message.role === 'user' ? 'user' : 'agent';
                addTranscriptMessage(role, message.transcript);
            }
        }
    });

    instance.on('error', (e) => {
        console.error("Vapi Error Event:", e);
        const errMsg = e.error ? (e.error.message || JSON.stringify(e.error)) : (e.message || JSON.stringify(e));
        addTranscriptMessage("system", "Vapi Notice: " + errMsg);
    });
}

function openVapiModal(propertyContext = null) {
    vapiModal.style.display = 'flex';
    vapiTranscriptBox.innerHTML = '';
    
    if (propertyContext) {
        currentPropertyInquiry = propertyContext;
        vapiContextText.innerText = `Inquiring about: ${propertyContext.title}`;
        vapiPropertyContext.style.display = 'flex';
    } else {
        currentPropertyInquiry = null;
        vapiPropertyContext.style.display = 'none';
    }

    if (vapiChatInput) {
        vapiChatInput.focus();
    }
}

function closeVapiModal() {
    if (isCallActive) {
        endCall();
    }
    vapiModal.style.display = 'none';
}

if (closeVapiModalBtn) closeVapiModalBtn.addEventListener('click', closeVapiModal);

window.startInquiryCall = function(propId, title) {
    openVapiModal({ id: propId, title: title });
    startCall({ property_id: propId, title: title });
};

document.querySelectorAll('.call-agent-trigger').forEach(btn => {
    btn.addEventListener('click', () => {
        openVapiModal();
        startCall();
    });
});

document.querySelectorAll('.text-chat-trigger').forEach(btn => {
    btn.addEventListener('click', () => {
        openVapiModal();
        startCall();
    });
});

if (vapiVoiceBtn) {
    vapiVoiceBtn.addEventListener('click', () => {
        openVapiModal();
        startCall();
    });
}

if (floatingVoiceBtn) {
    floatingVoiceBtn.addEventListener('click', () => {
        openVapiModal();
        startCall();
    });
}

if (floatingChatBtn) {
    floatingChatBtn.addEventListener('click', () => {
        openVapiModal();
        startCall();
    });
}

// Send Text Message directly through Vapi Web SDK session
function sendUserTextMessage() {
    const text = vapiChatInput.value.trim();
    if (!text) return;
    
    vapiChatInput.value = '';
    addTranscriptMessage("user", text);
    
    if (vapiInstance && typeof vapiInstance.send === 'function') {
        try {
            vapiInstance.send({
                type: 'add-message',
                message: { role: 'user', content: text }
            });
        } catch (e) {
            console.warn("vapiInstance.send error:", e);
        }
    }
}

if (vapiSendMsgBtn) vapiSendMsgBtn.addEventListener('click', sendUserTextMessage);
if (vapiChatInput) {
    vapiChatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendUserTextMessage();
    });
}

async function startCall(variableValues = {}) {
    updateCallStatus("Connecting to Vapi...", "pulsing");
    
    // Request microphone access for Vapi WebRTC
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
            await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch (micErr) {
            console.warn("Microphone permission notice:", micErr);
        }
    }
    
    const VapiClass = window.Vapi || (window.exports && window.exports.Vapi) || (window.vapiSDK && window.vapiSDK.Vapi);
    if (typeof VapiClass === 'function') {
        try {
            console.log("Starting call with Vapi Assistant ID:", ASSISTANT_ID);
            vapiInstance = new VapiClass(VAPI_PUBLIC_KEY);
            setupVapiEventListeners(vapiInstance);
            await vapiInstance.start(ASSISTANT_ID, { variableValues: variableValues });
            return;
        } catch (err) {
            console.error("Vapi start call error:", err);
            updateCallStatus("Connection Error", "");
            addTranscriptMessage("system", "Error starting Vapi call: " + (err.message || err));
            return;
        }
    }

    if (window.vapiSDK && typeof window.vapiSDK.run === 'function') {
        try {
            console.log("Starting call with vapiSDK.run using Assistant ID:", ASSISTANT_ID);
            vapiInstance = window.vapiSDK.run({
                apiKey: VAPI_PUBLIC_KEY,
                assistant: ASSISTANT_ID,
                assistantOverrides: { variableValues: variableValues }
            });
            setupVapiEventListeners(vapiInstance);
            return;
        } catch (err) {
            console.error("vapiSDK run error:", err);
        }
    }
    
    updateCallStatus("SDK Load Error", "");
    addTranscriptMessage("system", "Vapi Web SDK is not loaded. Please check your network or refresh the page.");
}

function endCall() {
    isCallActive = false;
    stopTimer();
    resetOrbAnimation();
    updateCallStatus("Call Ended", "");
    
    if (vapiInstance) {
        try {
            if (typeof vapiInstance.stop === 'function') vapiInstance.stop();
        } catch (e) {
            console.error("Error stopping Vapi call:", e);
        }
    }
}

if (vapiEndCallBtn) vapiEndCallBtn.addEventListener('click', endCall);

if (vapiMuteBtn) {
    vapiMuteBtn.addEventListener('click', () => {
        isMuted = !isMuted;
        if (vapiInstance && typeof vapiInstance.setMuted === 'function') {
            try { vapiInstance.setMuted(isMuted); } catch (e) {}
        }
        vapiMuteBtn.classList.toggle('active-mute', isMuted);
        document.getElementById('mute-icon').innerText = isMuted ? '🔇' : '🎤';
    });
}

// Helper Functions
function updateCallStatus(text, dotClass = "") {
    if (vapiStatusText) vapiStatusText.innerText = text;
    if (vapiStatusBadge) {
        const dot = vapiStatusBadge.querySelector('.status-dot');
        if (dot) dot.className = `status-dot ${dotClass}`;
    }
}

function startTimer() {
    stopTimer();
    callStartTime = Date.now();
    if (vapiCallTimer) vapiCallTimer.innerText = "00:00";
    callTimerInterval = setInterval(() => {
        const elapsedSec = Math.floor((Date.now() - callStartTime) / 1000);
        const mins = String(Math.floor(elapsedSec / 60)).padStart(2, '0');
        const secs = String(elapsedSec % 60).padStart(2, '0');
        if (vapiCallTimer) vapiCallTimer.innerText = `${mins}:${secs}`;
    }, 1000);
}

function stopTimer() {
    if (callTimerInterval) clearInterval(callTimerInterval);
}

function resetOrbAnimation() {
    if (orbWave1) orbWave1.style.transform = 'scale(1)';
    if (orbWave2) orbWave2.style.transform = 'scale(1)';
    if (orbWave3) orbWave3.style.transform = 'scale(1)';
    if (vapiMainOrb) vapiMainOrb.style.transform = 'scale(1)';
}

function addTranscriptMessage(role, text) {
    if (!vapiTranscriptBox) return;
    
    const msgDiv = document.createElement('div');
    msgDiv.className = `transcript-msg ${role === 'user' ? 'user-msg' : role === 'system' ? 'system-msg' : 'agent-msg'}`;
    
    if (role === 'system') {
        msgDiv.style.justifyContent = 'center';
        msgDiv.innerHTML = `<span style="font-size:0.75rem; opacity:0.6; background:rgba(255,255,255,0.05); padding:0.2rem 0.6rem; border-radius:10px;">${text}</span>`;
    } else {
        const avatar = role === 'user' ? '👤' : '🤖';
        msgDiv.innerHTML = `
            <div class="msg-avatar">${avatar}</div>
            <div class="msg-bubble">${text}</div>
        `;
    }
    
    vapiTranscriptBox.appendChild(msgDiv);
    vapiTranscriptBox.scrollTop = vapiTranscriptBox.scrollHeight;
}

// Initial Page Load
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    fetchStats();
    fetchProperties();
});
