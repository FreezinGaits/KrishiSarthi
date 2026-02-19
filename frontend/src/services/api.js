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


export async function findVendors(lat, lng, query = 'pesticide shop', radiusKm = 10) {
  return request('/find-vendors', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      latitude: lat,
      longitude: lng,
      query,
      radius_km: radiusKm,
    }),
  });
}

export async function getHealth() {
  return request('/health');
}
