package app.printboard.mobile;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.NetworkInterface;
import java.net.Socket;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public class ApiClient {
    private static final int TIMEOUT_MS = 4500;
    private static final Map<String, Bitmap> THUMB_CACHE = Collections.synchronizedMap(new HashMap<>());

    private static HttpURLConnection openConn(Models.Printer p, String path, String method, String contentType, int timeoutMs) throws Exception {
        URL u = new URL(p.getBaseUrl() + path);
        HttpURLConnection c = (HttpURLConnection) u.openConnection();
        c.setRequestMethod(method);
        c.setConnectTimeout(timeoutMs);
        c.setReadTimeout(timeoutMs);
        c.setRequestProperty("Accept", "application/json");
        c.setRequestProperty("User-Agent", "PrintBoard-Android/1.0");
        if (contentType != null) {
            c.setRequestProperty("Content-Type", contentType);
        }
        if (p.token != null && !p.token.trim().isEmpty()) {
            c.setRequestProperty("X-Api-Key", p.token.trim());
            c.setRequestProperty("Authorization", "Bearer " + p.token.trim());
        }
        return c;
    }

    private static byte[] readStream(InputStream is, int maxBytes) throws Exception {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        int n;
        int total = 0;
        while ((n = is.read(buf)) != -1) {
            bos.write(buf, 0, n);
            total += n;
            if (total >= maxBytes) break;
        }
        return bos.toByteArray();
    }

    public static JSONObject getJson(Models.Printer p, String path, int timeoutMs) throws Exception {
        HttpURLConnection c = openConn(p, path, "GET", null, timeoutMs);
        try {
            int code = c.getResponseCode();
            InputStream is = (code >= 200 && code < 300) ? c.getInputStream() : c.getErrorStream();
            String raw = is != null ? new String(readStream(is, 4 * 1024 * 1024), StandardCharsets.UTF_8) : "{}";
            if (code < 200 || code >= 300) {
                throw new RuntimeException("HTTP " + code + ": " + raw);
            }
            JSONObject j = new JSONObject(raw);
            if (j.has("error")) {
                throw new RuntimeException(j.get("error").toString());
            }
            if (j.has("result") && j.get("result") instanceof JSONObject) {
                return j.getJSONObject("result");
            }
            return j;
        } finally {
            c.disconnect();
        }
    }

    public static byte[] getBytes(Models.Printer p, String path, int timeoutMs) throws Exception {
        HttpURLConnection c = openConn(p, path, "GET", null, timeoutMs);
        try {
            int code = c.getResponseCode();
            if (code < 200 || code >= 300) {
                throw new RuntimeException("HTTP " + code);
            }
            try (InputStream is = c.getInputStream()) {
                return readStream(is, 10 * 1024 * 1024);
            }
        } finally {
            c.disconnect();
        }
    }

    public static JSONObject postJson(Models.Printer p, String path, JSONObject data, int timeoutMs) throws Exception {
        HttpURLConnection c = openConn(p, path, "POST", "application/json", timeoutMs);
        c.setDoOutput(true);
        try {
            byte[] body = (data != null ? data.toString() : "{}").getBytes(StandardCharsets.UTF_8);
            try (OutputStream os = c.getOutputStream()) {
                os.write(body);
            }
            int code = c.getResponseCode();
            InputStream is = (code >= 200 && code < 300) ? c.getInputStream() : c.getErrorStream();
            String raw = is != null ? new String(readStream(is, 2 * 1024 * 1024), StandardCharsets.UTF_8) : "{}";
            if (code < 200 || code >= 300) {
                throw new RuntimeException("HTTP " + code + ": " + raw);
            }
            return raw.trim().isEmpty() ? new JSONObject() : new JSONObject(raw);
        } finally {
            c.disconnect();
        }
    }

    public static JSONObject deleteRequest(Models.Printer p, String path, int timeoutMs) throws Exception {
        HttpURLConnection c = openConn(p, path, "DELETE", null, timeoutMs);
        try {
            int code = c.getResponseCode();
            InputStream is = (code >= 200 && code < 300) ? c.getInputStream() : c.getErrorStream();
            String raw = is != null ? new String(readStream(is, 2 * 1024 * 1024), StandardCharsets.UTF_8) : "{}";
            if (code < 200 || code >= 300) {
                throw new RuntimeException("HTTP " + code + ": " + raw);
            }
            return raw.trim().isEmpty() ? new JSONObject() : new JSONObject(raw);
        } finally {
            c.disconnect();
        }
    }

    public static Models.PrinterStatus fetchStatus(Models.Printer p) {
        Models.PrinterStatus st = new Models.PrinterStatus();
        try {
            JSONObject listRes = getJson(p, "/printer/objects/list", TIMEOUT_MS);
            JSONArray objsArr = listRes.optJSONArray("objects");
            List<String> objs = new ArrayList<>();
            if (objsArr != null) {
                for (int i = 0; i < objsArr.length(); i++) {
                    objs.add(objsArr.getString(i));
                }
            }

            List<String> heaters = new ArrayList<>();
            List<String> sensors = new ArrayList<>();
            for (String o : objs) {
                if ("heater_bed".equals(o) || o.startsWith("extruder") || o.startsWith("heater_generic ")) {
                    heaters.add(o);
                } else if (o.startsWith("temperature_sensor ")) {
                    sensors.add(o);
                }
            }

            String[] candidates = new String[]{"print_stats", "display_status", "virtual_sdcard", "toolhead", "gcode_move", "fan", "print_task_config"};
            List<String> queryParts = new ArrayList<>();
            for (String w : candidates) {
                if (objs.contains(w)) {
                    queryParts.add(URLEncoder.encode(w, "UTF-8").replace("+", "%20"));
                }
            }
            for (String h : heaters) {
                queryParts.add(URLEncoder.encode(h, "UTF-8").replace("+", "%20"));
            }
            for (String s : sensors) {
                queryParts.add(URLEncoder.encode(s, "UTF-8").replace("+", "%20"));
            }

            StringBuilder q = new StringBuilder();
            for (int i = 0; i < queryParts.size(); i++) {
                if (i > 0) q.append("&");
                q.append(queryParts.get(i));
            }

            JSONObject statusRoot = getJson(p, "/printer/objects/query?" + q, TIMEOUT_MS);
            JSONObject status = statusRoot.optJSONObject("status");
            if (status == null) status = statusRoot;

            JSONObject ps = status.optJSONObject("print_stats");
            JSONObject ds = status.optJSONObject("display_status");
            JSONObject vs = status.optJSONObject("virtual_sdcard");
            JSONObject th = status.optJSONObject("toolhead");
            JSONObject gm = status.optJSONObject("gcode_move");
            JSONObject fn = status.optJSONObject("fan");
            JSONObject ptc = status.optJSONObject("print_task_config");

            st.online = true;
            st.state = ps != null ? ps.optString("state", "standby") : "standby";
            st.filename = ps != null ? ps.optString("filename", "") : "";
            st.duration = ps != null ? ps.optDouble("print_duration", 0.0) : 0.0;

            double prog = 0.0;
            if (ds != null && !ds.isNull("progress")) {
                prog = ds.optDouble("progress", 0.0);
            } else if (vs != null && !vs.isNull("progress")) {
                prog = vs.optDouble("progress", 0.0);
            }
            st.progress = Math.max(0.0, Math.min(1.0, prog));
            if ("printing".equals(st.state) && st.progress > 0.01) {
                st.remaining = st.duration * (1.0 - st.progress) / st.progress;
            } else {
                st.remaining = -1.0;
            }

            st.heaters = heaters;
            List<String> allTempObjs = new ArrayList<>(heaters);
            allTempObjs.addAll(sensors);
            for (String o : allTempObjs) {
                JSONObject d = status.optJSONObject(o);
                if (d == null) continue;
                String label = o;
                if ("heater_bed".equals(o)) label = "Bett";
                else if ("extruder".equals(o)) label = "Düse";
                else label = o.replace("heater_generic ", "").replace("temperature_sensor ", "");
                double temp = d.optDouble("temperature", Double.NaN);
                double target = d.optDouble("target", Double.NaN);
                st.temps.add(new Models.TempReading(label, temp, target, o));
            }

            try {
                JSONObject info = getJson(p, "/printer/info", 2500);
                st.klipper = info.optString("state", "ready");
            } catch (Exception e) {
                st.klipper = "ready";
            }

            if (th != null) {
                st.homed = th.optString("homed_axes", "");
                st.activeExtruder = th.optString("extruder", "extruder");
                JSONArray posArr = th.optJSONArray("position");
                if (posArr != null && posArr.length() >= 3) {
                    st.position = new double[]{posArr.optDouble(0, 0), posArr.optDouble(1, 0), posArr.optDouble(2, 0)};
                }
            }
            if (gm != null) {
                JSONArray ho = gm.optJSONArray("homing_origin");
                if (ho != null && ho.length() >= 3) {
                    st.zOffset = ho.optDouble(2, 0.0);
                }
            }
            if (fn != null) {
                st.fanSpeed = fn.optDouble("speed", 0.0);
            }

            if (ptc != null) {
                JSONArray sids = ptc.optJSONArray("filament_spool_id");
                if (sids != null) {
                    for (int i = 0; i < sids.length(); i++) {
                        int val = sids.optInt(i, 0);
                        st.slotSpoolIds.add(val > 0 ? val : null);
                    }
                }
            }
            int extIdx = 0;
            if (st.activeExtruder != null && st.activeExtruder.startsWith("extruder") && st.activeExtruder.length() > 8) {
                try {
                    extIdx = Integer.parseInt(st.activeExtruder.substring(8));
                } catch (Exception ignored) {
                }
            }
            if (extIdx >= 0 && extIdx < st.slotSpoolIds.size()) {
                st.activeSpoolId = st.slotSpoolIds.get(extIdx);
            }

            if (st.filename != null && !st.filename.isEmpty()) {
                st.thumbnail = fetchThumbnail(p, st.filename);
            }
        } catch (Exception e) {
            st.online = false;
            st.error = e.getMessage() != null ? e.getMessage() : e.toString();
        }
        return st;
    }

    public static Bitmap fetchThumbnail(Models.Printer p, String filename) {
        if (filename == null || filename.isEmpty()) return null;
        String key = p.id + "::" + filename;
        if (THUMB_CACHE.containsKey(key)) {
            return THUMB_CACHE.get(key);
        }
        try {
            String encFile = URLEncoder.encode(filename, "UTF-8").replace("+", "%20");
            JSONObject meta = getJson(p, "/server/files/metadata?filename=" + encFile, 3500);
            JSONArray thumbs = meta.optJSONArray("thumbnails");
            if (thumbs == null || thumbs.length() == 0) {
                THUMB_CACHE.put(key, null);
                return null;
            }
            JSONObject best = null;
            int bestScore = -1;
            for (int i = 0; i < thumbs.length(); i++) {
                JSONObject t = thumbs.getJSONObject(i);
                int score = t.optInt("width", 0) * t.optInt("height", 0);
                if (score > bestScore) {
                    bestScore = score;
                    best = t;
                }
            }
            if (best == null) return null;
            String rel = best.optString("relative_path", "");
            if (rel.isEmpty()) return null;

            String fullRel = rel;
            int slash = filename.lastIndexOf('/');
            if (slash > 0) {
                fullRel = filename.substring(0, slash + 1) + rel;
            }
            String[] parts = fullRel.split("/");
            StringBuilder urlPath = new StringBuilder("/server/files/gcodes");
            for (String part : parts) {
                if (!part.isEmpty()) {
                    urlPath.append("/").append(URLEncoder.encode(part, "UTF-8").replace("+", "%20"));
                }
            }
            byte[] bytes = getBytes(p, urlPath.toString(), 4500);
            Bitmap bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.length);
            THUMB_CACHE.put(key, bmp);
            return bmp;
        } catch (Exception e) {
            return null;
        }
    }

    public static boolean probePort(String host, int port, int timeoutMs) {
        try (Socket s = new Socket()) {
            s.connect(new InetSocketAddress(host, port), timeoutMs);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    public static List<Models.WebcamItem> printerWebcams(Models.Printer p) {
        List<Models.WebcamItem> cams = new ArrayList<>();
        try {
            JSONObject res = getJson(p, "/server/webcams/list", 3000);
            JSONArray wlist = res.optJSONArray("webcams");
            if (wlist != null) {
                for (int i = 0; i < wlist.length(); i++) {
                    JSONObject w = wlist.getJSONObject(i);
                    String u = w.optString("stream_url", "");
                    if (u.isEmpty()) u = w.optString("snapshot_url", "");
                    if (!u.isEmpty()) {
                        String fullUrl = u.startsWith("http") ? u : p.getBaseUrl() + (u.startsWith("/") ? u : "/" + u);
                        String name = w.optString("name", p.name);
                        String service = w.optString("service", "");
                        if (fullUrl.endsWith("/webrtc")) {
                            fullUrl = fullUrl.substring(0, fullUrl.length() - 6) + "player";
                            service = "iframe";
                        }
                        cams.add(new Models.WebcamItem(p.name, name, fullUrl, service));
                    }
                }
            }
        } catch (Exception ignored) {
        }

        String displayUrl = p.displayUrl != null ? p.displayUrl.trim() : "";
        if (displayUrl.isEmpty() && probePort(p.host, 18080, 450)) {
            displayUrl = "http://" + p.host + ":18080/";
        }
        if (!displayUrl.isEmpty()) {
            boolean hasDisplay = false;
            for (Models.WebcamItem c : cams) {
                String cu = c.url.replaceAll("/+$", "");
                String cn = c.name.toLowerCase(Locale.ROOT);
                if (cu.endsWith(":18080") || cu.endsWith("/screen") || cu.endsWith("/gui")
                        || cn.equals("gui") || cn.equals("screen") || cn.equals("display")) {
                    hasDisplay = true;
                    break;
                }
            }
            if (!hasDisplay) {
                cams.add(new Models.WebcamItem(p.name, "Display", displayUrl, "iframe"));
            }
        }

        for (Models.WebcamItem c : cams) {
            if (cams.size() > 1 || !c.name.equals(p.name)) {
                String prefix = p.name + " · ";
                if (!c.name.startsWith(prefix)) {
                    c.name = prefix + c.name;
                }
            }
        }
        return cams;
    }

    public static List<Models.WebcamItem> allWebcams(List<Models.Printer> printers) {
        List<Models.WebcamItem> result = new ArrayList<>();
        if (printers == null || printers.isEmpty()) return result;
        ExecutorService ex = Executors.newFixedThreadPool(Math.min(printers.size(), 6));
        try {
            List<Future<List<Models.WebcamItem>>> futs = new ArrayList<>();
            for (Models.Printer p : printers) {
                futs.add(ex.submit(() -> printerWebcams(p)));
            }
            for (Future<List<Models.WebcamItem>> f : futs) {
                try {
                    result.addAll(f.get());
                } catch (Exception ignored) {
                }
            }
        } finally {
            ex.shutdown();
        }
        return result;
    }

    public static JSONObject sendGcode(Models.Printer p, String script) throws Exception {
        JSONObject body = new JSONObject();
        body.put("script", script);
        return postJson(p, "/printer/gcode/script", body, 25000);
    }

    public static JSONObject controlAction(Models.Printer p, String action) throws Exception {
        if ("pause".equals(action) || "resume".equals(action) || "cancel".equals(action)) {
            return postJson(p, "/printer/print/" + action, new JSONObject(), 15000);
        }
        if ("emergency_stop".equals(action) || "firmware_restart".equals(action) || "restart".equals(action)) {
            return postJson(p, "/printer/" + action, new JSONObject(), 15000);
        }
        throw new IllegalArgumentException("Unbekannte Aktion: " + action);
    }

    public static JSONObject setHeaterTemp(Models.Printer p, String heater, double target) throws Exception {
        String name = heater.replace("heater_generic ", "").trim();
        return sendGcode(p, String.format(Locale.US, "SET_HEATER_TEMPERATURE HEATER=%s TARGET=%.0f", name, target));
    }

    public static JSONObject setFanPercent(Models.Printer p, int percent) throws Exception {
        int s = Math.max(0, Math.min(255, Math.round(percent * 2.55f)));
        return sendGcode(p, "M106 S" + s);
    }

    public static JSONObject homeAxes(Models.Printer p, String axes) throws Exception {
        String a = axes == null ? "" : axes.trim().toUpperCase(Locale.ROOT);
        return sendGcode(p, ("G28 " + a).trim());
    }

    public static JSONObject jogAxis(Models.Printer p, String axis, double dist, int speed) throws Exception {
        String ax = axis.toUpperCase(Locale.ROOT);
        String cmd = String.format(Locale.US, "G91\nG1 %s%+.2f F%d\nG90", ax, dist, speed);
        return sendGcode(p, cmd);
    }

    public static JSONObject adjustZOffset(Models.Printer p, double delta, boolean reset) throws Exception {
        if (reset) {
            return sendGcode(p, "SET_GCODE_OFFSET Z=0 MOVE=1");
        }
        return sendGcode(p, String.format(Locale.US, "SET_GCODE_OFFSET Z_ADJUST=%+.3f MOVE=1", delta));
    }

    public static List<String> listMacros(Models.Printer p) throws Exception {
        JSONObject res = getJson(p, "/printer/objects/list", TIMEOUT_MS);
        JSONArray arr = res.optJSONArray("objects");
        List<String> macros = new ArrayList<>();
        if (arr != null) {
            for (int i = 0; i < arr.length(); i++) {
                String o = arr.getString(i);
                if (o.startsWith("gcode_macro ")) {
                    String m = o.substring(12);
                    if (!m.startsWith("_")) macros.add(m);
                }
            }
        }
        Collections.sort(macros);
        return macros;
    }

    public static List<Models.RemoteFile> listRemoteFiles(Models.Printer p) throws Exception {
        HttpURLConnection c = openConn(p, "/server/files/list?root=gcodes", "GET", null, 6000);
        try {
            int code = c.getResponseCode();
            InputStream is = (code >= 200 && code < 300) ? c.getInputStream() : c.getErrorStream();
            String raw = is != null ? new String(readStream(is, 4 * 1024 * 1024), StandardCharsets.UTF_8) : "{}";
            JSONObject j = new JSONObject(raw);
            JSONArray files = null;
            if (j.opt("result") instanceof JSONArray) {
                files = j.getJSONArray("result");
            } else if (j.opt("result") instanceof JSONObject) {
                files = j.getJSONObject("result").optJSONArray("files");
            } else if (j.has("files")) {
                files = j.optJSONArray("files");
            }
            List<Models.RemoteFile> out = new ArrayList<>();
            if (files != null) {
                for (int i = 0; i < files.length(); i++) {
                    JSONObject f = files.getJSONObject(i);
                    out.add(new Models.RemoteFile(
                        f.optString("path", ""),
                        f.optLong("size", 0),
                        (long) f.optDouble("modified", 0)
                    ));
                }
            }
            out.sort((a, b) -> Long.compare(b.modified, a.modified));
            return out;
        } finally {
            c.disconnect();
        }
    }

    public static JSONObject startPrint(Models.Printer p, String filename) throws Exception {
        JSONObject b = new JSONObject();
        b.put("filename", filename);
        return postJson(p, "/printer/print/start", b, 15000);
    }

    public static JSONObject deleteRemoteFile(Models.Printer p, String filename) throws Exception {
        String[] parts = filename.split("/");
        StringBuilder path = new StringBuilder("/server/files/gcodes");
        for (String part : parts) {
            if (!part.isEmpty()) {
                path.append("/").append(URLEncoder.encode(part, "UTF-8").replace("+", "%20"));
            }
        }
        return deleteRequest(p, path.toString(), 15000);
    }

    public static JSONObject uploadGcodeBytes(Models.Printer p, String filename, byte[] fileBytes, boolean startNow) throws Exception {
        String boundary = UUID.randomUUID().toString().replace("-", "");
        HttpURLConnection c = openConn(p, "/server/files/upload", "POST", "multipart/form-data; boundary=" + boundary, 60000);
        c.setDoOutput(true);
        try {
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            String head = "--" + boundary + "\r\nContent-Disposition: form-data; name=\"root\"\r\n\r\ngcodes\r\n"
                    + "--" + boundary + "\r\nContent-Disposition: form-data; name=\"print\"\r\n\r\n" + (startNow ? "true" : "false") + "\r\n"
                    + "--" + boundary + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"" + filename + "\"\r\n"
                    + "Content-Type: application/octet-stream\r\n\r\n";
            bos.write(head.getBytes(StandardCharsets.UTF_8));
            bos.write(fileBytes);
            bos.write(("\r\n--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8));

            try (OutputStream os = c.getOutputStream()) {
                os.write(bos.toByteArray());
            }
            int code = c.getResponseCode();
            InputStream is = (code >= 200 && code < 300) ? c.getInputStream() : c.getErrorStream();
            String raw = is != null ? new String(readStream(is, 2 * 1024 * 1024), StandardCharsets.UTF_8) : "{}";
            if (code < 200 || code >= 300) {
                throw new RuntimeException("Upload HTTP " + code + ": " + raw);
            }
            return new JSONObject(raw);
        } finally {
            c.disconnect();
        }
    }

    public static List<String> getGcodeStore(Models.Printer p, int count) throws Exception {
        JSONObject res = getJson(p, "/server/gcode_store?count=" + count, 5000);
        JSONArray arr = res.optJSONArray("gcode_store");
        List<String> lines = new ArrayList<>();
        if (arr != null) {
            java.text.SimpleDateFormat sdf = new java.text.SimpleDateFormat("HH:mm:ss", Locale.getDefault());
            for (int i = 0; i < arr.length(); i++) {
                JSONObject item = arr.getJSONObject(i);
                long t = (long) (item.optDouble("time", 0) * 1000);
                String ts = t > 0 ? sdf.format(new java.util.Date(t)) : "";
                String prefix = "command".equals(item.optString("type")) ? ">> " : "   ";
                lines.add("[" + ts + "] " + prefix + item.optString("message", ""));
            }
        }
        return lines;
    }

    public static List<Models.PrintJob> getHistory(Models.Printer p, int limit) throws Exception {
        JSONObject res = getJson(p, "/server/history/list?limit=" + limit + "&order=desc", 6000);
        JSONArray jobs = res.optJSONArray("jobs");
        List<Models.PrintJob> out = new ArrayList<>();
        if (jobs != null) {
            for (int i = 0; i < jobs.length(); i++) {
                JSONObject j = jobs.getJSONObject(i);
                out.add(new Models.PrintJob(
                    j.optString("filename", ""),
                    j.optString("status", ""),
                    j.optDouble("total_duration", 0.0),
                    j.optDouble("filament_used", 0.0),
                    (long) j.optDouble("start_time", 0)
                ));
            }
        }
        return out;
    }

    public static List<Models.Printer> discoverPrinters() {
        List<String> prefixes = getLocalIpv4Prefixes();
        if (prefixes.isEmpty()) prefixes.add("192.168.178");

        ExecutorService ex = Executors.newFixedThreadPool(48);
        List<Future<Models.Printer>> futures = new ArrayList<>();
        for (String pref : prefixes) {
            for (int i = 1; i <= 254; i++) {
                final String ip = pref + "." + i;
                for (final int port : new int[]{80, 7125}) {
                    futures.add(ex.submit((Callable<Models.Printer>) () -> probeMoonraker(ip, port)));
                }
            }
        }
        Map<String, Models.Printer> byHost = new HashMap<>();
        for (Future<Models.Printer> f : futures) {
            try {
                Models.Printer found = f.get();
                if (found != null && !byHost.containsKey(found.host)) {
                    byHost.put(found.host, found);
                }
            } catch (Exception ignored) {
            }
        }
        ex.shutdown();
        List<Models.Printer> list = new ArrayList<>(byHost.values());
        list.sort((a, b) -> a.host.compareTo(b.host));
        return list;
    }

    private static Models.Printer probeMoonraker(String host, int port) {
        try {
            URL u = new URL("http://" + host + ":" + port + "/printer/info");
            HttpURLConnection c = (HttpURLConnection) u.openConnection();
            c.setConnectTimeout(550);
            c.setReadTimeout(550);
            c.setRequestProperty("Accept", "application/json");
            try {
                if (c.getResponseCode() == 200) {
                    String raw = new String(readStream(c.getInputStream(), 65536), StandardCharsets.UTF_8);
                    JSONObject j = new JSONObject(raw);
                    JSONObject res = j.optJSONObject("result");
                    if (res == null) res = j;
                    if (res.has("state") || res.has("hostname") || res.has("software_version")) {
                        String name = res.optString("hostname", "Klipper (" + host + ")");
                        return new Models.Printer("", name, host, port, "", false, "");
                    }
                }
            } finally {
                c.disconnect();
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    private static List<String> getLocalIpv4Prefixes() {
        List<String> out = new ArrayList<>();
        try {
            Enumeration<NetworkInterface> ifaces = NetworkInterface.getNetworkInterfaces();
            while (ifaces != null && ifaces.hasMoreElements()) {
                NetworkInterface nif = ifaces.nextElement();
                if (nif.isLoopback() || !nif.isUp()) continue;
                Enumeration<InetAddress> addrs = nif.getInetAddresses();
                while (addrs.hasMoreElements()) {
                    InetAddress a = addrs.nextElement();
                    if (a instanceof Inet4Address && !a.isLoopbackAddress()) {
                        String ip = a.getHostAddress();
                        String[] parts = ip.split("\\.");
                        if (parts.length == 4) {
                            String pref = parts[0] + "." + parts[1] + "." + parts[2];
                            if (!out.contains(pref)) out.add(pref);
                        }
                    }
                }
            }
        } catch (Exception ignored) {
        }
        return out;
    }

    public static boolean sendDiscordWebhook(String webhookUrl, String text) throws Exception {
        if (webhookUrl == null || webhookUrl.trim().isEmpty()) {
            throw new IllegalArgumentException("Keine Discord Webhook-URL angegeben.");
        }
        URL u = new URL(webhookUrl.trim());
        HttpURLConnection c = (HttpURLConnection) u.openConnection();
        c.setRequestMethod("POST");
        c.setConnectTimeout(8000);
        c.setReadTimeout(8000);
        c.setRequestProperty("Content-Type", "application/json");
        c.setRequestProperty("User-Agent", "PrintBoard-Android/1.0");
        c.setDoOutput(true);
        try {
            JSONObject payload = new JSONObject();
            payload.put("content", text);
            try (OutputStream os = c.getOutputStream()) {
                os.write(payload.toString().getBytes(StandardCharsets.UTF_8));
            }
            int code = c.getResponseCode();
            if (code != 200 && code != 204) {
                throw new RuntimeException("Discord antwortete mit HTTP " + code);
            }
            return true;
        } finally {
            c.disconnect();
        }
    }

    public static void sendTelegram(String token, String chatId, String text) throws Exception {
        if (token == null || token.isEmpty() || chatId == null || chatId.isEmpty()) return;
        URL u = new URL("https://api.telegram.org/bot" + token.trim() + "/sendMessage");
        HttpURLConnection c = (HttpURLConnection) u.openConnection();
        c.setRequestMethod("POST");
        c.setConnectTimeout(8000);
        c.setReadTimeout(8000);
        c.setRequestProperty("Content-Type", "application/x-www-form-urlencoded");
        c.setDoOutput(true);
        try {
            String body = "chat_id=" + URLEncoder.encode(chatId.trim(), "UTF-8")
                    + "&text=" + URLEncoder.encode(text, "UTF-8");
            try (OutputStream os = c.getOutputStream()) {
                os.write(body.getBytes(StandardCharsets.UTF_8));
            }
            c.getResponseCode();
        } finally {
            c.disconnect();
        }
    }
}
