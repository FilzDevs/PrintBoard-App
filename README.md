# PrintBoard

Multi-printer fleet dashboard and control center for **Klipper / Moonraker** (Fluidd / Mainsail) and **Bambu Lab** (LAN MQTT) 3D printers.

## Architecture

PrintBoard provides three runtime modes from a single codebase:

1. **Native Desktop (`printboard`)** — Standalone PySide6 desktop application with direct printer polling, multi-camera matrix, built-in 3D model browser with persistent cookies, local 3D model library, Spoolman filament management, print queue, and maintenance tracking.
2. **Central Server & WebGUI (`printboard-server`)** — Background fleet polling service with Discord/Telegram webhook notifications and a responsive React WebGUI (Dark & Light themes) served on port `8080`.
3. **Remote Desktop Client (`printboard-client`)** — Lightweight PySide6 client that connects to a running `printboard-server` instance over LAN/WAN.

## Features

- **Klipper & Bambu Lab Support**: Unified status monitoring, temperature telemetry, progress gauges, and control actions.
- **Spoolman Integration**: Full filament, vendor, and spool management with color swatches, weight tracking, and slot assignment.
- **Print Queue & Batch Dispatcher**: Queue G-code jobs with copy counts and dispatch them to available printers.
- **Maintenance Tracker**: Automatically tracks cumulative operating hours from Moonraker history and monitors component wear intervals.
- **Cost & History Analytics**: Calculates filament usage, print time, electricity, and material costs across the fleet.
- **Multi-Camera & Display Matrix**: Simultaneous view of all configured printer webcams and HTTP displays with visibility filtering.
- **Command Palette (`Ctrl+K`)**: Quick keyboard launcher for navigation, preheating, and theme switching (`Obsidian Cyber`, `Graphite Studio`, `Daylight Clean`).

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
# Standalone desktop application
printboard

# Central server + WebGUI (http://localhost:8080)
printboard-server

# Remote desktop client
printboard-client
```

## Testing

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT
