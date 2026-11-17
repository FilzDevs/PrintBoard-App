export const STATE_LABELS: Record<string, string> = {
  printing: 'Druck läuft',
  paused: 'Pausiert',
  complete: 'Fertig',
  error: 'Fehler',
  cancelled: 'Abgebrochen',
  standby: 'Bereit',
  offline: 'Offline',
};

export const STATE_COLORS: Record<string, string> = {
  printing: '#06b6d4',
  paused: '#f59e0b',
  complete: '#10b981',
  error: '#f43f5e',
  cancelled: '#fb923c',
  standby: '#10b981',
  offline: '#64748b',
};

export function formatDuration(seconds?: number): string {
  if (!seconds || seconds <= 0) return '—';
  const s = Math.floor(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const rem = s % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${rem}s`;
  return `${rem}s`;
}

export function formatTemp(val?: number, target?: number): string {
  if (val === undefined || val === null) return '—';
  const cur = val.toFixed(1);
  if (target && target > 0) {
    return `${cur}° / ${target.toFixed(0)}°C`;
  }
  return `${cur}°C`;
}

export function formatBytes(bytes?: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
