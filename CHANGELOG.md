# Changelog

Alle wichtigen Änderungen und neuen Funktionen von **PrintBoard Studio** werden in dieser Datei dokumentiert.

---

## [1.0.0] — PrintBoard Studio (Komplett-Neuaufbau & React WebUI)

### ✨ Neue Hauptfunktionen
- **Komplett neue WebUI (React + TypeScript + Vite)**
  - Modernes Glassmorphic-Bento-Design mit Echtzeit-Synchronisation, flüssigen Fortschritts-Ringen, Live-Temperaturkurven (`TempChart`) und Command Palette (`Ctrl+K`).
- **Easy Mode & Advanced Pro Mode**
  - **Easy Mode**: Aufgeräumte, übersichtliche Ansicht für den schnellen Alltagsbetrieb ohne Reizüberflutung.
  - **Advanced Pro Mode**: Erweiterte Flotten-Telemetrie inkl. Live-Temperatur-Verlaufsdiagrammen für Düse und Heizbett auf jeder Druckerkarte.
- **Multi-Plattform 3D-Modell Meta-Suche („Modelle finden“)**
  - Neue Extraseite (`DiscoverPage`) und Backend-Suchmaschine (`printboard/model_search.py`), die **alle 6 großen 3D-Modell-Plattformen gleichzeitig** durchsucht:
    1. **Printables** (Offizielle GraphQL-API mit Vorschaubildern, Likes, Downloads & Creator)
    2. **MakerWorld** (Offizielle Search-Service-API mit Cover-Bildern, Likes & Downloads)
    3. **Thingiverse** (Offizielle v2 REST-API mit automatischer JWT-View-Token-Authentifizierung & CloudFront-Vorschaubildern)
    4. **MyMiniFactory** (Offizielle JSON-Such-API mit Vorschaubildern, Aufrufen & Preisstatus)
    5. **Thangs** (Live-Modell- & Vorschaubild-Index für `thangs.com/designer/.../3d-model`)
    6. **Cults3D** (Live-Modell- & Vorschaubild-Index für `cults3d.com/en/3d-model`)
  - Plattform-Filter-Tabs mit Live-Trefferzählern, Sortierung (*Plattform-Mix, Meiste Downloads, Meiste Likes, Alphabetisch*), Trending-Suchchips (*Gridfinity, Voron, 3DBenchy, Bambu AMS, Spool Holder, Multiboard, Dummy 13*) und Direkt-Suchbuttons.
- **Angebots- & Verkaufspreis-Kalkulator (`CostsPage` & `costs.calculate_quote`)**
  - Berechnet aus Filamentgewicht, Druckzeit, Filamentpreis (`€/kg`), Strompreis (`€/kWh`), Leistungsaufnahme (`W`), Maschinenverschleiß, Rüstzeit, Fehldruck-Risiko und Gewinnmarge sofort Selbstkosten, Netto-Preis und Brutto-Angebot inkl. MwSt.
- **Spoolman & Filament-Trockner (`SpoolmanPage`)**
  - Vollständige Spoolman-Anbindung mit visuellen Farbbalken, Restgewicht-Anzeige in Gramm und Prozent sowie integriertem Filament-Trocknungs-Assistenten mit Material-Presets (*PLA, PETG, ABS/ASA, TPU, PA/Nylon, PC*) und aktiven Countdown-Timern.
- **Druck-Warteschlange (`QueuePage`) & Wartungs-Tracker (`MaintenancePage`)**
  - Einreihen und Starten von Druckjobs (inkl. Auto-Dispatch auf freie Drucker) sowie Überwachung von Verschleiß- und Wartungsintervallen nach Betriebsstunden.
- **Interaktive Demo-Flotte (`printboard/sim.py`)**
  - Realistischer Simulator (*Voron 2.4 R2 Pro*, *Bambu Lab X1 Carbon*, *RatRig V-Core 4 400*) mit thermischer PID-Physik, Fortschritt, Layern und Demo-Spulen (jederzeit in den Einstellungen an-/abschaltbar).

### 🔧 Verbesserungen & Fixes
- **Server & Caching (`printboard/server.py`)**: `Cache-Control: no-store, no-cache, must-revalidate` und `allow_reuse_address` ergänzt, damit Browser-Clients nach Updates sofort die neueste WebUI laden.
- **Telemetrie-Normalisierung**: Einheitliche Temperatur-, Layer- und Restzeit-Felder für Klipper/Moonraker, Bambu Lab (LAN MQTT) und Simulator-Drucker.
- **Vorschaubilder bei Thingiverse, Thangs & Cults3D**: Direkte CloudFront-Bild-Extraktion für Thingiverse sowie `no-referrer`-Unterstützung und Kontrast-Hintergründe für transparente CAD-Renderings.
