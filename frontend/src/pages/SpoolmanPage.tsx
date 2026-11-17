import React, { useState } from 'react';
import { Flame, Square, Plus } from 'lucide-react';
import { postApi } from '../api';
import type { AppState } from '../types';

interface Props {
  state: AppState;
  onToast: (msg: string, isError?: boolean) => void;
  onRefresh: () => void;
}

export const SpoolmanPage: React.FC<Props> = ({ state, onToast, onRefresh }) => {
  const [selectedPreset, setSelectedPreset] = useState(state.drying_presets[0]?.material || 'PLA / PLA+');
  const [newWeight, setNewWeight] = useState('1000');
  const [newLocation, setNewLocation] = useState(state.locations[0] || 'Regal');
  const [newFilamentId, setNewFilamentId] = useState(String(state.filaments[0]?.id || ''));

  const startDrying = async () => {
    const preset = state.drying_presets.find((p) => p.material === selectedPreset) || state.drying_presets[0];
    if (!preset) return;
    try {
      await postApi('/api/spoolman/drying/start', {
        material: preset.material,
        temp_c: preset.temp_c,
        hours: preset.hours,
      });
      onToast(`Trocknung gestartet: ${preset.material}`);
      onRefresh();
    } catch (e) {
      onToast(`Fehler: ${(e as Error).message}`, true);
    }
  };

  const stopDrying = async (id: string) => {
    try {
      await postApi('/api/spoolman/drying/stop', { id });
      onToast('Trocknung gestoppt');
      onRefresh();
    } catch (e) {
      onToast(`Fehler: ${(e as Error).message}`, true);
    }
  };

  const createSpool = async () => {
    try {
      await postApi('/api/spoolman/spool/create', {
        filament_id: Number(newFilamentId) || undefined,
        remaining_weight: Number(newWeight) || 1000,
        location: newLocation,
      });
      onToast('Spule angelegt');
      onRefresh();
    } catch (e) {
      onToast(`Fehler: ${(e as Error).message}`, true);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="card">
        <div className="card-header">
          <div className="card-title">Filament-Spulen ({state.spools.length})</div>
          <span
            className="status-pill"
            style={{
              background: state.spoolman_connected ? 'rgba(16,185,129,0.16)' : 'rgba(100,116,139,0.2)',
              color: state.spoolman_connected ? 'var(--success)' : 'var(--text-muted)',
            }}
          >
            {state.spoolman_connected ? 'Spoolman verbunden' : 'Demo / Offline'}
          </span>
        </div>

        <div className="cards-grid">
          {state.spools.map((sp) => {
            const color = sp.filament?.color_hex ? `#${sp.filament.color_hex.replace('#', '')}` : '#06b6d4';
            const rem = Math.round(sp.remaining_weight ?? 0);
            const init = Math.round(sp.initial_weight ?? 1000);
            const pct = Math.min(100, Math.max(0, Math.round((rem / Math.max(1, init)) * 100)));

            return (
              <div key={sp.id} className="stat-box" style={{ padding: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span
                    style={{
                      width: 14,
                      height: 14,
                      borderRadius: '50%',
                      background: color,
                      border: '1px solid rgba(255,255,255,0.25)',
                    }}
                  />
                  <strong>{sp.filament?.name || `Spule #${sp.id}`}</strong>
                  <span style={{ marginLeft: 'auto', fontSize: 11.5, color: 'var(--text-muted)' }}>
                    {sp.filament?.material || '—'}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>
                  {sp.filament?.vendor?.name || '—'} · {sp.location || 'Kein Ort'}
                </div>
                <div className="progress-track" style={{ marginBottom: 4 }}>
                  <div className="progress-fill" style={{ width: `${pct}%`, background: color }} />
                </div>
                <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
                  {rem} g / {init} g ({pct}%)
                </div>
              </div>
            );
          })}
        </div>

        {state.filaments.length > 0 && (
          <div className="form-grid" style={{ marginTop: 8, alignItems: 'end' }}>
            <div>
              <label className="field-label">Filament</label>
              <select className="select" value={newFilamentId} onChange={(e) => setNewFilamentId(e.target.value)}>
                {state.filaments.map((f, idx) => (
                  <option key={f.id || idx} value={f.id}>
                    {f.name || f.material}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label">Restgewicht (g)</label>
              <input className="input" type="number" value={newWeight} onChange={(e) => setNewWeight(e.target.value)} />
            </div>
            <div>
              <label className="field-label">Lagerort</label>
              <input className="input" value={newLocation} onChange={(e) => setNewLocation(e.target.value)} />
            </div>
            <button className="btn btn-primary" onClick={createSpool}>
              <Plus size={14} /> Spule anlegen
            </button>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">Filament-Trockner</div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <select
            className="select"
            style={{ maxWidth: 260 }}
            value={selectedPreset}
            onChange={(e) => setSelectedPreset(e.target.value)}
          >
            {state.drying_presets.map((p) => (
              <option key={p.material} value={p.material}>
                {p.material} ({p.temp_c}°C · {p.hours}h)
              </option>
            ))}
          </select>
          <button className="btn btn-primary" onClick={startDrying}>
            <Flame size={14} /> Trocknung starten
          </button>
        </div>

        {state.drying_timers.length > 0 && (
          <div className="btn-row">
            {state.drying_timers.map((t) => {
              const remMin = Math.max(0, Math.round((t.ends_at - Date.now() / 1000) / 60));
              return (
                <div key={t.id} className="stat-box" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div>
                    <strong>{t.material}</strong> ({t.temp_c}°C) · noch {remMin} min
                  </div>
                  <button className="btn btn-danger" onClick={() => stopDrying(t.id)}>
                    <Square size={12} /> Stop
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
