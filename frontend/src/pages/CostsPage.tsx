import React, { useState } from 'react';
import { Calculator, Save } from 'lucide-react';
import { postApi } from '../api';
import type { AppState, CostRates } from '../types';

interface Props {
  state: AppState;
  onToast: (msg: string, isError?: boolean) => void;
  onRefresh: () => void;
}

export const CostsPage: React.FC<Props> = ({ state, onToast, onRefresh }) => {
  const [rates, setRates] = useState<CostRates>(state.cost_rates);
  const [grams, setGrams] = useState('85');
  const [hours, setHours] = useState('3.5');
  const [quote, setQuote] = useState<Record<string, number> | null>(null);

  const calc = async () => {
    try {
      const res = await postApi<Record<string, number>>('/api/costs/quote', {
        grams: Number(grams) || 0,
        hours: Number(hours) || 0,
        ...rates,
      });
      setQuote(res);
    } catch (e) {
      onToast(`Fehler: ${(e as Error).message}`, true);
    }
  };

  const saveRates = async () => {
    try {
      await postApi('/api/costs/save', { ...rates });
      onToast('Kostensätze gespeichert');
      onRefresh();
    } catch (e) {
      onToast(`Fehler: ${(e as Error).message}`, true);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="card">
        <div className="card-header">
          <div className="card-title">Angebots- & Druckkostenrechner</div>
          <button className="btn" onClick={saveRates}>
            <Save size={14} /> Sätze speichern
          </button>
        </div>

        <div className="form-grid">
          <div>
            <label className="field-label">Filamentgewicht (g)</label>
            <input className="input" type="number" value={grams} onChange={(e) => setGrams(e.target.value)} />
          </div>
          <div>
            <label className="field-label">Druckzeit (Stunden)</label>
            <input className="input" type="number" step="0.1" value={hours} onChange={(e) => setHours(e.target.value)} />
          </div>
          <div>
            <label className="field-label">Filament (€/kg)</label>
            <input
              className="input"
              type="number"
              value={rates.eur_kg}
              onChange={(e) => setRates({ ...rates, eur_kg: Number(e.target.value) })}
            />
          </div>
          <div>
            <label className="field-label">Strom (€/kWh)</label>
            <input
              className="input"
              type="number"
              step="0.01"
              value={rates.kwh}
              onChange={(e) => setRates({ ...rates, kwh: Number(e.target.value) })}
            />
          </div>
          <div>
            <label className="field-label">Leistung (W)</label>
            <input
              className="input"
              type="number"
              value={rates.watts}
              onChange={(e) => setRates({ ...rates, watts: Number(e.target.value) })}
            />
          </div>
          <div>
            <label className="field-label">Marge (%)</label>
            <input
              className="input"
              type="number"
              value={rates.margin_pct}
              onChange={(e) => setRates({ ...rates, margin_pct: Number(e.target.value) })}
            />
          </div>
        </div>

        <div>
          <button className="btn btn-primary" onClick={calc}>
            <Calculator size={14} /> Preis berechnen
          </button>
        </div>

        {quote && (
          <div className="kpi-grid" style={{ marginTop: 8, marginBottom: 0 }}>
            <div className="kpi-card">
              <div className="kpi-label">Material + Strom + Verschleiß</div>
              <div className="kpi-value">{(quote.base_cost ?? quote.total_cost ?? 0).toFixed(2)} €</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Netto-Preis</div>
              <div className="kpi-value">{(quote.net_price ?? 0).toFixed(2)} €</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Brutto-Angebot (inkl. MwSt.)</div>
              <div className="kpi-value" style={{ color: 'var(--accent)' }}>
                {(quote.gross_price ?? quote.total_price ?? 0).toFixed(2)} €
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
