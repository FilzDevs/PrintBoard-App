import React, { useEffect, useState } from 'react';
import { RefreshCw, Maximize2, Grid2x2, Grid3x3, ExternalLink, VideoOff } from 'lucide-react';
import { getApi } from '../api';

interface CamItem {
  printer: string;
  name: string;
  url: string;
  service?: string;
}

export const CamerasPage: React.FC = () => {
  const [cams, setCams] = useState<CamItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [layout, setLayout] = useState<'grid2' | 'grid3' | 'focus'>('grid2');
  const [focusIdx, setFocusIdx] = useState(0);
  const [reloadKey, setReloadKey] = useState(0);
  const [failedUrls, setFailedUrls] = useState<Record<string, boolean>>({});

  const loadCams = async () => {
    setLoading(true);
    try {
      const res = await getApi<{ cams?: CamItem[] }>('/api/webcams');
      setCams(res.cams || []);
      setFailedUrls({});
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCams();
  }, []);

  if (loading && cams.length === 0) {
    return (
      <div className="card">
        <div className="card-title">Suche Kameras…</div>
      </div>
    );
  }

  if (cams.length === 0) {
    return (
      <div className="card">
        <div className="card-header">
          <div className="card-title">Keine Kameras gefunden</div>
          <button className="btn" onClick={loadCams}>
            <RefreshCw size={14} /> Neu laden
          </button>
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          Es wurden keine Moonraker-Webcams oder Drucker-Displays gefunden. Stelle sicher, dass dein
          Drucker online ist und in Moonraker/Mainsail/Fluidd eine Webcam konfiguriert wurde.
        </div>
      </div>
    );
  }

  const renderFeed = (cam: CamItem, idx: number, tall = false) => {
    const key = `${cam.url}_${reloadKey}`;
    const isIframe = cam.service === 'iframe';
    const failed = failedUrls[cam.url];

    return (
      <div key={`${cam.name}_${idx}`} className="card">
        <div className="card-header">
          <div>
            <div className="card-title">{cam.name}</div>
            <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
              {cam.printer} · {isIframe ? 'Display / UI' : 'Live Stream'}
            </div>
          </div>
          <div className="btn-row">
            <button
              className="btn"
              title="Fokus-Ansicht"
              onClick={() => {
                setFocusIdx(idx);
                setLayout('focus');
              }}
            >
              <Maximize2 size={13} />
            </button>
            <a
              href={cam.url}
              target="_blank"
              rel="noreferrer"
              className="btn"
              title="Direkt öffnen"
              style={{ textDecoration: 'none' }}
            >
              <ExternalLink size={13} />
            </a>
          </div>
        </div>

        {isIframe ? (
          <iframe
            key={key}
            src={cam.url}
            title={cam.name}
            className="cam-frame"
            style={{ border: '1px solid var(--border)', height: tall ? 520 : undefined }}
          />
        ) : failed ? (
          <div
            className="cam-frame"
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 10,
              color: 'var(--text-muted)',
              padding: 16,
            }}
          >
            <VideoOff size={28} />
            <div style={{ fontSize: 12.5, textAlign: 'center' }}>
              Stream konnte nicht eingebettet werden ({cam.url})
            </div>
            <a href={cam.url} target="_blank" rel="noreferrer" className="btn">
              <ExternalLink size={13} /> Stream direkt öffnen
            </a>
          </div>
        ) : (
          <img
            key={key}
            src={cam.url}
            alt={cam.name}
            className="cam-frame"
            style={{ height: tall ? 520 : undefined }}
            onError={() => setFailedUrls((prev) => ({ ...prev, [cam.url]: true }))}
          />
        )}
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
        <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          {cams.length} {cams.length === 1 ? 'Kamera / Display' : 'Kameras & Displays'} aktiv
        </div>
        <div className="btn-row">
          <button
            className={`btn ${layout === 'grid2' ? 'btn-primary' : ''}`}
            onClick={() => setLayout('grid2')}
          >
            <Grid2x2 size={14} /> 2-Spalten
          </button>
          <button
            className={`btn ${layout === 'grid3' ? 'btn-primary' : ''}`}
            onClick={() => setLayout('grid3')}
          >
            <Grid3x3 size={14} /> 3-Spalten
          </button>
          <button
            className={`btn ${layout === 'focus' ? 'btn-primary' : ''}`}
            onClick={() => setLayout('focus')}
          >
            <Maximize2 size={14} /> Cinema
          </button>
          <button
            className="btn"
            onClick={() => {
              setReloadKey((k) => k + 1);
              loadCams();
            }}
          >
            <RefreshCw size={14} /> Neu laden
          </button>
        </div>
      </div>

      {layout === 'focus' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {renderFeed(cams[Math.min(focusIdx, cams.length - 1)], Math.min(focusIdx, cams.length - 1), true)}
          {cams.length > 1 && (
            <div className="btn-row">
              {cams.map((c, idx) => (
                <button
                  key={idx}
                  className={`btn ${idx === focusIdx ? 'btn-primary' : ''}`}
                  onClick={() => setFocusIdx(idx)}
                >
                  {c.name}
                </button>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className={layout === 'grid3' ? 'cam-grid-3' : 'cam-grid-2'}>
          {cams.map((cam, idx) => renderFeed(cam, idx))}
        </div>
      )}
    </div>
  );
};
