package app.printboard.mobile;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.reflect.Field;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class SpoolmanClient {
    private static final int TIMEOUT_MS = 6000;

    public static String normalizeUrl(String url) {
        if (url == null) return "";
        String u = url.trim().replaceAll("/+$", "");
        if (u.isEmpty()) return "";
        if (!u.startsWith("http://") && !u.startsWith("https://")) {
            u = "http://" + u;
        }
        if (u.endsWith("/api/v1")) {
            u = u.substring(0, u.length() - 7).replaceAll("/+$", "");
        } else if (u.endsWith("/api")) {
            u = u.substring(0, u.length() - 4).replaceAll("/+$", "");
        }
        return u;
    }

    private static byte[] readAll(InputStream is) throws Exception {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        int n;
        while ((n = is.read(buf)) != -1) {
            bos.write(buf, 0, n);
        }
        return bos.toByteArray();
    }

    private static String requestRaw(String baseUrl, String method, String path, JSONObject body, int timeoutMs) throws Exception {
        String base = normalizeUrl(baseUrl);
        if (base.isEmpty()) {
            throw new IllegalArgumentException("Keine Spoolman Server-URL konfiguriert.");
        }
        URL u = new URL(base + "/api/v1" + path);
        HttpURLConnection c = (HttpURLConnection) u.openConnection();
        c.setConnectTimeout(timeoutMs);
        c.setReadTimeout(timeoutMs);
        c.setRequestProperty("Accept", "application/json");
        c.setRequestProperty("User-Agent", "PrintBoard-Android/1.0");

        if ("PATCH".equals(method)) {
            try {
                c.setRequestMethod("PATCH");
            } catch (Exception e) {
                c.setRequestMethod("POST");
                c.setRequestProperty("X-HTTP-Method-Override", "PATCH");
                try {
                    Field mf = HttpURLConnection.class.getDeclaredField("method");
                    mf.setAccessible(true);
                    mf.set(c, "PATCH");
                } catch (Exception ignored) {
                }
            }
        } else {
            c.setRequestMethod(method);
        }

        if (body != null) {
            c.setRequestProperty("Content-Type", "application/json");
            c.setDoOutput(true);
            byte[] rawBody = body.toString().getBytes(StandardCharsets.UTF_8);
            try (OutputStream os = c.getOutputStream()) {
                os.write(rawBody);
            }
        }

        try {
            int code = c.getResponseCode();
            InputStream is = (code >= 200 && code < 300) ? c.getInputStream() : c.getErrorStream();
            String resp = is != null ? new String(readAll(is), StandardCharsets.UTF_8) : "";
            if (code < 200 || code >= 300) {
                throw new RuntimeException("Spoolman HTTP " + code + ": " + resp);
            }
            return resp;
        } finally {
            c.disconnect();
        }
    }

    public static String decodeExtraString(JSONObject extra, String key) {
        if (extra == null || !extra.has(key) || extra.isNull(key)) return "";
        String raw = extra.optString(key, "").trim();
        if (raw.startsWith("\"") && raw.endsWith("\"") && raw.length() >= 2) {
            raw = raw.substring(1, raw.length() - 1);
        }
        return raw;
    }

    public static Object encodeExtraString(String val) {
        if (val == null || val.trim().isEmpty()) return JSONObject.NULL;
        return JSONObject.quote(val.trim());
    }

    public static String formatCardUid(Object rawUid) {
        if (rawUid instanceof JSONArray) {
            JSONArray arr = (JSONArray) rawUid;
            if (arr.length() >= 4) {
                StringBuilder sb = new StringBuilder();
                for (int i = 0; i < arr.length(); i++) {
                    sb.append(String.format(Locale.US, "%02X", arr.optInt(i, 0) & 0xFF));
                }
                return sb.toString();
            }
        }
        if (rawUid instanceof String) {
            String s = ((String) rawUid).trim().replace("\"", "");
            if (!s.isEmpty() && !"0".equals(s)) return s.toUpperCase(Locale.ROOT);
        }
        return "";
    }

    // ---------- Server & Discovery ----------

    public static JSONObject getInfo(String baseUrl) throws Exception {
        return new JSONObject(requestRaw(baseUrl, "GET", "/info", null, 3500));
    }

    public static JSONObject triggerBackup(String baseUrl) throws Exception {
        return new JSONObject(requestRaw(baseUrl, "POST", "/backup", new JSONObject(), 10000));
    }

    public static String discoverUrl(List<Models.Printer> printers) {
        List<String> candidates = new ArrayList<>();
        if (printers != null) {
            for (Models.Printer p : printers) {
                try {
                    JSONObject cfgRoot = ApiClient.getJson(p, "/server/config", 2500);
                    JSONObject cfg = cfgRoot.optJSONObject("config");
                    if (cfg != null) {
                        for (String sec : new String[]{"spoolman", "spoollink"}) {
                            JSONObject s = cfg.optJSONObject(sec);
                            if (s != null) {
                                String srv = normalizeUrl(s.optString("server", ""));
                                if (!srv.isEmpty() && !candidates.contains(srv)) {
                                    candidates.add(srv);
                                }
                            }
                        }
                    }
                } catch (Exception ignored) {
                }
            }
        }
        if (!candidates.contains(AppConfig.DEFAULT_SPOOLMAN_URL)) {
            candidates.add(AppConfig.DEFAULT_SPOOLMAN_URL);
        }
        for (String cand : candidates) {
            try {
                JSONObject info = getInfo(cand);
                if (info.has("version")) return cand;
            } catch (Exception ignored) {
            }
        }
        return candidates.isEmpty() ? AppConfig.DEFAULT_SPOOLMAN_URL : candidates.get(0);
    }

    // ---------- Parsers ----------

    public static Models.Vendor parseVendor(JSONObject o) {
        if (o == null) return null;
        Models.Vendor v = new Models.Vendor();
        v.id = o.optInt("id", 0);
        v.name = o.optString("name", "");
        if (!o.isNull("empty_spool_weight")) {
            v.emptySpoolWeight = o.optDouble("empty_spool_weight", 0.0);
        }
        v.externalId = o.isNull("external_id") ? "" : o.optString("external_id", "");
        v.comment = o.isNull("comment") ? "" : o.optString("comment", "");
        return v;
    }

    public static Models.Filament parseFilament(JSONObject o) {
        if (o == null) return new Models.Filament();
        Models.Filament f = new Models.Filament();
        f.id = o.optInt("id", 0);
        f.name = o.isNull("name") ? "" : o.optString("name", "");
        f.vendor = parseVendor(o.optJSONObject("vendor"));
        f.material = o.isNull("material") ? "PLA" : o.optString("material", "PLA");
        f.density = o.optDouble("density", 1.24);
        f.diameter = o.optDouble("diameter", 1.75);
        f.weight = o.optDouble("weight", 1000.0);
        if (!o.isNull("spool_weight")) f.spoolWeight = o.optDouble("spool_weight");
        if (!o.isNull("price")) f.price = o.optDouble("price");
        if (!o.isNull("settings_extruder_temp")) f.extruderTemp = o.optInt("settings_extruder_temp");
        if (!o.isNull("settings_bed_temp")) f.bedTemp = o.optInt("settings_bed_temp");
        f.colorHex = o.isNull("color_hex") ? "" : o.optString("color_hex", "");
        f.multiColorHexes = o.isNull("multi_color_hexes") ? "" : o.optString("multi_color_hexes", "");
        f.articleNumber = o.isNull("article_number") ? "" : o.optString("article_number", "");
        f.comment = o.isNull("comment") ? "" : o.optString("comment", "");
        f.variant = decodeExtraString(o.optJSONObject("extra"), "variant");
        return f;
    }

    public static Models.Spool parseSpool(JSONObject o) {
        Models.Spool s = new Models.Spool();
        s.id = o.optInt("id", 0);
        s.filament = parseFilament(o.optJSONObject("filament"));
        if (!o.isNull("price")) s.price = o.optDouble("price");
        s.remainingWeight = o.optDouble("remaining_weight", 0.0);
        s.initialWeight = o.optDouble("initial_weight", s.filament != null ? s.filament.weight : 1000.0);
        if (!o.isNull("spool_weight")) s.spoolWeight = o.optDouble("spool_weight");
        s.usedWeight = o.optDouble("used_weight", 0.0);
        s.remainingLength = o.optDouble("remaining_length", 0.0);
        s.usedLength = o.optDouble("used_length", 0.0);
        s.location = o.isNull("location") ? "" : o.optString("location", "");
        s.lotNr = o.isNull("lot_nr") ? "" : o.optString("lot_nr", "");
        s.comment = o.isNull("comment") ? "" : o.optString("comment", "");
        s.archived = o.optBoolean("archived", false);
        s.cardUids = decodeExtraString(o.optJSONObject("extra"), "card_uids");
        return s;
    }

    // ---------- Spools CRUD ----------

    public static List<Models.Spool> listSpools(String baseUrl, boolean allowArchived) throws Exception {
        String raw = requestRaw(baseUrl, "GET", "/spool?allow_archived=" + (allowArchived ? "true" : "false"), null, TIMEOUT_MS);
        JSONArray arr = new JSONArray(raw);
        List<Models.Spool> list = new ArrayList<>();
        for (int i = 0; i < arr.length(); i++) {
            list.add(parseSpool(arr.getJSONObject(i)));
        }
        return list;
    }

    public static Models.Spool createSpool(String baseUrl, JSONObject payload) throws Exception {
        return parseSpool(new JSONObject(requestRaw(baseUrl, "POST", "/spool", payload, TIMEOUT_MS)));
    }

    public static Models.Spool updateSpool(String baseUrl, int spoolId, JSONObject payload) throws Exception {
        return parseSpool(new JSONObject(requestRaw(baseUrl, "PATCH", "/spool/" + spoolId, payload, TIMEOUT_MS)));
    }

    public static void deleteSpool(String baseUrl, int spoolId) throws Exception {
        requestRaw(baseUrl, "DELETE", "/spool/" + spoolId, null, TIMEOUT_MS);
    }

    public static Models.Spool measureSpool(String baseUrl, int spoolId, double grossWeight) throws Exception {
        JSONObject b = new JSONObject();
        b.put("weight", grossWeight);
        return parseSpool(new JSONObject(requestRaw(baseUrl, "PUT", "/spool/" + spoolId + "/measure", b, TIMEOUT_MS)));
    }

    public static Models.Spool useSpool(String baseUrl, int spoolId, Double useWeight, Double useLength) throws Exception {
        JSONObject b = new JSONObject();
        if (useWeight != null) b.put("use_weight", useWeight);
        else if (useLength != null) b.put("use_length", useLength);
        return parseSpool(new JSONObject(requestRaw(baseUrl, "PUT", "/spool/" + spoolId + "/use", b, TIMEOUT_MS)));
    }

    // ---------- Filaments CRUD ----------

    public static List<Models.Filament> listFilaments(String baseUrl) throws Exception {
        String raw = requestRaw(baseUrl, "GET", "/filament", null, TIMEOUT_MS);
        JSONArray arr = new JSONArray(raw);
        List<Models.Filament> list = new ArrayList<>();
        for (int i = 0; i < arr.length(); i++) {
            list.add(parseFilament(arr.getJSONObject(i)));
        }
        return list;
    }

    public static Models.Filament createFilament(String baseUrl, JSONObject payload) throws Exception {
        return parseFilament(new JSONObject(requestRaw(baseUrl, "POST", "/filament", payload, TIMEOUT_MS)));
    }

    public static Models.Filament updateFilament(String baseUrl, int filamentId, JSONObject payload) throws Exception {
        return parseFilament(new JSONObject(requestRaw(baseUrl, "PATCH", "/filament/" + filamentId, payload, TIMEOUT_MS)));
    }

    public static void deleteFilament(String baseUrl, int filamentId) throws Exception {
        requestRaw(baseUrl, "DELETE", "/filament/" + filamentId, null, TIMEOUT_MS);
    }

    // ---------- Vendors CRUD ----------

    public static List<Models.Vendor> listVendors(String baseUrl) throws Exception {
        String raw = requestRaw(baseUrl, "GET", "/vendor", null, TIMEOUT_MS);
        JSONArray arr = new JSONArray(raw);
        List<Models.Vendor> list = new ArrayList<>();
        for (int i = 0; i < arr.length(); i++) {
            list.add(parseVendor(arr.getJSONObject(i)));
        }
        return list;
    }

    public static Models.Vendor createVendor(String baseUrl, JSONObject payload) throws Exception {
        return parseVendor(new JSONObject(requestRaw(baseUrl, "POST", "/vendor", payload, TIMEOUT_MS)));
    }

    public static Models.Vendor updateVendor(String baseUrl, int vendorId, JSONObject payload) throws Exception {
        return parseVendor(new JSONObject(requestRaw(baseUrl, "PATCH", "/vendor/" + vendorId, payload, TIMEOUT_MS)));
    }

    public static void deleteVendor(String baseUrl, int vendorId) throws Exception {
        requestRaw(baseUrl, "DELETE", "/vendor/" + vendorId, null, TIMEOUT_MS);
    }

    // ---------- External SpoolmanDB Catalog ----------

    public static List<Models.ExternalFilament> searchExternalFilaments(String baseUrl, String query, int limit) throws Exception {
        String q = query != null ? query.trim() : "";
        String path;
        if (!q.isEmpty()) {
            path = "/external/filament/search?query=" + URLEncoder.encode(q, "UTF-8") + "&limit=" + Math.min(100, limit);
        } else {
            path = "/external/filament";
        }
        String raw = requestRaw(baseUrl, "GET", path, null, 8000);
        JSONArray arr = new JSONArray(raw);
        List<Models.ExternalFilament> out = new ArrayList<>();
        int max = Math.min(arr.length(), limit);
        for (int i = 0; i < max; i++) {
            JSONObject o = arr.getJSONObject(i);
            Models.ExternalFilament ef = new Models.ExternalFilament();
            ef.id = o.optString("id", "");
            ef.manufacturer = o.optString("manufacturer", "");
            ef.name = o.optString("name", "");
            ef.material = o.optString("material", "PLA");
            ef.density = o.optDouble("density", 1.24);
            ef.diameter = o.optDouble("diameter", 1.75);
            ef.weight = o.optDouble("weight", 1000.0);
            if (!o.isNull("spool_weight")) ef.spoolWeight = o.optDouble("spool_weight");
            ef.colorHex = o.isNull("color_hex") ? "38BDF8" : o.optString("color_hex", "38BDF8");
            JSONArray chexes = o.optJSONArray("color_hexes");
            if (chexes != null && chexes.length() > 1) {
                StringBuilder sb = new StringBuilder();
                for (int k = 0; k < chexes.length(); k++) {
                    if (k > 0) sb.append(",");
                    sb.append(chexes.optString(k, "").replace("#", ""));
                }
                ef.multiColorHexes = sb.toString();
            }
            if (!o.isNull("extruder_temp")) ef.extruderTemp = o.optInt("extruder_temp");
            if (!o.isNull("bed_temp")) ef.bedTemp = o.optInt("bed_temp");
            out.add(ef);
        }
        return out;
    }

    public static Models.Filament importExternalFilament(String baseUrl, Models.ExternalFilament ext, List<Models.Vendor> vendors) throws Exception {
        Integer vendorId = null;
        String mfg = ext.manufacturer != null ? ext.manufacturer.trim() : "";
        if (!mfg.isEmpty()) {
            if (vendors != null) {
                for (Models.Vendor v : vendors) {
                    if (v.name != null && v.name.trim().equalsIgnoreCase(mfg)) {
                        vendorId = v.id;
                        break;
                    }
                }
            }
            if (vendorId == null) {
                JSONObject vp = new JSONObject();
                vp.put("name", mfg);
                vp.put("external_id", mfg);
                if (ext.spoolWeight != null && ext.spoolWeight > 0) {
                    vp.put("empty_spool_weight", ext.spoolWeight);
                }
                Models.Vendor createdV = createVendor(baseUrl, vp);
                vendorId = createdV.id;
            }
        }

        JSONObject fp = new JSONObject();
        fp.put("name", ext.name != null && !ext.name.isEmpty() ? ext.name : mfg);
        if (vendorId != null) fp.put("vendor_id", vendorId);
        fp.put("material", ext.material != null && !ext.material.isEmpty() ? ext.material : "PLA");
        fp.put("density", ext.density > 0 ? ext.density : 1.24);
        fp.put("diameter", ext.diameter > 0 ? ext.diameter : 1.75);
        if (ext.weight > 0) fp.put("weight", ext.weight);
        if (ext.spoolWeight != null && ext.spoolWeight > 0) fp.put("spool_weight", ext.spoolWeight);
        if (ext.extruderTemp != null && ext.extruderTemp > 0) fp.put("settings_extruder_temp", ext.extruderTemp);
        if (ext.bedTemp != null && ext.bedTemp > 0) fp.put("settings_bed_temp", ext.bedTemp);
        if (ext.multiColorHexes != null && !ext.multiColorHexes.isEmpty()) {
            fp.put("multi_color_hexes", ext.multiColorHexes);
            fp.put("multi_color_direction", "coaxial");
        } else if (ext.colorHex != null && !ext.colorHex.isEmpty()) {
            fp.put("color_hex", ext.colorHex.replace("#", ""));
        }
        if (ext.id != null && !ext.id.isEmpty()) fp.put("external_id", ext.id);
        return createFilament(baseUrl, fp);
    }

    // ---------- Printer Slot & NFC Sync ----------

    public static Models.PrinterSpoolState fetchPrinterSpoolState(Models.Printer p) {
        Models.PrinterSpoolState ps = new Models.PrinterSpoolState();
        ps.printerId = p.id;
        ps.printerName = p.name;
        try {
            JSONObject objsRes = ApiClient.getJson(p, "/printer/objects/list", 3000);
            JSONArray objsArr = objsRes.optJSONArray("objects");
            List<String> objs = new ArrayList<>();
            if (objsArr != null) {
                for (int i = 0; i < objsArr.length(); i++) objs.add(objsArr.getString(i));
            }
            ps.online = true;

            try {
                JSONObject sm = ApiClient.getJson(p, "/server/spoolman/status", 2500);
                if (!sm.isNull("spool_id")) {
                    int sid = sm.optInt("spool_id", 0);
                    if (sid > 0) ps.activeSpoolId = sid;
                }
            } catch (Exception ignored) {
            }

            List<String> qList = new ArrayList<>();
            for (String cand : new String[]{"toolhead", "print_task_config", "filament_detect"}) {
                if (objs.contains(cand)) qList.add(cand);
            }
            if (!qList.isEmpty()) {
                StringBuilder qb = new StringBuilder();
                for (int i = 0; i < qList.size(); i++) {
                    if (i > 0) qb.append("&");
                    qb.append(qList.get(i));
                }
                JSONObject stRoot = ApiClient.getJson(p, "/printer/objects/query?" + qb, 3000);
                JSONObject st = stRoot.optJSONObject("status");
                if (st == null) st = stRoot;

                JSONObject th = st.optJSONObject("toolhead");
                if (th != null) {
                    ps.activeExtruder = th.optString("extruder", "extruder");
                }
                JSONObject ptc = st.optJSONObject("print_task_config");
                JSONObject fdet = st.optJSONObject("filament_detect");
                JSONArray sids = ptc != null ? ptc.optJSONArray("filament_spool_id") : null;
                JSONArray existArr = ptc != null ? ptc.optJSONArray("filament_exist") : null;
                JSONArray typeArr = ptc != null ? ptc.optJSONArray("filament_type") : null;
                JSONArray colorArr = ptc != null ? ptc.optJSONArray("filament_color_rgba") : null;
                JSONArray infoArr = fdet != null ? fdet.optJSONArray("info") : null;

                int nSlots = Math.max(sids != null ? sids.length() : 0, infoArr != null ? infoArr.length() : 0);
                for (int ch = 0; ch < nSlots; ch++) {
                    Models.PrinterSlot sl = new Models.PrinterSlot();
                    sl.channel = ch;
                    sl.label = "T" + ch;
                    sl.extruder = ch == 0 ? "extruder" : "extruder" + ch;
                    sl.active = sl.extruder.equals(ps.activeExtruder);
                    if (sids != null && ch < sids.length()) {
                        int v = sids.optInt(ch, 0);
                        sl.spoolId = v > 0 ? v : null;
                    }
                    if (existArr != null && ch < existArr.length()) {
                        sl.exist = existArr.optBoolean(ch, false);
                    }
                    if (typeArr != null && ch < typeArr.length()) {
                        String t = typeArr.optString(ch, "");
                        sl.type = "NONE".equals(t) ? "" : t;
                    }
                    if (colorArr != null && ch < colorArr.length()) {
                        String rgba = colorArr.optString(ch, "FFFFFF");
                        if (rgba.length() >= 6) sl.colorHex = "#" + rgba.substring(0, 6);
                    }
                    if (infoArr != null && ch < infoArr.length()) {
                        JSONObject inf = infoArr.optJSONObject(ch);
                        if (inf != null) {
                            sl.cardUid = formatCardUid(inf.opt("CARD_UID"));
                        }
                    }
                    ps.slots.add(sl);
                }
            }
        } catch (Exception e) {
            ps.online = false;
        }
        return ps;
    }

    public static void assignSpoolToPrinter(Models.Printer p, Integer spoolId, Integer channel) throws Exception {
        int sid = (spoolId != null && spoolId > 0) ? spoolId : 0;
        if (channel != null) {
            ApiClient.sendGcode(p, "SET_SPOOL_ID CHANNEL=" + channel + " SPOOL_ID=" + sid);
            try {
                JSONObject b = new JSONObject();
                b.put("spool_id", sid > 0 ? sid : JSONObject.NULL);
                ApiClient.postJson(p, "/server/spoolman/spool_id", b, 4000);
            } catch (Exception ignored) {
            }
            return;
        }
        try {
            JSONObject b = new JSONObject();
            b.put("spool_id", sid > 0 ? sid : JSONObject.NULL);
            ApiClient.postJson(p, "/server/spoolman/spool_id", b, 4000);
        } catch (Exception e) {
            ApiClient.sendGcode(p, "SET_SPOOL_ID CHANNEL=0 SPOOL_ID=" + sid);
        }
    }

    public static Models.Spool linkNfcUidToSpool(String baseUrl, Models.Spool spool, String cardUid) throws Exception {
        String uid = formatCardUid(cardUid);
        if (uid.isEmpty()) return spool;
        List<String> existing = new ArrayList<>();
        if (spool.cardUids != null && !spool.cardUids.isEmpty()) {
            for (String part : spool.cardUids.split(",")) {
                String clean = part.trim().toUpperCase(Locale.ROOT);
                if (!clean.isEmpty() && !existing.contains(clean)) existing.add(clean);
            }
        }
        if (!existing.contains(uid)) existing.add(uid);
        StringBuilder merged = new StringBuilder();
        for (int i = 0; i < existing.size(); i++) {
            if (i > 0) merged.append(",");
            merged.append(existing.get(i));
        }
        JSONObject extra = new JSONObject();
        extra.put("card_uids", encodeExtraString(merged.toString()));
        JSONObject payload = new JSONObject();
        payload.put("extra", extra);
        return updateSpool(baseUrl, spool.id, payload);
    }
}
