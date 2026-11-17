package app.printboard.mobile;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class AppConfig {
    private static final String PREFS = "printboard_mobile_prefs";

    public static final String DEFAULT_SPOOLMAN_URL = "http://192.168.178.170:7912";
    public static final String DEFAULT_DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1565203709472809051/BCP34bcurjXItbkpqJFWAqWE_8ep8XvM8SsiS6Lx8he6idFFYxlaoQFsHyXintL4tMRi";

    private final SharedPreferences prefs;

    public AppConfig(Context ctx) {
        this.prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        ensureDefaults();
    }

    private void ensureDefaults() {
        if (!prefs.contains("initialized_v1")) {
            List<Models.Printer> defaults = new ArrayList<>();
            defaults.add(new Models.Printer("d9324a09", "U1", "192.168.178.143", 80, "", false, ""));
            defaults.add(new Models.Printer("c6451280", "Q2", "192.168.178.165", 80, "", false, "http://192.168.178.165:18080/"));
            savePrinters(defaults);
            prefs.edit()
                .putBoolean("initialized_v1", true)
                .putString("spoolman_url", DEFAULT_SPOOLMAN_URL)
                .putString("discord_webhook", DEFAULT_DISCORD_WEBHOOK)
                .putBoolean("controls_enabled", true)
                .apply();
        }
    }

    public List<Models.Printer> loadPrinters() {
        List<Models.Printer> list = new ArrayList<>();
        String raw = prefs.getString("printers_json", "[]");
        try {
            JSONArray arr = new JSONArray(raw);
            for (int i = 0; i < arr.length(); i++) {
                JSONObject o = arr.getJSONObject(i);
                list.add(new Models.Printer(
                    o.optString("id", ""),
                    o.optString("name", "Printer"),
                    o.optString("host", ""),
                    o.optInt("port", 80),
                    o.optString("token", ""),
                    o.optBoolean("tls", false),
                    o.optString("display_url", "")
                ));
            }
        } catch (Exception ignored) {
        }
        return list;
    }

    public void savePrinters(List<Models.Printer> printers) {
        JSONArray arr = new JSONArray();
        for (Models.Printer p : printers) {
            try {
                JSONObject o = new JSONObject();
                o.put("id", p.id);
                o.put("name", p.name);
                o.put("host", p.host);
                o.put("port", p.port);
                o.put("token", p.token);
                o.put("tls", p.tls);
                o.put("display_url", p.displayUrl);
                arr.put(o);
            } catch (Exception ignored) {
            }
        }
        prefs.edit().putString("printers_json", arr.toString()).apply();
    }

    public String getSpoolmanUrl() {
        return SpoolmanClient.normalizeUrl(prefs.getString("spoolman_url", DEFAULT_SPOOLMAN_URL));
    }

    public void setSpoolmanUrl(String url) {
        prefs.edit().putString("spoolman_url", SpoolmanClient.normalizeUrl(url)).apply();
    }

    public String getDiscordWebhook() {
        return prefs.getString("discord_webhook", DEFAULT_DISCORD_WEBHOOK).trim();
    }

    public void setDiscordWebhook(String url) {
        prefs.edit().putString("discord_webhook", url == null ? "" : url.trim()).apply();
    }

    public String getTelegramToken() {
        return prefs.getString("tg_token", "").trim();
    }

    public void setTelegramToken(String token) {
        prefs.edit().putString("tg_token", token == null ? "" : token.trim()).apply();
    }

    public String getTelegramChatId() {
        return prefs.getString("tg_chat", "").trim();
    }

    public void setTelegramChatId(String chatId) {
        prefs.edit().putString("tg_chat", chatId == null ? "" : chatId.trim()).apply();
    }

    public boolean isControlsEnabled() {
        return prefs.getBoolean("controls_enabled", true);
    }

    public void setControlsEnabled(boolean enabled) {
        prefs.edit().putBoolean("controls_enabled", enabled).apply();
    }

    public Integer getLocalPrinterSpool(String printerId) {
        int v = prefs.getInt("local_spool_" + printerId, 0);
        return v > 0 ? v : null;
    }

    public void setLocalPrinterSpool(String printerId, Integer spoolId) {
        prefs.edit().putInt("local_spool_" + printerId, (spoolId != null && spoolId > 0) ? spoolId : 0).apply();
    }

    public Set<String> getHiddenCameras() {
        Set<String> s = prefs.getStringSet("multicam_hidden", null);
        return s != null ? new HashSet<>(s) : new HashSet<>();
    }

    public void setHiddenCameras(Set<String> hidden) {
        prefs.edit().putStringSet("multicam_hidden", new HashSet<>(hidden)).apply();
    }

    public float getCostEurPerKg() {
        return prefs.getFloat("cost_eur_kg", 25.0f);
    }

    public void setCostEurPerKg(float v) {
        prefs.edit().putFloat("cost_eur_kg", v).apply();
    }

    public float getCostWatts() {
        return prefs.getFloat("cost_watts", 150.0f);
    }

    public void setCostWatts(float v) {
        prefs.edit().putFloat("cost_watts", v).apply();
    }

    public float getCostEurPerKwh() {
        return prefs.getFloat("cost_kwh", 0.30f);
    }

    public void setCostEurPerKwh(float v) {
        prefs.edit().putFloat("cost_kwh", v).apply();
    }

    public float getCostWearPerHour() {
        return prefs.getFloat("cost_wear", 0.10f);
    }

    public void setCostWearPerHour(float v) {
        prefs.edit().putFloat("cost_wear", v).apply();
    }
}
