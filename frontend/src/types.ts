export interface Printer {
  id: string;
  name: string;
  url: string;
  printer_type?: string;
  bambu_ip?: string;
  bambu_serial?: string;
  webcam_url?: string;
  is_sim?: boolean;
}

export interface PrinterStatus {
  state: string;
  filename?: string;
  progress?: number;
  print_duration?: number;
  total_duration?: number;
  eta_seconds?: number;
  nozzle_temp?: number;
  nozzle_target?: number;
  bed_temp?: number;
  bed_target?: number;
  chamber_temp?: number;
  fan_speed?: number;
  speed_factor?: number;
  flow_factor?: number;
  current_layer?: number;
  total_layers?: number;
  filament_used_mm?: number;
  error?: string;
  thumbnail?: string;
}

export interface TempPoint {
  t: number;
  nozzle?: number;
  bed?: number;
  nozzle_target?: number;
  bed_target?: number;
}

export interface Spool {
  id: number;
  remaining_weight?: number;
  initial_weight?: number;
  location?: string;
  lot_nr?: string;
  comment?: string;
  filament?: {
    id?: number;
    name?: string;
    material?: string;
    color_hex?: string;
    price?: number;
    vendor?: { id?: number; name?: string };
  };
}

export interface QueueItem {
  id: string;
  filename: string;
  printer_id?: string;
  material?: string;
  priority?: number;
  added_at?: string;
}

export interface MaintTask {
  key: string;
  title: string;
  interval_h: number;
  builtin?: boolean;
}

export interface DryingPreset {
  material: string;
  temp_c: number;
  hours: number;
  max_temp_c: number;
  humidity_target: string;
  notes: string;
}

export interface DryingTimer {
  id: string;
  material: string;
  temp_c: number;
  duration_h: number;
  started_at: number;
  ends_at: number;
}

export interface CostRates {
  eur_kg: number;
  kwh: number;
  watts: number;
  wear: number;
  labor_h: number;
  margin_pct: number;
  fail_pct: number;
  vat_pct: number;
}

export interface AppState {
  mode: 'easy' | 'advanced';
  theme: string;
  controls_enabled: boolean;
  sim_enabled: boolean;
  auto_dispatch: boolean;
  autostart: boolean;
  is_desktop: boolean;
  printers: Printer[];
  statuses: Record<string, PrinterStatus>;
  temp_history: Record<string, TempPoint[]>;
  spools: Spool[];
  filaments: NonNullable<Spool['filament']>[];
  vendors: { id: number; name: string; empty_spool_weight?: number }[];
  locations: string[];
  materials: string[];
  spoolman_url: string;
  spoolman_connected: boolean;
  drying_presets: DryingPreset[];
  drying_timers: DryingTimer[];
  queue: QueueItem[];
  maintenance: Record<string, Record<string, number>>;
  maintenance_tasks: MaintTask[];
  printer_hours: Record<string, number>;
  models_dir: string;
  slicer_cmd: string;
  detected_slicers: { name: string; cmd: string }[];
  notify_cfg: Record<string, unknown>;
  cost_rates: CostRates;
}

export interface PrinterDetails {
  files: { path?: string; filename?: string; size?: number; modified?: number }[];
  macros: string[];
  console: { message: string; time?: number; type?: string }[];
}
