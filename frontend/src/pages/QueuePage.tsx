import React, { useState } from 'react';
import { ArrowUp, ArrowDown, Trash2, Send, Plus } from 'lucide-react';
import { postApi } from '../api';
import type { AppState } from '../types';

interface Props {
  state: AppState;
  onToast: (msg: string, isError?: boolean) => void;
  onRefresh: () => void;
}

export const QueuePage: React.FC<Props> = ({ state, onToast, onRefresh }) => {
  const [filename, setFilename] = useState('');
  const [printerId, setPrinterId] = useState(state.printers[0]?.id || '');
  const [material, setMaterial] = useState('PLA');

  const addJob = async () => {
    if (!filename.trim()) return;
    try {
      await postApi('/api/queue/add', {
        filename: filename.trim(),
        printer_id: printerId,
        material,
      });
      setFilename('');
      onToast('Job zur Warteschlange hinzugefügt');
      onRefresh();
    } catch (e) {
      onToast(`Fehler: ${(e as Error).message}`, true);
    }
  };

  const act = async (url: string, body: Record<string, unknown>, msg: string) => {
    try {
      await postApi(url, body);
      onToast(msg);
      onRefresh();
    } catch (e) {
      onToast(`Fehler: ${(e as Error).message}`, true);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="card">
        <div className="card-header">
          <div className="card-title">Neuen Druckjob einreihen</div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={state.auto_dispatch}
              onChange={(e) =>
                act('/api/settings/save', { auto_dispatch: e.target.checked }, 'Auto-Dispatch aktualisiert')
              }
            />
            Auto-Dispatch
          </label>
        </div>
        <div className="form-grid">
          <div>
            <label className="field-label">G-Code Datei</label>
            <input
              className="input"
              placeholder="z. B. benchy.gcode"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
            />
          </div>
          <div>
            <label className="field-label">Zieldrucker</label>
            <select className="select" value={printerId} onChange={(e) => setPrinterId(e.target.value)}>
              {state.printers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="field-label">Material</label>
            <select className="select" value={material} onChange={(e) => setMaterial(e.target.value)}>
              {state.materials.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <button className="btn btn-primary" onClick={addJob}>
            <Plus size={14} /> Einreihen
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">Aktuelle Warteschlange ({state.queue.length})</div>
          <button
            className="btn"
            disabled={state.queue.length === 0}
            onClick={() => act('/api/queue/dispatch', {}, 'Nächster Job gestartet')}
          >
            <Send size={14} /> Nächsten starten
          </button>
        </div>

        <table className="table">
          <thead>
            <tr>
              <th>#</th>
              <th>Datei</th>
              <th>Material</th>
              <th>Drucker</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {state.queue.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ color: 'var(--text-muted)' }}>
                  Warteschlange ist leer
                </td>
              </tr>
            ) : (
              state.queue.map((q, idx) => (
                <tr key={q.id || idx}>
                  <td>{idx + 1}</td>
                  <td>{q.filename}</td>
                  <td>{q.material || '—'}</td>
                  <td>{state.printers.find((p) => p.id === q.printer_id)?.name || q.printer_id || 'Auto'}</td>
                  <td>
                    <div className="btn-row">
                      <button
                        className="btn"
                        disabled={idx === 0}
                        onClick={() => act('/api/queue/move', { id: q.id, direction: 'up' }, 'Verschoben')}
                      >
                        <ArrowUp size={13} />
                      </button>
                      <button
                        className="btn"
                        disabled={idx === state.queue.length - 1}
                        onClick={() => act('/api/queue/move', { id: q.id, direction: 'down' }, 'Verschoben')}
                      >
                        <ArrowDown size={13} />
                      </button>
                      <button
                        className="btn btn-danger"
                        onClick={() => act('/api/queue/remove', { id: q.id }, 'Entfernt')}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
