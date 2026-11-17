import React, { useCallback, useEffect, useState } from 'react';
import {
  Compass,
  Download,
  ExternalLink,
  Heart,
  Layers,
  RefreshCw,
  Search,
  Sparkles,
  User,
} from 'lucide-react';
import { getApi, postApi } from '../api';
import type { AppState } from '../types';

interface ModelSearchResult {
  id: string;
  title: string;
  author: string;
  source: string;
  source_color: string;
  url: string;
  thumbnail: string;
  likes: number;
  downloads: number;
  is_free: boolean;
  snippet: string;
}

interface PlatformLink {
  name: string;
  color: string;
  url: string;
  home: string;
  desc: string;
}

interface SearchResponse {
  ok: boolean;
  query: string;
  site: string;
  sort: string;
  total: number;
  counts: Record<string, number>;
  items: ModelSearchResult[];
  platforms: PlatformLink[];
  trending: string[];
}

interface Props {
  state: AppState;
  onToast: (msg: string, isError?: boolean) => void;
}

const SITE_FILTERS = [
  { id: 'all', label: 'Alle Seiten', color: '#00e5ff' },
  { id: 'printables', label: 'Printables', color: '#FA6831' },
  { id: 'myminifactory', label: 'MyMiniFactory', color: '#06B6D4' },
  { id: 'makerworld', label: 'MakerWorld', color: '#10B981' },
  { id: 'thingiverse', label: 'Thingiverse', color: '#3B82F6' },
  { id: 'thangs', label: 'Thangs', color: '#8B5CF6' },
  { id: 'cults3d', label: 'Cults3D', color: '#EC4899' },
];

