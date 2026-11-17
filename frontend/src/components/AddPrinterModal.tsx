import React, { useState } from 'react';
import { X, Search, CheckCircle2 } from 'lucide-react';
import { getApi, postApi } from '../api';

interface Props {
  onClose: () => void;
  onToast: (msg: string, isError?: boolean) => void;
  onRefresh: () => void;
}

export const AddPrinterModal: React.FC<Props> = ({ onClose, onToast, onRefresh }) => {
  const [name, setName] = useState('');
  const [url, setUrl] = useState('http://192.168.1.');
  const [type, setType] = useState<'moonraker' | 'bambu'>('moonraker');
  const [bambuIp, setBambuIp] = useState('');
  const [bambuSerial, setBambuSerial] = useState('');
  const [bambuCode, setBambuCode] = useState('');
  const [discovered, setDiscovered] = useState<{ name?: string; url: string }[]>([]);
  const [scanning, setScanning] = useState(false);

  const discover = async () => {
    setScanning(true);
    try {
      const res = await getApi<{ found?: { name?: string; url: string }[] }>('/api/printers/discover');
      setDiscovered(res.found || []);
      onToast(`${(res.found || []).length} Drucker gefunden`);
    } catch (e) {
      onToast(`Scan fehlgeschlagen: ${(e as Error).message}`, true);
    } finally {
      setScanning(false);
    }
  };

  const testConn = async () => {
    try {
      const res = await postApi<{ ok?: boolean; info?: string; error?: string }>('/api/printers/test', {
        printer_type: type,
        url,
        bambu_ip: bambuIp,
        bambu_serial: bambuSerial,
        bambu_access_code: bambuCode,
      });
      if (res.ok) onToast('Verbindung erfolgreich!');
      else onToast(res.error || 'Keine Verbindung', true);
    } catch (e) {
      onToast(`Test fehlgeschlagen: ${(e as Error).message}`, true);
    }
  };

  const addPrinter = async () => {
    if (!name.trim()) {
      onToast('Bitte einen Druckernamen angeben', true);
      return;
    }
    try {
      await postApi('/api/printers/add', {
        name: name.trim(),
        printer_type: type,
        url: type === 'moonraker' ? url.trim() : '',
        bambu_ip: type === 'bambu' ? bambuIp.trim() : '',
        bambu_serial: type === 'bambu' ? bambuSerial.trim() : '',
        bambu_access_code: type === 'bambu' ? bambuCode.trim() : '',
      });
      onToast('Drucker hinzugefügt');
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
          <div style={{ fontWeight: 700, fontSize: 16 }}>Drucker hinzufügen</div>
          <button className="btn" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          <div className="btn-row">
            <button className="btn" onClick={discover} disabled={scanning}>
              <Search size={14} /> {scanning ? 'Scanne Netzwerk…' : 'Netzwerk scannen'}
            </button>
          </div>

          {discovered.length > 0 && (
            <div className="btn-row">
              {discovered.map((d, i) => (
                <button
                  key={i}
                  className="btn"
                  onClick={() => {
                    setType('moonraker');
                    setUrl(d.url);
                    if (!name) setName(d.name || 'Klipper Drucker');
                  }}
                >
                  {d.name || d.url}
                </button>
              ))}
            </div>
          )}

          <div className="form-grid">
            <div>
              <label className="field-label">Name</label>
              <input
                className="input"
                placeholder="z. B. Voron 2.4"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <label className="field-label">Typ</label>
              <select
                className="select"
                value={type}
                onChange={(e) => setType(e.target.value as 'moonraker' | 'bambu')}
              >
                <option value="moonraker">Klipper / Moonraker</option>
                <option value="bambu">Bambu Lab (LAN)</option>
              </select>
            </div>
          </div>

          {type === 'moonraker' ? (
            <div>
              <label className="field-label">Moonraker URL</label>
              <input
                className="input"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="http://192.168.1.50:7125"
              />
            </div>
          ) : (
            <div className="form-grid">
              <div>
                <label className="field-label">Bambu IP</label>
                <input className="input" value={bambuIp} onChange={(e) => setBambuIp(e.target.value)} />
              </div>
              <div>
                <label className="field-label">Serial</label>
                <input
                  className="input"
                  value={bambuSerial}
                  onChange={(e) => setBambuSerial(e.target.value)}
                />
              </div>
              <div>
                <label className="field-label">LAN Access Code</label>
                <input
                  className="input"
                  value={bambuCode}
                  onChange={(e) => setBambuCode(e.target.value)}
                />
              </div>
            </div>
          )}

          <div className="btn-row" style={{ justifyContent: 'flex-end' }}>
            <button className="btn" onClick={testConn}>
              <CheckCircle2 size={14} /> Verbindung testen
            </button>
            <button className="btn btn-primary" onClick={addPrinter}>
              Speichern
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
