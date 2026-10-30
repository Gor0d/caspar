export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const form = body instanceof FormData;
  const response = await fetch('/api' + path, {
    method,
    headers: { 'X-Caspar-Local': '1', ...(!form && body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
    body: body === undefined ? undefined : form ? body : JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data.detail === 'string' ? data.detail : Array.isArray(data.detail) ? data.detail.map((e: {msg: string}) => e.msg).join('; ') : `Falha na operação (${response.status}).`);
  }
  return response.status === 204 ? undefined as T : response.json();
}
export async function download(path: string, filename: string, method = 'GET') {
  const response = await fetch('/api' + path, { method, headers: { 'X-Caspar-Local': '1' } });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Não foi possível exportar.');
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
