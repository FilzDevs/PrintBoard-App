import React, { useEffect, useState } from 'react';
import { getApi } from '../api';
import { formatDuration } from '../utils';

interface HistoryJob {
  printer_name?: string;
  filename?: string;
  status?: string;
  total_duration?: number;
  filament_used?: number;
}

export const HistoryPage: React.FC = () => {
  const [jobs, setJobs] = useState<HistoryJob[]>([]);

  useEffect(() => {
    getApi<{ jobs?: HistoryJob[] }>('/api/history')
      .then((res) => setJobs(res.jobs || []))
      .catch(() => {});
  }, []);

  return (
    <div className="card">
      <div className="card-title">Druckverlauf ({jobs.length})</div>
      <table className="table">
        <thead>
          <tr>
            <th>Drucker</th>
            <th>Datei</th>
            <th>Status</th>
            <th>Dauer</th>
          </tr>
        </thead>
        <tbody>
          {jobs.length === 0 ? (
            <tr>
              <td colSpan={4} style={{ color: 'var(--text-muted)' }}>
                Noch kein Druckverlauf vorhanden
              </td>
            </tr>
          ) : (
            jobs.slice(0, 60).map((j, i) => (
              <tr key={i}>
                <td>{j.printer_name || '—'}</td>
                <td>{j.filename || '—'}</td>
                <td>{j.status || '—'}</td>
                <td>{formatDuration(j.total_duration)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};