export const DiscoverPage: React.FC<Props> = ({ state, onToast }) => {
  const [queryInput, setQueryInput] = useState('Gridfinity');
  const [activeQuery, setActiveQuery] = useState('Gridfinity');
  const [siteFilter, setSiteFilter] = useState('all');
  const [sortBy, setSortBy] = useState('popular');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<SearchResponse | null>(null);

  const runSearch = useCallback(
    async (q: string, site: string, sort: string) => {
      const cleanQ = q.trim() || 'Gridfinity';
      setLoading(true);
      try {
        const qs = new URLSearchParams({
          q: cleanQ,
          site,
          sort,
        });
        const res = await getApi<SearchResponse>(`/api/models/search?${qs.toString()}`);
        setData(res);
        setActiveQuery(res.query || cleanQ);
      } catch (e) {
        onToast(`Suche fehlgeschlagen: ${(e as Error).message}`, true);
      } finally {
        setLoading(false);
      }
    },
    [onToast]
  );

  useEffect(() => {
    runSearch(activeQuery, siteFilter, sortBy);
  }, [activeQuery, siteFilter, sortBy, runSearch]);

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = queryInput.trim() || 'Gridfinity';
    setActiveQuery(q);
    runSearch(q, siteFilter, sortBy);
  };

  const selectTrending = (topic: string) => {
    setQueryInput(topic);
    setActiveQuery(topic);
  };

  const openUrl = async (url: string, useDesktopDock = false) => {
    if (useDesktopDock && state.is_desktop) {
      try {
        await postApi('/api/desktop/action', { action: 'open_model_browser', url });
        return;
      } catch {
        /* fallback to new tab */
      }
    }
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const items = data?.items || [];
  const platforms = data?.platforms || [];
  const trending = data?.trending || [
    'Gridfinity',
    'Voron',
    '3DBenchy',
    'Bambu AMS',
    'Spool Holder',
    'Multiboard',
    'Dummy 13',
    'Cable Chain',
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      {/* 1. Search Hero Card */}
      <div
        className="card"
        style={{
          background:
            'linear-gradient(135deg, rgba(0, 229, 255, 0.09) 0%, rgba(99, 102, 241, 0.09) 100%), var(--bg-card)',
          borderColor: 'rgba(0, 229, 255, 0.28)',
        }}
      >
        <div className="card-header" style={{ flexWrap: 'wrap', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 42,
                height: 42,
                borderRadius: 12,
                background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
                display: 'grid',
                placeItems: 'center',
                color: '#04101d',
              }}
            >
              <Compass size={22} />
            </div>
            <div>
              <div className="card-title" style={{ fontSize: 18 }}>
                3D-Modelle finden — Multi-Plattform Meta-Suche
              </div>
              <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>
                Durchsucht gleichzeitig Printables, MyMiniFactory, MakerWorld, Thingiverse, Thangs & Cults3D
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="status-pill" style={{ background: 'rgba(0, 229, 255, 0.14)', color: 'var(--accent)' }}>
              {loading ? 'Suche läuft…' : `${data?.total ?? 0} Treffer für „${activeQuery}“`}
            </span>
          </div>
        </div>

        <form onSubmit={handleFormSubmit} style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 260, position: 'relative' }}>
            <input
              className="input"
              style={{ width: '100%', paddingLeft: 14, height: 44, fontSize: 14.5 }}
              placeholder="Suchbegriff eingeben (z. B. Gridfinity, Voron, Bambu AMS, Benchy, Spool Holder)…"
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
            />
          </div>
          <select
            className="select"
            style={{ width: 210, height: 44 }}
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="popular">Sortierung: Plattform-Mix</option>
            <option value="downloads">Meiste Downloads / Aufrufe</option>
            <option value="likes">Meiste Likes ♥</option>
            <option value="title">Alphabetisch (A–Z)</option>
          </select>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ height: 44, padding: '0 20px', fontSize: 14 }}
          >
            {loading ? <RefreshCw size={15} /> : <Search size={15} />}
            Alle Seiten durchsuchen
          </button>
        </form>

        {/* Trending Quick-Chips */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, flexWrap: 'wrap' }}>
          <span
            style={{
              fontSize: 11.5,
              fontWeight: 700,
              color: 'var(--text-muted)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              marginRight: 4,
            }}
          >
            <Sparkles size={13} color="var(--accent)" /> Beliebt:
          </span>
          {trending.map((t) => {
            const isAct = activeQuery.toLowerCase() === t.toLowerCase();
            return (
              <button
                key={t}
                type="button"
                className="btn"
                onClick={() => selectTrending(t)}
                style={{
                  padding: '4px 11px',
                  fontSize: 12,
                  borderRadius: 999,
                  borderColor: isAct ? 'var(--accent)' : undefined,
                  color: isAct ? 'var(--accent)' : undefined,
                  background: isAct ? 'rgba(0, 229, 255, 0.12)' : undefined,
                }}
              >
                {t}
              </button>
            );
          })}
        </div>

        {/* Platform Filter Tabs */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            flexWrap: 'wrap',
            paddingTop: 6,
            borderTop: '1px solid var(--border)',
          }}
        >
          {SITE_FILTERS.map((sf) => {
            const active = siteFilter === sf.id;
            const count =
              sf.id === 'all'
                ? data?.total ?? 0
                : data?.counts?.[sf.label] ?? 0;
            return (
              <button
                key={sf.id}
                type="button"
                className="btn"
                onClick={() => setSiteFilter(sf.id)}
                style={{
                  borderColor: active ? sf.color : undefined,
                  background: active ? `${sf.color}22` : undefined,
                  color: active ? sf.color : undefined,
                  fontWeight: active ? 700 : 600,
                }}
              >
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: sf.color,
                    display: 'inline-block',
                  }}
                />
                {sf.label}
                {sf.id === 'all' || count > 0 ? (
                  <span
                    className="tabular"
                    style={{
                      fontSize: 11,
                      opacity: 0.85,
                      padding: '1px 6px',
                      borderRadius: 999,
                      background: 'rgba(148, 163, 184, 0.14)',
                    }}
                  >
                    {count}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      </div>

      {/* 2. Direct Platform Search Launchers (always clickable for all 6 sites) */}
      <div className="card" style={{ padding: '14px 18px' }}>
        <div
          style={{
            fontSize: 12,
            fontWeight: 700,
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
          }}
        >
          Direkt-Suche nach „{activeQuery}“ auf Plattform öffnen:
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(195px, 1fr))', gap: 10 }}>
          {platforms.map((p) => (
            <button
              key={p.name}
              type="button"
              className="btn"
              onClick={() => openUrl(p.url, state.is_desktop)}
              title={p.desc}
              style={{
                justifyContent: 'space-between',
                padding: '9px 13px',
                borderColor: `${p.color}44`,
                background: 'rgba(15, 23, 42, 0.5)',
              }}
            >
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontWeight: 700 }}>
                <span
                  style={{
                    width: 9,
                    height: 9,
                    borderRadius: '50%',
                    background: p.color,
                    boxShadow: `0 0 8px ${p.color}`,
                  }}
                />
                {p.name}
              </span>
              <ExternalLink size={13} color={p.color} />
            </button>
          ))}
        </div>
      </div>

      {/* 3. Clickable Model Results Grid */}
      {loading && items.length === 0 ? (
        <div className="card" style={{ alignItems: 'center', padding: 48, textAlign: 'center' }}>
          <RefreshCw size={28} color="var(--accent)" style={{ marginBottom: 8 }} />
          <div className="card-title">Durchsuche 3D-Modell-Plattformen nach „{activeQuery}“…</div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Printables, MyMiniFactory, MakerWorld, Thingiverse, Thangs & Cults3D werden abgefragt.
          </div>
        </div>
      ) : items.length === 0 ? (
        <div className="card" style={{ alignItems: 'center', padding: 42, textAlign: 'center' }}>
          <div className="card-title">Keine direkten Treffer für diesen Filter gefunden</div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', maxWidth: 520 }}>
            Klicke oben auf einen der 6 Plattform-Buttons, um die Suche nach „{activeQuery}“ direkt auf der jeweiligen
            Webseite zu öffnen, oder wähle „Alle Seiten“.
          </div>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: 16,
          }}
        >
          {items.map((item) => (
            <div
              key={item.id}
              className="card"
              onClick={() => openUrl(item.url, false)}
              style={{
                padding: 0,
                overflow: 'hidden',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              {/* Thumbnail Header */}
              <div>
                <div
                  style={{
                    position: 'relative',
                    width: '100%',
                    height: 185,
                    background: 'linear-gradient(145deg, #1e293b 0%, #334155 100%)',
                    borderBottom: '1px solid var(--border)',
                    overflow: 'hidden',
                    display: 'grid',
                    placeItems: 'center',
                  }}
                >
                  {item.thumbnail ? (
                    <img
                      src={item.thumbnail}
                      alt={item.title}
                      loading="lazy"
                      referrerPolicy="no-referrer"
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        transition: 'transform 0.25s ease',
                      }}
                      onError={(e) => {
                        (e.currentTarget as HTMLImageElement).style.display = 'none';
                      }}
                    />
                  ) : (
                    <div
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: 8,
                        color: item.source_color || 'var(--accent)',
                      }}
                    >
                      <Layers size={42} />
                      <span style={{ fontSize: 12, fontWeight: 700, opacity: 0.85 }}>{item.source} 3D-Modell</span>
                    </div>
                  )}

                  {/* Platform Badge Overlay */}
                  <span
                    style={{
                      position: 'absolute',
                      top: 10,
                      left: 10,
                      padding: '4px 10px',
                      borderRadius: 999,
                      fontSize: 11,
                      fontWeight: 800,
                      background: 'rgba(5, 8, 17, 0.85)',
                      color: item.source_color || '#00e5ff',
                      border: `1px solid ${item.source_color || '#00e5ff'}66`,
                      backdropFilter: 'blur(8px)',
                    }}
                  >
                    ● {item.source}
                  </span>

                  {item.is_free && (
                    <span
                      style={{
                        position: 'absolute',
                        top: 10,
                        right: 10,
                        padding: '3px 9px',
                        borderRadius: 999,
                        fontSize: 10.5,
                        fontWeight: 800,
                        background: 'rgba(16, 185, 129, 0.22)',
                        color: '#10b981',
                        border: '1px solid rgba(16, 185, 129, 0.45)',
                        backdropFilter: 'blur(8px)',
                      }}
                    >
                      FREE
                    </span>
                  )}
                </div>

                {/* Title & Creator */}
                <div style={{ padding: '14px 16px 8px' }}>
                  <div
                    style={{
                      fontWeight: 700,
                      fontSize: 14.5,
                      lineHeight: 1.35,
                      marginBottom: 6,
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}
                    title={item.title}
                  >
                    {item.title}
                  </div>
                  <div
                    style={{
                      fontSize: 12,
                      color: 'var(--text-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 5,
                      marginBottom: 6,
                    }}
                  >
                    <User size={12} /> {item.author}
                  </div>
                  {item.snippet && (
                    <div
                      style={{
                        fontSize: 11.5,
                        color: 'var(--text-muted)',
                        opacity: 0.85,
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                      }}
                    >
                      {item.snippet}
                    </div>
                  )}
                </div>
              </div>

              {/* Footer Stats & Clickable Action Buttons */}
              <div
                style={{
                  padding: '10px 16px 14px',
                  borderTop: '1px solid var(--border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 8,
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <div
                  className="tabular"
                  style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 12, color: 'var(--text-muted)' }}
                >
                  {item.likes > 0 && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                      <Heart size={12} color="#f43f5e" /> {item.likes.toLocaleString('de-DE')}
                    </span>
                  )}
                  {item.downloads > 0 && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                      <Download size={12} color="var(--accent)" /> {item.downloads.toLocaleString('de-DE')}
                    </span>
                  )}
                </div>

                <div style={{ display: 'flex', gap: 6, marginLeft: 'auto' }}>
                  {state.is_desktop && (
                    <button
                      type="button"
                      className="btn"
                      style={{ padding: '6px 10px', fontSize: 11.5 }}
                      onClick={() => openUrl(item.url, true)}
                      title="Im integrierten PrintBoard-Browser mit 1-Klick-Bibliothek-Download öffnen"
                    >
                      App-Browser
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ padding: '6px 11px', fontSize: 12 }}
                    onClick={() => openUrl(item.url, false)}
                  >
                    <ExternalLink size={13} /> Öffnen
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
