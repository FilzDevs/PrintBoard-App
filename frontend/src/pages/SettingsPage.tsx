import React, { useState } from 'react';
import { Save, Bell } from 'lucide-react';
import { postApi } from '../api';
import type { AppState } from '../types';

interface Props {
  state: AppState;
  onToast: (msg: string, isError?: boolean) => void;
  onRefresh: () => void;
}

export const SettingsPage: React.FC<Props> = ({ state, onToast, onRefresh }) => {
  const [spoolmanUrl, setSpoolmanUrl] = useState(state.spoolman_url || '');
  const [modelsDir, setModelsDir] = useState(state.models_dir || '');
  const [slicerCmd, setSlicerCmd] = useState(state.slicer_cmd || '');
  const [discordUrl, setDiscordUrl] = useState(String(state.notify_cfg?.discord_webhook || ''));

  const saveSettings = async (patch: Record<string, unknown>, msg = 'Einstellungen gespeichert') => {
    try {
      await postApi('/api/settings/save', patch);
      onToast(msg);
      onRefresh();
    } catch (e) {
      onToast(`Fehler: ${(e as Error).message}`, true);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="card">
        <div className="card-title">Oberfläche & Verhalten</div>
        <div className="form-grid">
          <div>
            <label className="field-label">Modus</label>
            <select
              className="select"
              value={state.mode}
              onChange={(e) => postApi('/api/mode', { mode: e.target.value }).then(onRefresh)}
            >
              <option value="easy">Easy Mode</option>
              <option value="advanced">Advanced Mode (inkl. Temp-Charts)</option>
            </select>
          </div>
          <div>
            <label className="field-label">Theme</label>
            <select
              className="select"
              value={state.theme}
              onChange={(e) => saveSettings({ theme: e.target.value }, 'Theme geändert')}
            >
              <option value="obsidian">Dark (Obsidian)</option>
              <option value="light">Hell (Light)</option>
            </select>
          </div>
        </div>

        <div className="btn-row">
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={state.sim_enabled}
              onChange={(e) => saveSettings({ sim_enabled: e.target.checked })}
            />
            Demo-Flotte aktivieren
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={state.controls_enabled}
              onChange={(e) => saveSettings({ controls_enabled: e.target.checked })}
            />
            Druckersteuerung erlauben
          </label>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Pfade & Integrationen</div>
        <div className="form-grid">
          <div>
            <label className="field-label">Spoolman URL</label>
            <input className="input" value={spoolmanUrl} onChange={(e) => setSpoolmanUrl(e.target.value)} />
          </div>
          <div>
            <label className="field-label">Modell-Ordner</label>
            <input className="input" value={modelsDir} onChange={(e) => setModelsDir(e.target.value)} />
          </div>
          <div>
            <label className="field-label">Slicer-Befehl</label>
            <input className="input" value={slicerCmd} onChange={(e) => setSlicerCmd(e.target.value)} />
          </div>
        </div>

        <div className="btn-row">
          <button
            className="btn btn-primary"
            onClick={() => {
              postApi('/api/spoolman/save', { url: spoolmanUrl });
              saveSettings({ models_dir: modelsDir, slicer_cmd: slicerCmd });
            }}
          >
            <Save size={14} /> Speichern
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Benachrichtigungen</div>
        <div>
          <label className="field-label">Discord Webhook URL</label>
          <input
            className="input"
            placeholder="https://discord.com/api/webhooks/..."
            value={discordUrl}
            onChange={(e) => setDiscordUrl(e.target.value)}
          />
        </div>
        <div className="btn-row">
          <button
            className="btn"
            onClick={() =>
              postApi('/api/notify/save', { discord_webhook: discordUrl })
                .then(() => onToast('Webhook gespeichert'))
                .catch((e) => onToast((e as Error).message, true))
            }
          >
            <Save size={14} /> Webhook speichern
          </button>
          <button
            className="btn"
            onClick={() =>
              postApi('/api/notify/test', {})
                .then(() => onToast('Testbenachrichtigung gesendet'))
                .catch((e) => onToast((e as Error).message, true))
            }
          >
            <Bell size={14} /> Test senden
          </button>
        </div>
      </div>
    </div>
  );
};
