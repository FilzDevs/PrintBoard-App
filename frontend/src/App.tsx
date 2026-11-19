import React, { useCallback, useEffect, useState } from 'react';
import {
  Printer,
  ListOrdered,
  Disc,
  Wrench,
  Calculator,
  Box,
  Compass,
  Video,
  History,
  Settings,
  RefreshCw,
  Search,
} from 'lucide-react';
import { fetchState, postApi } from './api';
import type { AppState } from './types';
import { FleetPage } from './pages/FleetPage';
import { QueuePage } from './pages/QueuePage';
import { SpoolmanPage } from './pages/SpoolmanPage';
import { MaintenancePage } from './pages/MaintenancePage';
import { CostsPage } from './pages/CostsPage';
import { LibraryPage } from './pages/LibraryPage';
import { DiscoverPage } from './pages/DiscoverPage';
import { CamerasPage } from './pages/CamerasPage';
import { HistoryPage } from './pages/HistoryPage';
import { SettingsPage } from './pages/SettingsPage';

type PageId =
  | 'fleet'
  | 'queue'
  | 'spoolman'
  | 'maintenance'
  | 'costs'
  | 'discover'
  | 'library'
  | 'cameras'
  | 'history'
  | 'settings';

const NAV: { id: PageId; label: string; icon: React.ReactNode }[] = [
  { id: 'fleet', label: 'Drucker-Flotte', icon: <Printer size={17} /> },
  { id: 'queue', label: 'Warteschlange', icon: <ListOrdered size={17} /> },
  { id: 'spoolman', label: 'Spoolman & Trockner', icon: <Disc size={17} /> },
  { id: 'maintenance', label: 'Wartung', icon: <Wrench size={17} /> },
  { id: 'costs', label: 'Kostenrechner', icon: <Calculator size={17} /> },
  { id: 'discover', label: 'Modelle finden', icon: <Compass size={17} /> },
  { id: 'library', label: 'Lokale Modelle', icon: <Box size={17} /> },
  { id: 'cameras', label: 'Kameras', icon: <Video size={17} /> },
  { id: 'history', label: 'Verlauf', icon: <History size={17} /> },
  { id: 'settings', label: 'Einstellungen', icon: <Settings size={17} /> },
];

export const App: React.FC = () => {
  const [page, setPage] = useState<PageId>('fleet');
  const [state, setState] = useState<AppState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toasts, setToasts] = useState<{ id: number; msg: string; isError?: boolean }[]>([]);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [cmdQuery, setCmdQuery] = useState('');

  const addToast = useCallback((msg: string, isError = false) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, msg, isError }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3200);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const s = await fetchState();
      setState(s);
      setError(null);
      document.documentElement.setAttribute('data-theme', s.theme === 'light' ? 'light' : 'dark');
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    (window as unknown as { navigatePrintBoard?: (p: PageId) => void }).navigatePrintBoard = setPage;
    refresh();
    const timer = setInterval(refresh, 2000);
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCmdOpen((v) => !v);
        setCmdQuery('');
      } else if (e.key === 'Escape') {
        setCmdOpen(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => {
      clearInterval(timer);
      window.removeEventListener('keydown', onKey);
    };
  }, [refresh]);

  const currentNav = NAV.find((n) => n.id === page);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo">PB</div>
          <div>
            <div className="brand-title">PrintBoard</div>
            <div className="brand-sub">React Web UI</div>
          </div>
        </div>

        {NAV.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${page === item.id ? 'active' : ''}`}
            onClick={() => setPage(item.id)}
          >
            {item.icon}
            <span>{item.label}</span>
            {item.id === 'fleet' && state && (
              <span className="nav-badge">{state.printers.length}</span>
            )}
            {item.id === 'queue' && state && state.queue.length > 0 && (
              <span className="nav-badge">{state.queue.length}</span>
            )}
          </button>
        ))}
      </aside>

      <div className="main-col">
        <header className="topbar">
          <div className="topbar-title">{currentNav?.label}</div>
          <div className="topbar-actions">
            <button className="cmd-trigger" onClick={() => { setCmdOpen(true); setCmdQuery(''); }}>
              <Search size={13} /> Schnellzugriff <kbd>Ctrl+K</kbd>
            </button>
            {state && (
              <button
                className="btn"
                onClick={() =>
                  postApi('/api/mode', { mode: state.mode === 'easy' ? 'advanced' : 'easy' }).then(
                    refresh
                  )
                }
              >
                {state.mode === 'advanced' ? 'Advanced Mode' : 'Easy Mode'}
              </button>
            )}
            <button className="btn" onClick={refresh}>
              <RefreshCw size={14} /> Sync
            </button>
          </div>
        </header>

        <main className="content">
          {error && !state && (
            <div className="card" style={{ borderColor: 'var(--danger)' }}>
              <div className="card-title">Server nicht erreichbar</div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                Bitte starte `printboard-server` ({error}).
              </div>
            </div>
          )}

          {state && page === 'fleet' && (
            <FleetPage state={state} onToast={addToast} onRefresh={refresh} />
          )}
          {state && page === 'queue' && (
            <QueuePage state={state} onToast={addToast} onRefresh={refresh} />
          )}
          {state && page === 'spoolman' && (
            <SpoolmanPage state={state} onToast={addToast} onRefresh={refresh} />
          )}
          {state && page === 'maintenance' && (
            <MaintenancePage state={state} onToast={addToast} onRefresh={refresh} />
          )}
          {state && page === 'costs' && (
            <CostsPage state={state} onToast={addToast} onRefresh={refresh} />
          )}
          {state && page === 'discover' && <DiscoverPage state={state} onToast={addToast} />}
          {state && page === 'library' && (
            <LibraryPage state={state} onToast={addToast} onOpenDiscover={() => setPage('discover')} />
          )}
          {state && page === 'cameras' && <CamerasPage />}
          {state && page === 'history' && <HistoryPage />}
          {state && page === 'settings' && (
            <SettingsPage state={state} onToast={addToast} onRefresh={refresh} />
          )}
        </main>
      </div>

      <div className="toast-stack">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.isError ? 'error' : ''}`}>
            {t.msg}
          </div>
        ))}
      </div>

      {cmdOpen && (
        <div className="modal-backdrop" onClick={() => setCmdOpen(false)}>
          <div className="modal" style={{ maxWidth: 460 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-body" style={{ padding: 14 }}>
              <input
                autoFocus
                className="input"
                placeholder="Seite oder Aktion suchen…"
                value={cmdQuery}
                onChange={(e) => setCmdQuery(e.target.value)}
              />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {NAV.filter((n) => n.label.toLowerCase().includes(cmdQuery.toLowerCase())).map((n) => (
                  <button
                    key={n.id}
                    className={`nav-item ${page === n.id ? 'active' : ''}`}
                    onClick={() => {
                      setPage(n.id);
                      setCmdOpen(false);
                    }}
                  >
                    {n.icon}
                    <span>{n.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
