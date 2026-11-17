import type { AppState, PrinterDetails } from './types';

export async function getApi<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function postApi<T = Record<string, unknown>>(
  url: string,
  body: Record<string, unknown> = {}
): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function fetchState(): Promise<AppState> {
  return getApi<AppState>('/api/state');
}

export function fetchPrinterDetails(printerId: string): Promise<PrinterDetails> {
  return getApi<PrinterDetails>(`/api/printer/details?printer_id=${encodeURIComponent(printerId)}`);
}
