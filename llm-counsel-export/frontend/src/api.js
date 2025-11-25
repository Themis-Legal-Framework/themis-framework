/**
 * LLM-COUNSEL API Client
 */

const API_BASE = '/api';

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// ============================================================================
// Matter API
// ============================================================================

export async function listMatters() {
  return fetchAPI('/matters');
}

export async function createMatter(data = {}) {
  return fetchAPI('/matters', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getMatter(matterId) {
  return fetchAPI(`/matters/${matterId}`);
}

export async function updateMatter(matterId, data) {
  return fetchAPI(`/matters/${matterId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteMatter(matterId) {
  return fetchAPI(`/matters/${matterId}`, {
    method: 'DELETE',
  });
}

// ============================================================================
// Deliberation API
// ============================================================================

export async function submitQuestion(matterId, data) {
  return fetchAPI(`/matters/${matterId}/messages`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function* streamDeliberation(matterId, data) {
  const url = `${API_BASE}/matters/${matterId}/messages`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ...data, stream: true }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    let currentEvent = null;
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7);
      } else if (line.startsWith('data: ') && currentEvent) {
        try {
          const data = JSON.parse(line.slice(6));
          yield { type: currentEvent, data };
        } catch (e) {
          // Skip malformed JSON
        }
        currentEvent = null;
      }
    }
  }
}

// ============================================================================
// Quick Deliberation (no matter)
// ============================================================================

export async function quickDeliberate(data) {
  return fetchAPI('/deliberate', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function* streamQuickDeliberation(data) {
  const url = `${API_BASE}/deliberate`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ...data, stream: true }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    let currentEvent = null;
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7);
      } else if (line.startsWith('data: ') && currentEvent) {
        try {
          const data = JSON.parse(line.slice(6));
          yield { type: currentEvent, data };
        } catch (e) {
          // Skip malformed JSON
        }
        currentEvent = null;
      }
    }
  }
}

// ============================================================================
// Config API
// ============================================================================

export async function getTeamConfig() {
  return fetchAPI('/config/team');
}

export async function getPersonas() {
  return fetchAPI('/config/personas');
}

export async function getJurisdictions() {
  return fetchAPI('/config/jurisdictions');
}
