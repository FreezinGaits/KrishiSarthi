const API_BASE = '/api';

async function request(url, options = {}) {
  const headers = { 'X-API-Key': 'krishi-sarthi-api-key-change-this', ...options.headers };
  try {
    const res = await fetch(`${API_BASE}${url}`, { ...options, headers });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(err || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    console.error(`API error [${url}]:`, e);
    throw e;
  }
}

export async function speechToText(audioBlob) {
  const form = new FormData();
  form.append('audio', audioBlob, 'recording.webm');
  return request('/speech-to-text', {
    method: 'POST',
    body: form,
  });
}

export async function diagnoseImage(imageFile) {
  const form = new FormData();
  form.append('image', imageFile);
  return request('/diagnose-image', {
    method: 'POST',
    body: form,
  });
}

export async function chatWithAgent(message, sessionId = '', imageBase64 = null, lat = null, lng = null, language = 'hi', options = {}) {
  return request('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      image_base64: imageBase64,
      latitude: lat,
      longitude: lng,
      language,
      options, // extra options (e.g., { answer_length: 'short' })
    }),
  });
}


export async function findVendors(lat, lng, query = 'pesticide shop', radiusKm = 50, disease = null) {
  const body = {
    latitude: lat,
    longitude: lng,
    query,
    radius_km: radiusKm,
  }
  if (disease) body.disease = disease

  return request('/find-vendors', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function deleteSession(sessionId) {
  return request(`/sessions/${sessionId}`, { method: 'DELETE' });
}

export async function getHealth() {
  return request('/health');
}

// ══════════════════════════════════════════════════
//  Marketplace API
// ══════════════════════════════════════════════════

const MARKET_BASE = '/marketplace';

async function marketRequest(url, options = {}) {
  const headers = { ...options.headers };
  try {
    const res = await fetch(`${MARKET_BASE}${url}`, { ...options, headers });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(err || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    console.error(`Marketplace API error [${url}]:`, e);
    throw e;
  }
}

export async function startConversation(farmerId, vendorId) {
  return marketRequest('/chat/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ farmer_id: farmerId, vendor_id: vendorId }),
  });
}

export async function sendMarketMessage(conversationId, senderId, message) {
  return marketRequest('/chat/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation_id: conversationId, sender_id: senderId, message }),
  });
}

export async function getConversationMessages(conversationId) {
  return marketRequest(`/chat/${conversationId}`);
}

export async function createMedicineRequest(farmerId, vendorId, diseaseName, medicineName) {
  return marketRequest('/medicine/request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      farmer_id: farmerId,
      vendor_id: vendorId,
      disease_name: diseaseName,
      medicine_name: medicineName,
    }),
  });
}

export async function respondToMedicineRequest(requestId, status) {
  return marketRequest('/medicine/respond', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request_id: requestId, status }),
  });
}
