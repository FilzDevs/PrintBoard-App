import React, { useState } from 'react';
import { RotateCcw, Plus, Trash2 } from 'lucide-react';
import { postApi } from '../api';
import type { AppState } from '../types';

interface Props {
  state: AppState;
  onToast: (msg: string, isError?: boolean) => void;
  onRefresh: () => void;
}

export const MaintenancePage: React.FC<Props> = ({ state, onToast, onRefresh }) => {
  const [title, setTitle] = useState('');
  const [interval, setInterval] = useState('100');

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
        <div className="card-title">Eigene Wartungsaufgabe hinzufügen</div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <input
            className="input"
            style={{ flex: 2, minWidth: 200 }}
            placeholder="z. B. Düse wechseln"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <input
            className="input"
            style={{ width: 140 }}
            type="number"
            placeholder="Intervall (h)"
            value={interval}
            onChange={(e) => setInterval(e.target.value)}
          />
          <button
            className="btn btn-primary"
            onClick={() => {
              if (!title.trim()) return;
              act(
                '/api/maintenance/add_task',
                { title: title.trim(), interval_h: Number(interval) || 100 },
                'Aufgabe hinzugefügt'
              );
              setTitle('');
            }}
          >
            <Plus size={14} /> Hinzufügen
          </button>
        </div>
      </div>

      <div className="cards-grid">
        {state.printers.map((p) => {
          const hours = state.printer_hours[p.id] || 0;
          const pMaint = state.maintenance[p.id] || {};
          return (
            <div key={p.id} className="card">
              <div className="card-header">
                <div className="card-title">{p.name}</div>
                <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{hours.toFixed(1)} h Laufzeit</span>
              </div>

              {state.maintenance_tasks.map((task) => {
                const lastH = pMaint[task.key] || 0;
                const since = Math.max(0, hours - lastH);
                const pct = Math.min(100, Math.round((since / Math.max(1, task.interval_h)) * 100));
                return (
                  <div key={task.key} className="stat-box">
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span>{task.title}</span>
                      <span style={{ color: pct >= 90 ? 'var(--danger)' : 'var(--text-muted)' }}>
                        {since.toFixed(1)} / {task.interval_h} h
                      </span>
                    </div>
                    <div className="progress-track" style={{ marginBottom: 6 }}>
                      <div
                        className="progress-fill"
                        style={{
                          width: `${pct}%`,
                          background: pct >= 90 ? 'var(--danger)' : undefined,
                        }}
                      />
                    </div>
                    <div className="btn-row">
                      <button
                        className="btn"
                        onClick={() =>
                          act('/api/maintenance/reset', { printer_id: p.id, task_key: task.key }, 'Zurückgesetzt')
                        }
                      >
                        <RotateCcw size={12} /> Erledigt
                      </button>
                      {!task.builtin && (
                        <button
                          className="btn btn-danger"
                          onClick={() =>
                            act('/api/maintenance/delete_task', { key: task.key }, 'Aufgabe gelöscht')
                          }
                        >
                          <Trash2 size={12} />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
};
