import React, { useState } from 'react';
import { Pause, Play, Square, SlidersHorizontal, Plus, Thermometer, Layers } from 'lucide-react';
import { postApi } from '../api';
import type { AppState, Printer } from '../types';
import { formatDuration, formatTemp, STATE_COLORS, STATE_LABELS } from '../utils';
import { TempChart } from '../components/TempChart';
import { PrinterModal } from '../components/PrinterModal';
import { AddPrinterModal } from '../components/AddPrinterModal';

interface Props {
  state: AppState;
  onToast: (msg: string, isError?: boolean) => void;
  onRefresh: () => void;
}

const ProgressRing: React.FC<{ pct: number; color: string }> = ({ pct, color }) => {
  const r = 27;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  return (
    <div className="ring-wrap">
      <svg width="68" height="68" viewBox="0 0 68 68" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="34" cy="34" r={r} fill="none" stroke="rgba(148,163,184,0.16)" strokeWidth="5.5" />
        <circle
          cx="34"
          cy="34"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="5.5"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.4s ease' }}
        />
      </svg>
      <span className="ring-text tabular">{pct}%</span>
    </div>
  );
};

export const FleetPage: React.FC<Props> = ({ state, onToast, onRefresh }) => {
  const [selected, setSelected] = useState<Printer | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  const printers = state.printers || [];
  const printingCount = printers.filter((p) => state.statuses[p.id]?.state === 'printing').length;
  const readyCount = printers.filter((p) =>
    ['standby', 'complete'].includes(state.statuses[p.id]?.state || '')
  ).length;
  const offlineCount = printers.filter(
    (p) => (state.statuses[p.id]?.state || 'offline') === 'offline'
  ).length;

  const sendAction = async (printerId: string, action: string) => {
    try {
      await postApi('/api/control', { printer_id: printerId, action });
      onToast(`Aktion "${action}" ausgeführt`);
      onRefresh();
    } catch (e) {
      onToast(`Fehler: ${(e as Error).message}`, true);
    }
  };

  return (
    <>
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">Drucker gesamt</div>
          <div className="kpi-value tabular">{printers.length}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Aktiv am Drucken</div>
          <div className="kpi-value tabular" style={{ color: 'var(--accent)' }}>
            {printingCount}
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Bereit</div>
          <div className="kpi-value tabular" style={{ color: 'var(--success)' }}>
            {readyCount}
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Offline</div>
          <div className="kpi-value tabular" style={{ color: 'var(--text-muted)' }}>
            {offlineCount}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          {state.sim_enabled ? 'Demo-Flotte aktiv' : 'Live-Flotte'}
        </div>
        <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
          <Plus size={15} /> Drucker hinzufügen
        </button>
      </div>

      <div className="cards-grid">
        {printers.map((p) => {
          const st = state.statuses[p.id] || { state: 'offline' };
          const stKey = st.state || 'offline';
          const color = STATE_COLORS[stKey] || '#64748b';
          const pct = Math.min(100, Math.max(0, Math.round((st.progress || 0) * 100)));

          return (
            <div key={p.id} className="card">
              <div className="card-header">
                <div>
                  <div className="card-title">{p.name}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
                    {p.is_sim ? 'Simulation' : p.printer_type || 'Moonraker'}
                  </div>
                </div>
                <span className="status-pill" style={{ background: `${color}22`, color }}>
                  <span
                    className={`status-dot ${stKey === 'printing' ? 'pulse' : ''}`}
                    style={{ background: color }}
                  />
                  {STATE_LABELS[stKey] || stKey}
                </span>
              </div>

              <div className="printer-hero">
                <ProgressRing pct={pct} color={color} />
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 700,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      marginBottom: 4,
                    }}
                  >
                    {st.filename || 'Kein aktiver Druckjob'}
                  </div>
                  <div className="tabular" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    Restzeit: {formatDuration(st.eta_seconds)} · Laufzeit: {formatDuration(st.print_duration)}
                  </div>
                  {st.total_layers ? (
                    <div
                      className="tabular"
                      style={{ fontSize: 11.5, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 5, marginTop: 3 }}
                    >
                      <Layers size={12} /> Layer {st.current_layer ?? 0} / {st.total_layers}
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="stats-row">
                <div className="stat-box">
                  <div className="stat-box-label">
                    <Thermometer size={12} color="#f97316" /> Düse
                  </div>
                  <div className="stat-box-val tabular">{formatTemp(st.nozzle_temp, st.nozzle_target)}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-box-label">
                    <Thermometer size={12} color="#3b82f6" /> Heizbett
                  </div>
                  <div className="stat-box-val tabular">{formatTemp(st.bed_temp, st.bed_target)}</div>
                </div>
              </div>

              {state.mode === 'advanced' && <TempChart points={state.temp_history[p.id] || []} />}

              <div className="btn-row">
                {stKey === 'printing' && (
                  <button
                    className="btn"
                    disabled={!state.controls_enabled}
                    onClick={() => sendAction(p.id, 'pause')}
                  >
                    <Pause size={14} /> Pause
                  </button>
                )}
                {stKey === 'paused' && (
                  <button
                    className="btn btn-primary"
                    disabled={!state.controls_enabled}
                    onClick={() => sendAction(p.id, 'resume')}
                  >
                    <Play size={14} /> Weiter
                  </button>
                )}
                {(stKey === 'printing' || stKey === 'paused') && (
                  <button
                    className="btn btn-danger"
                    disabled={!state.controls_enabled}
                    onClick={() => sendAction(p.id, 'cancel')}
                  >
                    <Square size={14} /> Abbrechen
                  </button>
                )}
                <button className="btn" onClick={() => setSelected(p)} style={{ marginLeft: 'auto' }}>
                  <SlidersHorizontal size={14} /> Details
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {selected && (
        <PrinterModal
          printer={selected}
          status={state.statuses[selected.id]}
          controlsEnabled={state.controls_enabled}
          onClose={() => setSelected(null)}
          onToast={onToast}
          onRefresh={onRefresh}
        />
      )}

      {showAdd && (
        <AddPrinterModal onClose={() => setShowAdd(false)} onToast={onToast} onRefresh={onRefresh} />
      )}
    </>
  );
};
