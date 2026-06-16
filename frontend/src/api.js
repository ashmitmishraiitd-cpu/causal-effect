const API_BASE = import.meta.env.VITE_API_URL || '';

export async function uploadCSV(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/upload-csv`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function runAnalysis(sessionId, treatment, outcome, confounders) {
  const form = new FormData();
  form.append('session_id', sessionId);
  form.append('treatment', treatment);
  form.append('outcome', outcome);
  form.append('confounders', confounders);
  const res = await fetch(`${API_BASE}/analyze`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Analysis failed');
  }
  return res.json();
}

export async function runCATE(sessionId, treatment, outcome, confounders, feature) {
  const form = new FormData();
  form.append('session_id', sessionId);
  form.append('treatment', treatment);
  form.append('outcome', outcome);
  form.append('confounders', confounders);
  form.append('feature', feature);
  const res = await fetch(`${API_BASE}/cate`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'CATE analysis failed');
  }
  return res.json();
}

export function getSampleDataUrl() {
  return `${API_BASE}/sample-data`;
}
