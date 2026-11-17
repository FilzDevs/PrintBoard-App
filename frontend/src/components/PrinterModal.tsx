import React, { useEffect, useState } from 'react';
import { X, Play, Terminal, FolderOpen, Flame, Home, Trash2 } from 'lucide-react';
import { fetchPrinterDetails, postApi } from '../api';
import type { Printer, PrinterDetails, PrinterStatus } from '../types';
import { formatBytes, formatTemp } from '../utils';

interface Props {
  printer: Printer;
  status?: PrinterStatus;
  controlsEnabled: boolean;
  onClose: () => void;
  onToast: (msg: string, isError?: boolean) => void;
  onRefresh: () => void;
}

export const PrinterModal: React.FC<Props> = ({
  printer,
  status,
  controlsEnabled,
  onClose,
  onToast,
  onRefresh,
}) => {
  const [tab, setTab] = useState<'controls' | 'console' | 'files'>('controls');
  const [details, setDetails] = useState<PrinterDetails>({ files: [], macros: [], console: [] });
  const [nozzleTarget, setNozzleTarget] = useState('210');
  const [bedTarget, setBedTarget] = useState('60');
  const [gcode, setGcode] = useState('');

  const loadDetails = async () => {
    try {
      const d = await fetchPrinterDetails(printer.id);
      setDetails(d);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    loadDetails();
  }, [printer.id]);

  const sendControl = async (action: string, extra: Record<string, unknown> = {}) => {
    try {
      await postApi('/api/control', { printer_id: printer.id, action, ...extra });
      onToast(`Aktion "${action}" gesendet`);
      onRefresh();
    } catch (e) {
      onToast(`Fehler: ${(e as Error).message}`, true);
    }
  };

  const deletePrinter = async () => {
    if (!confirm(`Drucker "${printer.name}" wirklich entfernen?`)) return;
    try {
      await postApi('/api/printers/delete', { id: printer.id });
      onToast('Drucker entfernt');
      onRefresh();
      onClose();
    } catch (e) {
      onToast(`Fehler: ${(e as Error).message}`, true);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>{printer.name}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {printer.url || printer.bambu_ip || 'Simulierter Drucker'}
            </div>
          </div>
          <div className="btn-row">
            {!printer.is_sim && (
              <button className="btn btn-danger" onClick={deletePrinter}>
                <Trash2 size={14} /> Löschen
              </button>
            )}
            <button className="btn" onClick={onClose}>
              <X size={16} />
            </button>
          </div>
        </div>

        <div className="modal-body">
          <div className="tabs">
            <button
              className={`btn ${tab === 'controls' ? 'btn-primary' : ''}`}
              onClick={() => setTab('controls')}
            >
              <Flame size={14} /> Steuerung
            </button>
            <button
              className={`btn ${tab === 'console' ? 'btn-primary' : ''}`}
              onClick={() => setTab('console')}
            >
              <Terminal size={14} /> Konsole & Makros
            </button>
            <button
              className={`btn ${tab === 'files' ? 'btn-primary' : ''}`}
              onClick={() => setTab('files')}
            >
              <FolderOpen size={14} /> Dateien ({details.files.length})
            </button>
          </div>

          {tab === 'controls' && (
            <>
              <div className="stats-row">
                <div className="stat-box">
                  <div className="stat-box-label">Düse</div>
                  <div className="stat-box-val">
                    {formatTemp(status?.nozzle_temp, status?.nozzle_target)}
                  </div>
                </div>
                <div className="stat-box">
                  <div className="stat-box-label">Heizbett</div>
                  <div className="stat-box-val">
                    {formatTemp(status?.bed_temp, status?.bed_target)}
                  </div>
                </div>
              </div>

              <div className="form-grid">
                <div>
                  <label className="field-label">Düsen-Temperatur (°C)</label>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <input
                      className="input"
                      type="number"
                      value={nozzleTarget}
                      onChange={(e) => setNozzleTarget(e.target.value)}
                    />
                    <button
                      className="btn btn-primary"
                      disabled={!controlsEnabled}
                      onClick={() => sendControl('set_nozzle', { temp: Number(nozzleTarget) })}
                    >
                      Setzen
                    </button>
                  </div>
                </div>
                <div>
                  <label className="field-label">Bett-Temperatur (°C)</label>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <input
                      className="input"
                      type="number"
                      value={bedTarget}
                      onChange={(e) => setBedTarget(e.target.value)}
                    />
                    <button
                      className="btn btn-primary"
                      disabled={!controlsEnabled}
                      onClick={() => sendControl('set_bed', { temp: Number(bedTarget) })}
                    >
                      Setzen
                    </button>
                  </div>
                </div>
              </div>

              <div className="btn-row">
                <button
                  className="btn"
                  disabled={!controlsEnabled}
                  onClick={() => sendControl('home')}
                >
                  <Home size={14} /> Home All (G28)
                </button>
                <button
                  className="btn"
                  disabled={!controlsEnabled}
                  onClick={() => sendControl('cooldown')}
                >
                  Abkühlen
                </button>
                <button
                  className="btn btn-danger"
                  disabled={!controlsEnabled}
                  onClick={() => sendControl('estop')}
                >
                  NOT-AUS (M112)
                </button>
              </div>
            </>
          )}

          {tab === 'console' && (
            <>
              {details.macros.length > 0 && (
                <div>
                  <div className="field-label">Makros</div>
                  <div className="btn-row">
                    {details.macros.slice(0, 18).map((m) => (
                      <button
                        key={m}
                        className="btn"
                        disabled={!controlsEnabled}
                        onClick={() => sendControl('gcode', { gcode: m })}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  className="input"
                  placeholder="G-Code senden (z. B. G28 oder M105)"
                  value={gcode}
                  onChange={(e) => setGcode(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && gcode.trim()) {
                      sendControl('gcode', { gcode: gcode.trim() });
                      setGcode('');
                      setTimeout(loadDetails, 400);
                    }
                  }}
                />
                <button
                  className="btn btn-primary"
                  disabled={!controlsEnabled || !gcode.trim()}
                  onClick={() => {
                    sendControl('gcode', { gcode: gcode.trim() });
                    setGcode('');
                    setTimeout(loadDetails, 400);
                  }}
                >
                  Senden
                </button>
              </div>

              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: 10,
                  padding: 10,
                  maxHeight: 240,
                  overflowY: 'auto',
                  fontFamily: 'monospace',
                  fontSize: 12,
                }}
              >
                {details.console.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)' }}>Keine Konsolenausgabe</div>
                ) : (
                  details.console.slice(-40).map((c, idx) => (
                    <div key={idx} style={{ padding: '2px 0' }}>
                      {c.message}
                    </div>
                  ))
                )}
              </div>
            </>
          )}

          {tab === 'files' && (
            <table className="table">
              <thead>
                <tr>
                  <th>Datei</th>
                  <th>Größe</th>
                  <th>Aktion</th>
                </tr>
              </thead>
              <tbody>
                {details.files.length === 0 ? (
                  <tr>
                    <td colSpan={3} style={{ color: 'var(--text-muted)' }}>
                      Keine Dateien gefunden
                    </td>
                  </tr>
                ) : (
                  details.files.slice(0, 50).map((f, i) => {
                    const name = f.path || f.filename || 'unknown.gcode';
                    return (
                      <tr key={i}>
                        <td>{name}</td>
                        <td>{formatBytes(f.size)}</td>
                        <td>
                          <button
                            className="btn btn-primary"
                            disabled={!controlsEnabled}
                            onClick={() => sendControl('start_print', { filename: name })}
                          >
                            <Play size={13} /> Drucken
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
