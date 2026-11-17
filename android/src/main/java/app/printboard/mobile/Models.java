package app.printboard.mobile;

import android.graphics.Bitmap;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public class Models {

    public static class Printer {
        public String id;
        public String name;
        public String host;
        public int port = 80;
        public String token = "";
        public boolean tls = false;
        public String displayUrl = "";

        public Printer() {
            this.id = UUID.randomUUID().toString().substring(0, 8);
        }

        public Printer(String id, String name, String host, int port, String token, boolean tls, String displayUrl) {
            this.id = (id == null || id.isEmpty()) ? UUID.randomUUID().toString().substring(0, 8) : id;
            this.name = name;
            this.host = host;
            this.port = port;
            this.token = token == null ? "" : token;
            this.tls = tls;
            this.displayUrl = displayUrl == null ? "" : displayUrl;
        }

        public String getBaseUrl() {
            return (tls ? "https://" : "http://") + host + ":" + port;
        }
    }

    public static class TempReading {
        public String label;
        public double temperature;
        public double target;
        public String rawHeater;

        public TempReading(String label, double temperature, double target, String rawHeater) {
            this.label = label;
            this.temperature = temperature;
            this.target = target;
            this.rawHeater = rawHeater;
        }
    }

    public static class PrinterStatus {
        public boolean online = false;
        public String error = "";
        public String state = "standby";
        public String klipper = "ready";
        public String filename = "";
        public double progress = 0.0;
        public double duration = 0.0;
        public double remaining = -1.0;
        public List<TempReading> temps = new ArrayList<>();
        public List<String> heaters = new ArrayList<>();
        public String homed = "";
        public double[] position = new double[]{0.0, 0.0, 0.0};
        public double zOffset = 0.0;
        public double fanSpeed = 0.0;
        public Integer activeSpoolId = null;
        public List<Integer> slotSpoolIds = new ArrayList<>();
        public String activeExtruder = "extruder";
        public Bitmap thumbnail = null;
    }

    public static class WebcamItem {
        public String printer;
        public String name;
        public String url;
        public String service;

        public WebcamItem(String printer, String name, String url, String service) {
            this.printer = printer;
            this.name = name;
            this.url = url;
            this.service = service;
        }

        public String getKey() {
            return printer + "::" + name;
        }

        public boolean isDisplay() {
            String n = name != null ? name.toLowerCase() : "";
            String u = url != null ? url.toLowerCase() : "";
            String s = service != null ? service.toLowerCase() : "";
            return "iframe".equals(s) || u.contains(":18080") || u.contains("/screen") || n.contains("display") || n.contains("gui") || n.contains("screen");
        }
    }

    public static class RemoteFile {
        public String path;
        public long size;
        public long modified;

        public RemoteFile(String path, long size, long modified) {
            this.path = path;
            this.size = size;
            this.modified = modified;
        }
    }

    public static class PrintJob {
        public String filename;
        public String status;
        public double totalDuration;
        public double filamentUsedMm;
        public long startTime;

        public PrintJob(String filename, String status, double totalDuration, double filamentUsedMm, long startTime) {
            this.filename = filename;
            this.status = status;
            this.totalDuration = totalDuration;
            this.filamentUsedMm = filamentUsedMm;
            this.startTime = startTime;
        }
    }

    public static class Vendor {
        public int id;
        public String name = "";
        public Double emptySpoolWeight = null;
        public String externalId = "";
        public String comment = "";
    }

    public static class Filament {
        public int id;
        public String name = "";
        public Vendor vendor = null;
        public String material = "PLA";
        public String variant = "";
        public double density = 1.24;
        public double diameter = 1.75;
        public double weight = 1000.0;
        public Double spoolWeight = null;
        public Double price = null;
        public Integer extruderTemp = null;
        public Integer bedTemp = null;
        public String colorHex = "38BDF8";
        public String multiColorHexes = "";
        public String articleNumber = "";
        public String comment = "";

        public String[] getColors() {
            if (multiColorHexes != null && !multiColorHexes.trim().isEmpty()) {
                String[] parts = multiColorHexes.split(",");
                List<String> clean = new ArrayList<>();
                for (String p : parts) {
                    String s = p.trim().replace("#", "");
                    if (s.length() >= 6) clean.add("#" + s.substring(0, 6));
                }
                if (!clean.isEmpty()) return clean.toArray(new String[0]);
            }
            String c = colorHex != null ? colorHex.trim().replace("#", "") : "";
            if (c.length() >= 6) return new String[]{"#" + c.substring(0, 6)};
            return new String[]{"#38BDF8"};
        }

        public String getDisplayName() {
            String v = (vendor != null && vendor.name != null) ? vendor.name.trim() : "";
            String n = name != null ? name.trim() : "?";
            if (!v.isEmpty() && !n.toLowerCase().startsWith(v.toLowerCase())) {
                return v + " " + n;
            }
            return n;
        }
    }

    public static class Spool {
        public int id;
        public Filament filament = new Filament();
        public Double price = null;
        public double remainingWeight = 0.0;
        public double initialWeight = 1000.0;
        public Double spoolWeight = null;
        public double usedWeight = 0.0;
        public double remainingLength = 0.0;
        public double usedLength = 0.0;
        public String location = "";
        public String lotNr = "";
        public String comment = "";
        public boolean archived = false;
        public String cardUids = "";

        public double getEffectiveInitialWeight() {
            if (initialWeight > 0) return initialWeight;
            if (filament != null && filament.weight > 0) return filament.weight;
            if (remainingWeight + usedWeight > 0) return remainingWeight + usedWeight;
            return 1000.0;
        }

        public double getFillFraction() {
            double init = getEffectiveInitialWeight();
            if (init <= 0) return 0.0;
            return Math.max(0.0, Math.min(1.0, remainingWeight / init));
        }

        public Double getEffectivePrice() {
            if (price != null && price > 0) return price;
            if (filament != null && filament.price != null && filament.price > 0) return filament.price;
            return null;
        }

        public double getEffectiveTareWeight() {
            if (spoolWeight != null && spoolWeight > 0) return spoolWeight;
            if (filament != null && filament.spoolWeight != null && filament.spoolWeight > 0) return filament.spoolWeight;
            if (filament != null && filament.vendor != null && filament.vendor.emptySpoolWeight != null && filament.vendor.emptySpoolWeight > 0) {
                return filament.vendor.emptySpoolWeight;
            }
            return 200.0;
        }

        public String getDisplayName() {
            String fn = filament != null ? filament.getDisplayName() : "?";
            String mat = (filament != null && filament.material != null && !filament.material.isEmpty()) ? " [" + filament.material + "]" : "";
            return "#" + id + " " + fn + mat;
        }

        public String[] getColors() {
            return filament != null ? filament.getColors() : new String[]{"#38BDF8"};
        }
    }

    public static class ExternalFilament {
        public String id = "";
        public String manufacturer = "";
        public String name = "";
        public String material = "PLA";
        public double density = 1.24;
        public double diameter = 1.75;
        public double weight = 1000.0;
        public Double spoolWeight = null;
        public String colorHex = "38BDF8";
        public String multiColorHexes = "";
        public Integer extruderTemp = null;
        public Integer bedTemp = null;
    }

    public static class PrinterSlot {
        public int channel;
        public String label;
        public String extruder;
        public Integer spoolId;
        public boolean exist;
        public boolean active;
        public String type = "";
        public String vendor = "";
        public String colorHex = "#FFFFFF";
        public String cardUid = "";
    }

    public static class PrinterSpoolState {
        public String printerId;
        public String printerName;
        public boolean online = false;
        public Integer activeSpoolId = null;
        public String activeExtruder = "extruder";
        public List<PrinterSlot> slots = new ArrayList<>();
    }
}
