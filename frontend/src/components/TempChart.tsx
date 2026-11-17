import React from 'react';
import type { TempPoint } from '../types';

interface Props {
  points: TempPoint[];
  height?: number;
}

export const TempChart: React.FC<Props> = ({ points, height = 74 }) => {
  if (!points || points.length < 2) {
    return (
      <div
        style={{
          height,
          display: 'grid',
          placeItems: 'center',
          fontSize: 11.5,
          color: 'var(--text-muted)',
          background: 'var(--bg)',
          borderRadius: 10,
          border: '1px solid var(--border)',
        }}
      >
        Sammle Temperaturdaten…
      </div>
    );
  }

  const w = 320;
  const h = height;
  const pad = 6;
  const recent = points.slice(-60);

  const vals = recent.flatMap((p) => [p.nozzle ?? 0, p.bed ?? 0]);
  const maxVal = Math.max(60, ...vals) + 10;
  const minVal = 0;

  const toPoints = (key: 'nozzle' | 'bed') =>
    recent
      .map((p, i) => {
        const x = pad + (i / (recent.length - 1)) * (w - pad * 2);
        const v = p[key] ?? 0;
        const y = h - pad - ((v - minVal) / (maxVal - minVal)) * (h - pad * 2);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      style={{
        width: '100%',
        height,
        background: 'var(--bg)',
        borderRadius: 10,
        border: '1px solid var(--border)',
      }}
    >
      <polyline fill="none" stroke="#3b82f6" strokeWidth="1.8" points={toPoints('bed')} />
      <polyline fill="none" stroke="#f97316" strokeWidth="2" points={toPoints('nozzle')} />
    </svg>
  );
};
