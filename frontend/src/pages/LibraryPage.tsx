import React, { useEffect, useState } from 'react';
import { ExternalLink, RefreshCw, Scissors } from 'lucide-react';
import { getApi, postApi } from '../api';
import type { AppState } from '../types';
import { formatBytes } from '../utils';

interface Props {
  state: AppState;
  onToast: (msg: string, isError?: boolean) => void;
  onOpenDiscover?: () => void;
}

const SITES = [
  { name: 'Printables', url: 'https://www.printables.com' },
  { name: 'MakerWorld', url: 'https://makerworld.com' },
  { name: 'Thingiverse', url: 'https://www.thingiverse.com' },
  { name: 'Thangs', url: 'https://thangs.com' },
  { name: 'MyMiniFactory', url: 'https://www.myminifactory.com' },
  { name: 'Cults3D', url: 'https://cults3d.com' },
];

export const LibraryPage: React.FC<Props> = ({ state, onToast, onOpenDiscover }) => {
  const [models, setModels] = useState<{ name: string; path: string; size?: number; ext?: string }[]>([]);

  const load = async () => {
    try {
      const res = await getApi<{ files?: { name: string; path: string; size?: number; ext?: string }[] }>(
        '/api/library/list'
      );
      setModels(res.files || []);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openSlicer = async (path: string) => {
    try {
      await postApi('/api/library/action', { action: 'slice', path });
      onToast('Slicer gestartet');
    } catch (e) {
      onToast(`Fehler: ${(e as Error).message}`, true);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="card">
        <div className="card-header">
          <div className="card-title">3D-Modell-Plattformen</div>
          {onOpenDiscover && (
            <button className="btn btn-primary" onClick={onOpenDiscover}>
              Alle Seiten gleichzeitig durchsuchen →
            </button>
          )}
        </div>
        <div className="btn-row">
          {SITES.map((s) => (
            <a
              key={s.name}
              href={s.url}
              target="_blank"
              rel="noreferrer"
              className="btn"
              style={{ textDecoration: 'none' }}
            >
              <ExternalLink size={13} /> {s.name}
            </a>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">Lokale Modelle ({models.length})</div>
            <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{state.models_dir}</div>
          </div>
          <button className="btn" onClick={load}>
            <RefreshCw size={14} /> Aktualisieren
          </button>
        </div>

        <table className="table">
          <thead>
            <tr>
              <th>Datei</th>
              <th>Größe</th>
              <th>Aktion</th>
            </tr>
          </thead>
          <tbody>
            {models.length === 0 ? (
              <tr>
                <td colSpan={3} style={{ color: 'var(--text-muted)' }}>
                  Keine lokalen STL/3MF/OBJ-Dateien gefunden
                </td>
              </tr>
            ) : (
              models.slice(0, 60).map((m, i) => (
                <tr key={i}>
                  <td>{m.name}</td>
                  <td>{formatBytes(m.size)}</td>
                  <td>
                    <button className="btn" onClick={() => openSlicer(m.path)}>
                      <Scissors size={13} /> Im Slicer öffnen
                    </button>
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
