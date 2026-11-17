package app.printboard.mobile;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.OpenableColumns;
import android.text.Editable;
import android.text.InputType;
import android.text.TextUtils;
import android.text.TextWatcher;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {

    private static final int REQ_PICK_GCODE = 1001;

    public interface TaskCallable<T> {
        T call() throws Exception;
    }

    public interface TaskCallback<T> {
        void onSuccess(T result);
    }

    public AppConfig config;
    public List<Models.Printer> printers = new ArrayList<>();
    public final Map<String, Models.PrinterStatus> statuses = new ConcurrentHashMap<>();
    public final Map<String, String> lastStates = new ConcurrentHashMap<>();

    public List<Models.Spool> spools = new ArrayList<>();
    public List<Models.Filament> filaments = new ArrayList<>();
    public List<Models.Vendor> vendors = new ArrayList<>();
    public final Map<Integer, Models.Spool> spoolById = new ConcurrentHashMap<>();
    public final Map<String, Models.PrinterSpoolState> printerSpoolStates = new ConcurrentHashMap<>();
    public String spoolmanVersion = "";
    public boolean spoolmanOnline = false;

    private final ExecutorService executor = Executors.newCachedThreadPool();
    private final Handler uiHandler = new Handler(Looper.getMainLooper());

    private int activeTab = 0; // 0=Printers, 1=Spoolman, 2=Stats, 3=Models, 4=Settings
    private FrameLayout contentContainer;
    private LinearLayout bottomNav;

    // Printers Tab sub-modes: 0=Cards Overview, 1=Multi-Cam Grid, 2=Printer Detail
    private int printerSubMode = 0;
    private String selectedPrinterId = null;
    private LinearLayout printersCardsBox;
    private WebView multiCamWebView;
    private boolean multiCamCover = true;
    private List<Models.WebcamItem> cachedAllCams = new ArrayList<>();
    private double detailJogStep = 10.0;
    private Models.Printer pendingUploadPrinter = null;
    private boolean pendingUploadStartNow = false;

    // Spoolman Tab state
    private int spoolmanSubTab = 0; // 0=Spools, 1=Filaments, 2=Vendors, 3=Slots & NFC
    private String spoolSearchQuery = "";
    private String spoolMaterialFilter = "Alle";
    private boolean spoolShowArchived = false;
    private LinearLayout spoolmanListContainer;
    private TextView kpiSpoolsVal, kpiWeightVal, kpiValueVal, kpiLowVal;
    private TextView spoolmanServerBadge;

    // Stats Tab state
    private int statsPrinterIndex = 0;
    private List<Models.PrintJob> currentStatsJobs = new ArrayList<>();

    // Models WebView state
    private WebView modelsWebView;
    private EditText modelsUrlInput;

    private final Runnable pollRunnable = this::runPollCycle;

    private void runPollCycle() {
        pollAllPrinters();
        uiHandler.postDelayed(pollRunnable, 3500);
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP && getWindow() != null) {
            getWindow().setStatusBarColor(UiTheme.BG_MAIN);
            getWindow().setNavigationBarColor(UiTheme.BG_NAV);
        }

        config = new AppConfig(this);
        printers = config.loadPrinters();

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(UiTheme.BG_MAIN);

        contentContainer = new FrameLayout(this);
        root.addView(contentContainer, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        bottomNav = buildBottomNav();
        root.addView(bottomNav, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, UiTheme.dp(this, 64)));

        setContentView(root);

        switchTab(0);
        refreshSpoolmanData();
        uiHandler.post(pollRunnable);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        uiHandler.removeCallbacks(pollRunnable);
        executor.shutdownNow();
    }

    @Override
    public void onBackPressed() {
        if (activeTab == 0 && printerSubMode != 0) {
            printerSubMode = 0;
            renderPrintersTab();
            return;
        }
        if (activeTab == 3 && modelsWebView != null && modelsWebView.canGoBack()) {
            modelsWebView.goBack();
            return;
        }
        if (activeTab != 0) {
            switchTab(0);
            return;
        }
        super.onBackPressed();
    }

    public <T> void runAsync(TaskCallable<T> task, TaskCallback<T> onSuccess) {
        executor.submit(() -> {
            try {
                final T res = task.call();
                uiHandler.post(() -> {
                    if (!isFinishing() && onSuccess != null) {
                        onSuccess.onSuccess(res);
                    }
                });
            } catch (Exception e) {
                final String msg = e.getMessage() != null ? e.getMessage() : e.toString();
                uiHandler.post(() -> {
                    if (!isFinishing()) {
                        toast("Fehler: " + msg);
                    }
                });
            }
        });
    }

    public void toast(String msg) {
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show();
    }

    // ---------- Bottom Navigation ----------

    private LinearLayout buildBottomNav() {
        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setBackgroundColor(UiTheme.BG_NAV);
        nav.setGravity(Gravity.CENTER);
        nav.setPadding(UiTheme.dp(this, 6), UiTheme.dp(this, 4), UiTheme.dp(this, 6), UiTheme.dp(this, 4));
        updateBottomNavItems(nav);
        return nav;
    }

    private void updateBottomNavItems(LinearLayout nav) {
        nav.removeAllViews();
        String[][] tabs = new String[][]{
            {"", "Drucker"},
            {"", "Spoolman"},
            {"", "Statistik"},
            {"", "Modelle"},
            {"", "Setup"}
        };
        for (int i = 0; i < tabs.length; i++) {
            final int idx = i;
            boolean sel = (i == activeTab);
            LinearLayout item = new LinearLayout(this);
            item.setOrientation(LinearLayout.VERTICAL);
            item.setGravity(Gravity.CENTER);
            int py = UiTheme.dp(this, 4);
            item.setPadding(0, py, 0, py);
            if (sel) {
                item.setBackground(UiTheme.roundRect(Color.parseColor("#13263C"), Color.parseColor("#25486E"), UiTheme.dp(this, 1), UiTheme.dp(this, 12)));
            }

            TextView icon = new TextView(this);
            icon.setText(tabs[i][0]);
            icon.setTextSize(TypedValue.COMPLEX_UNIT_SP, 17f);
            icon.setGravity(Gravity.CENTER);
            item.addView(icon);

            TextView lbl = new TextView(this);
            lbl.setText(tabs[i][1]);
            lbl.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11f);
            lbl.setGravity(Gravity.CENTER);
            lbl.setTextColor(sel ? UiTheme.ACCENT : UiTheme.TEXT_DIM);
            lbl.setTypeface(Typeface.create("sans-serif-medium", sel ? Typeface.BOLD : Typeface.NORMAL));
            item.addView(lbl);

            item.setOnClickListener(v -> switchTab(idx));
            nav.addView(item, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1f));
        }
    }

    private void switchTab(int idx) {
        activeTab = idx;
        updateBottomNavItems(bottomNav);
        contentContainer.removeAllViews();
        switch (idx) {
            case 0:
                renderPrintersTab();
                break;
            case 1:
                renderSpoolmanTab();
                break;
            case 2:
                renderStatsTab();
                break;
            case 3:
                renderModelsTab();
                break;
            case 4:
                renderSettingsTab();
                break;
        }
    }

    // ---------- Polling & Spoolman Sync ----------

    public void pollAllPrinters() {
        final List<Models.Printer> snap = new ArrayList<>(printers);
        for (Models.Printer p : snap) {
            executor.submit(() -> {
                Models.PrinterStatus st = ApiClient.fetchStatus(p);
                String prev = lastStates.get(p.id);
                if (prev != null && !prev.equals(st.state)) {
                    onPrinterStateTransition(p, prev, st);
                }
                if (st.online) {
                    lastStates.put(p.id, st.state);
                }
                statuses.put(p.id, st);
                uiHandler.post(() -> {
                    if (activeTab == 0 && printerSubMode == 0 && printersCardsBox != null) {
                        populatePrinterCards();
                    }
                });
            });
        }
    }

    private void onPrinterStateTransition(Models.Printer p, String oldState, Models.PrinterStatus st) {
        String msg = null;
        if ("printing".equals(oldState) && "complete".equals(st.state)) {
            msg = "PrintBoard: Druck fertig auf " + p.name + " (" + st.filename + ")";
        } else if ("error".equals(st.state)) {
            msg = "PrintBoard: Fehler auf " + p.name + " (" + st.filename + ")";
        }
        if (msg != null) {
            final String finalMsg = msg;
            executor.submit(() -> {
                try {
                    String wh = config.getDiscordWebhook();
                    if (!wh.isEmpty()) ApiClient.sendDiscordWebhook(wh, finalMsg);
                } catch (Exception ignored) {
                }
                try {
                    String tok = config.getTelegramToken();
                    String chat = config.getTelegramChatId();
                    if (!tok.isEmpty() && !chat.isEmpty()) ApiClient.sendTelegram(tok, chat, finalMsg);
                } catch (Exception ignored) {
                }
            });
        }
    }

    public void refreshSpoolmanData() {
        final String url = config.getSpoolmanUrl();
        final List<Models.Printer> pSnap = new ArrayList<>(printers);
        executor.submit(() -> {
            boolean ok = false;
            String ver = "";
            List<Models.Spool> spList = new ArrayList<>();
            List<Models.Filament> filList = new ArrayList<>();
            List<Models.Vendor> venList = new ArrayList<>();
            try {
                JSONObject info = SpoolmanClient.getInfo(url);
                ver = info.optString("version", "v1");
                spList = SpoolmanClient.listSpools(url, spoolShowArchived);
                filList = SpoolmanClient.listFilaments(url);
                venList = SpoolmanClient.listVendors(url);
                ok = true;
            } catch (Exception ignored) {
            }

            Map<String, Models.PrinterSpoolState> pStates = new HashMap<>();
            for (Models.Printer p : pSnap) {
                Models.PrinterSpoolState ps = SpoolmanClient.fetchPrinterSpoolState(p);
                pStates.put(p.id, ps);
            }

            // Auto-match NFC CARD_UID to Spoolman spools
            if (ok && !spList.isEmpty()) {
                Map<String, Models.Spool> uidMap = new HashMap<>();
                for (Models.Spool s : spList) {
                    if (s.cardUids != null && !s.cardUids.isEmpty()) {
                        for (String u : s.cardUids.split(",")) {
                            String clean = u.trim().toUpperCase(Locale.ROOT);
                            if (!clean.isEmpty()) uidMap.put(clean, s);
                        }
                    }
                }
                for (Models.PrinterSpoolState ps : pStates.values()) {
                    for (Models.PrinterSlot sl : ps.slots) {
                        if ((sl.spoolId == null || sl.spoolId <= 0) && sl.cardUid != null && uidMap.containsKey(sl.cardUid)) {
                            sl.spoolId = uidMap.get(sl.cardUid).id;
                        }
                    }
                }
            }

            final boolean finalOk = ok;
            final String finalVer = ver;
            final List<Models.Spool> finalSpools = spList;
            final List<Models.Filament> finalFils = filList;
            final List<Models.Vendor> finalVens = venList;

            uiHandler.post(() -> {
                spoolmanOnline = finalOk;
                spoolmanVersion = finalVer;
                spools = finalSpools;
                filaments = finalFils;
                vendors = finalVens;
                spoolById.clear();
                for (Models.Spool s : spools) {
                    spoolById.put(s.id, s);
                }
                printerSpoolStates.clear();
                printerSpoolStates.putAll(pStates);

                if (activeTab == 1) {
                    updateSpoolmanUI();
                } else if (activeTab == 0 && printerSubMode == 0 && printersCardsBox != null) {
                    populatePrinterCards();
                }
            });
        });
    }

    public Models.Spool resolveActiveSpoolForPrinter(Models.Printer p, Models.PrinterStatus st) {
        if (st != null && st.activeSpoolId != null && spoolById.containsKey(st.activeSpoolId)) {
            return spoolById.get(st.activeSpoolId);
        }
        Models.PrinterSpoolState ps = printerSpoolStates.get(p.id);
        if (ps != null) {
            if (ps.activeSpoolId != null && spoolById.containsKey(ps.activeSpoolId)) {
                return spoolById.get(ps.activeSpoolId);
            }
            for (Models.PrinterSlot sl : ps.slots) {
                if (sl.active && sl.spoolId != null && spoolById.containsKey(sl.spoolId)) {
                    return spoolById.get(sl.spoolId);
                }
            }
        }
        Integer localId = config.getLocalPrinterSpool(p.id);
        if (localId != null && spoolById.containsKey(localId)) {
            return spoolById.get(localId);
        }
        return null;
    }

    // =========================================================================
    // TAB 1: DRUCKER (Overview, Multi-Camera Grid, Printer Detail)
    // =========================================================================

    private void renderPrintersTab() {
        contentContainer.removeAllViews();
        if (printerSubMode == 1) {
            renderMultiCamView();
            return;
        }
        if (printerSubMode == 2 && selectedPrinterId != null) {
            Models.Printer target = null;
            for (Models.Printer p : printers) {
                if (p.id.equals(selectedPrinterId)) {
                    target = p;
                    break;
                }
            }
            if (target != null) {
                renderPrinterDetailView(target);
                return;
            }
            printerSubMode = 0;
        }

        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        int pad = UiTheme.dp(this, 14);
        page.setPadding(pad, pad, pad, pad);

        // Top Header Bar
        LinearLayout topBar = new LinearLayout(this);
        topBar.setOrientation(LinearLayout.HORIZONTAL);
        topBar.setGravity(Gravity.CENTER_VERTICAL);

        LinearLayout titleCol = new LinearLayout(this);
        titleCol.setOrientation(LinearLayout.VERTICAL);
        titleCol.addView(UiTheme.makeTitle(this, "Meine Drucker", 21f));
        titleCol.addView(UiTheme.makeDim(this, "Klipper / Moonraker Live-Übersicht", 12f));
        topBar.addView(titleCol, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        Button btnCams = UiTheme.makeButton(this, "Alle Cams", "ghost");
        btnCams.setOnClickListener(v -> {
            printerSubMode = 1;
            renderPrintersTab();
        });
        topBar.addView(btnCams);

        Button btnAdd = UiTheme.makeButton(this, "+ Drucker", "primary");
        LinearLayout.LayoutParams alp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        alp.leftMargin = UiTheme.dp(this, 8);
        btnAdd.setOnClickListener(v -> showPrinterDialog(null));
        topBar.addView(btnAdd, alp);

        page.addView(topBar);

        ScrollView sc = new ScrollView(this);
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f);
        slp.topMargin = UiTheme.dp(this, 12);
        printersCardsBox = new LinearLayout(this);
        printersCardsBox.setOrientation(LinearLayout.VERTICAL);
        sc.addView(printersCardsBox);
        page.addView(sc, slp);

        contentContainer.addView(page);
        populatePrinterCards();
    }

    private void populatePrinterCards() {
        if (printersCardsBox == null) return;
        printersCardsBox.removeAllViews();

        if (printers.isEmpty()) {
            LinearLayout empty = UiTheme.makeCard(this, 24);
            empty.setGravity(Gravity.CENTER);
            empty.addView(UiTheme.makeTitle(this, "Noch keine Drucker eingerichtet", 16f));
            empty.addView(UiTheme.makeDim(this, "Tippe oben auf „+ Drucker“, um deine Klipper-Drucker hinzuzufügen oder im WLAN zu scannen.", 13f));
            printersCardsBox.addView(empty);
            return;
        }

        for (Models.Printer p : printers) {
            Models.PrinterStatus st = statuses.get(p.id);
            LinearLayout card = UiTheme.makeCard(this, 14);
            LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            clp.bottomMargin = UiTheme.dp(this, 12);
            card.setLayoutParams(clp);

            // Row 1: Name + Host + Status Badge + Edit/Delete
            LinearLayout r1 = new LinearLayout(this);
            r1.setOrientation(LinearLayout.HORIZONTAL);
            r1.setGravity(Gravity.CENTER_VERTICAL);

            LinearLayout nameCol = new LinearLayout(this);
            nameCol.setOrientation(LinearLayout.VERTICAL);
            nameCol.addView(UiTheme.makeTitle(this, p.name, 18f));
            nameCol.addView(UiTheme.makeDim(this, p.host + ":" + p.port, 12f));
            r1.addView(nameCol, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

            String stateKey = (st != null && st.online) ? st.state : "offline";
            TextView badge = makeStateBadge(stateKey);
            r1.addView(badge);

            Button bEdit = UiTheme.makeButton(this, "", "ghost");
            LinearLayout.LayoutParams elp = new LinearLayout.LayoutParams(UiTheme.dp(this, 40), UiTheme.dp(this, 36));
            elp.leftMargin = UiTheme.dp(this, 6);
            bEdit.setPadding(0, 0, 0, 0);
            bEdit.setOnClickListener(v -> showPrinterDialog(p));
            r1.addView(bEdit, elp);

            card.addView(r1);

            // Row 2: Thumbnail + File/Progress Info
            LinearLayout r2 = new LinearLayout(this);
            r2.setOrientation(LinearLayout.HORIZONTAL);
            r2.setGravity(Gravity.CENTER_VERTICAL);
            r2.setPadding(0, UiTheme.dp(this, 10), 0, UiTheme.dp(this, 8));

            if (st != null && st.thumbnail != null) {
                ImageView iv = new ImageView(this);
                iv.setImageBitmap(st.thumbnail);
                iv.setScaleType(ImageView.ScaleType.CENTER_CROP);
                int tsz = UiTheme.dp(this, 64);
                LinearLayout.LayoutParams ilp = new LinearLayout.LayoutParams(tsz, tsz);
                ilp.rightMargin = UiTheme.dp(this, 12);
                r2.addView(iv, ilp);
            }

            LinearLayout progCol = new LinearLayout(this);
            progCol.setOrientation(LinearLayout.VERTICAL);
            String fname = (st != null && st.online && st.filename != null && !st.filename.isEmpty())
                    ? st.filename : (st != null && !st.online ? "Nicht erreichbar (" + st.error + ")" : "Kein aktiver Druckauftrag");
            TextView fileTv = UiTheme.makeTitle(this, fname, 13.5f);
            fileTv.setEllipsize(TextUtils.TruncateAt.MIDDLE);
            fileTv.setSingleLine(true);
            progCol.addView(fileTv);

            double pct = (st != null && st.online) ? st.progress : 0.0;
            UiTheme.LevelBarView pBar = new UiTheme.LevelBarView(this, 9);
            LinearLayout.LayoutParams pblp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, UiTheme.dp(this, 9));
            pblp.topMargin = UiTheme.dp(this, 6);
            pblp.bottomMargin = UiTheme.dp(this, 4);
            pBar.setProgress(pct, "printing".equals(stateKey) ? UiTheme.ACCENT : UiTheme.GREEN);
            progCol.addView(pBar, pblp);

            String durText = (st != null && st.online)
                    ? String.format(Locale.US, "%.0f%%  ·  Laufzeit: %s  ·  Rest: %s", pct * 100.0, UiTheme.formatHms(st.duration), UiTheme.formatHms(st.remaining))
                    : "Tippe für Details & Steuerung";
            progCol.addView(UiTheme.makeDim(this, durText, 12f));

            r2.addView(progCol, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
            card.addView(r2);

            // Row 3: Live Temperatures
            if (st != null && st.online && !st.temps.isEmpty()) {
                StringBuilder tsb = new StringBuilder();
                int limit = Math.min(st.temps.size(), 4);
                for (int i = 0; i < limit; i++) {
                    Models.TempReading tr = st.temps.get(i);
                    if (Double.isNaN(tr.temperature)) continue;
                    if (tsb.length() > 0) tsb.append("   ·   ");
                    tsb.append(tr.label).append(": ").append(String.format(Locale.US, "%.1f°C", tr.temperature));
                    if (!Double.isNaN(tr.target) && tr.target > 0) {
                        tsb.append(String.format(Locale.US, " (→%.0f°)", tr.target));
                    }
                }
                if (tsb.length() > 0) {
                    TextView tempTv = UiTheme.makeDim(this, "" + tsb, 12.5f);
                    tempTv.setTextColor(Color.parseColor("#CBD5E1"));
                    tempTv.setPadding(0, 0, 0, UiTheme.dp(this, 6));
                    card.addView(tempTv);
                }
            }

            // Row 4: Active Spoolman Spool Pill
            Models.Spool activeSpool = resolveActiveSpoolForPrinter(p, st);
            if (activeSpool != null) {
                LinearLayout spBox = UiTheme.makeAltCard(this, 8);
                spBox.setOrientation(LinearLayout.HORIZONTAL);
                spBox.setGravity(Gravity.CENTER_VERTICAL);

                UiTheme.SpoolIconView sIcon = new UiTheme.SpoolIconView(this, 26);
                sIcon.setSpoolData(activeSpool.getColors(), activeSpool.getFillFraction());
                spBox.addView(sIcon);

                String sLabel = String.format(Locale.US, "  %s · %.0f g (%.0f%%)",
                        activeSpool.getDisplayName(), activeSpool.remainingWeight, activeSpool.getFillFraction() * 100.0);
                TextView sTv = UiTheme.makeTitle(this, sLabel, 12.5f);
                sTv.setSingleLine(true);
                sTv.setEllipsize(TextUtils.TruncateAt.END);
                spBox.addView(sTv, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

                spBox.setOnClickListener(v -> SpoolmanDialogs.showSpoolSheet(this, activeSpool));
                card.addView(spBox);
            }

            card.setOnClickListener(v -> {
                selectedPrinterId = p.id;
                printerSubMode = 2;
                renderPrintersTab();
            });

            printersCardsBox.addView(card);
        }
    }

    private TextView makeStateBadge(String state) {
        switch (state) {
            case "printing":
                return UiTheme.makePill(this, "● DRUCKT", UiTheme.ACCENT, Color.parseColor("#0C2D48"));
            case "paused":
                return UiTheme.makePill(this, "PAUSIERT", UiTheme.YELLOW, Color.parseColor("#3B2F0B"));
            case "complete":
                return UiTheme.makePill(this, "FERTIG", UiTheme.GREEN, Color.parseColor("#0A2E22"));
            case "error":
                return UiTheme.makePill(this, "FEHLER", UiTheme.RED, Color.parseColor("#3B1219"));
            case "standby":
            case "ready":
                return UiTheme.makePill(this, "● BEREIT", UiTheme.GREEN, Color.parseColor("#0A2E22"));
            default:
                return UiTheme.makePill(this, "○ OFFLINE", UiTheme.TEXT_DIM, Color.parseColor("#162231"));
        }
    }

    // ---------- Multi-Camera & Display Grid View ----------

    private void renderMultiCamView() {
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        int pad = UiTheme.dp(this, 10);
        page.setPadding(pad, pad, pad, pad);

        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);

        Button bBack = UiTheme.makeButton(this, "← Zurück", "ghost");
        bBack.setOnClickListener(v -> {
            printerSubMode = 0;
            renderPrintersTab();
        });
        bar.addView(bBack);

        TextView title = UiTheme.makeTitle(this, "  Alle Cams & Displays", 16f);
        bar.addView(title, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        Button bSelect = UiTheme.makeButton(this, "Auswählen", "");
        bSelect.setOnClickListener(v -> showCameraSelectorDialog());
        bar.addView(bSelect);

        Button bFit = UiTheme.makeButton(this, multiCamCover ? "↔ Ausfüllen" : "↔ Einpassen", "");
        LinearLayout.LayoutParams flp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        flp.leftMargin = UiTheme.dp(this, 6);
        bFit.setOnClickListener(v -> {
            multiCamCover = !multiCamCover;
            bFit.setText(multiCamCover ? "↔ Ausfüllen" : "↔ Einpassen");
            loadMultiCamHtml();
        });
        bar.addView(bFit, flp);

        page.addView(bar);

        multiCamWebView = new WebView(this);
        multiCamWebView.setBackgroundColor(UiTheme.BG_MAIN);
        WebSettings ws = multiCamWebView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setMediaPlaybackRequiresUserGesture(false);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        multiCamWebView.setWebViewClient(new WebViewClient());

        LinearLayout.LayoutParams wlp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f);
        wlp.topMargin = UiTheme.dp(this, 8);
        page.addView(multiCamWebView, wlp);

        contentContainer.addView(page);

        runAsync(() -> ApiClient.allWebcams(printers), cams -> {
            cachedAllCams = cams != null ? cams : new ArrayList<>();
            loadMultiCamHtml();
        });
    }

    private void loadMultiCamHtml() {
        if (multiCamWebView == null) return;
        Set<String> hidden = config.getHiddenCameras();
        List<Models.WebcamItem> visible = new ArrayList<>();
        for (Models.WebcamItem c : cachedAllCams) {
            if (!hidden.contains(c.getKey())) {
                visible.add(c);
            }
        }
        String fitMode = multiCamCover ? "cover" : "contain";
        StringBuilder cells = new StringBuilder();
        for (int i = 0; i < visible.size(); i++) {
            Models.WebcamItem c = visible.get(i);
            String u = c.url;
            String low = u.toLowerCase(Locale.ROOT);
            boolean isIframe = "iframe".equals(c.service) || c.service.contains("webrtc")
                    || low.contains(":18080") || low.endsWith("/player") || low.endsWith("/webrtc");
            boolean isSnap = low.contains("action=snapshot") || low.endsWith(".jpg") || low.endsWith(".jpeg") || low.endsWith(".png");

            String media;
            if (isIframe) {
                media = "<iframe src='" + u + "' allow='autoplay; fullscreen'></iframe>";
            } else if (isSnap) {
                media = "<img id='s" + i + "' src='" + u + "' style='object-fit:" + fitMode + "'/>"
                        + "<script>setInterval(function(){var el=document.getElementById('s" + i + "');if(el)el.src='" + u + "'+(('" + u + "'.indexOf('?')>-1)?'&':'?')+'_t='+Date.now();},1200);</script>";
            } else {
                media = "<img src='" + u + "' style='object-fit:" + fitMode + "'/>";
            }
            cells.append("<div class='cell'>").append(media)
                 .append("<div class='lbl'>").append(c.name).append("</div></div>");
        }
        if (visible.isEmpty()) {
            cells.append("<div style='color:#8198AF;display:flex;align-items:center;justify-content:center;height:100%;font-family:sans-serif;'>Keine Kameras ausgewählt oder erreichbar.</div>");
        }
        int cols = visible.size() <= 1 ? 1 : 2;
        String html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
                + "<style>*{box-sizing:border-box;margin:0;padding:0}html,body{width:100%;height:100%;background:#05080D;overflow:hidden}"
                + ".grid{display:grid;grid-template-columns:repeat(" + cols + ",1fr);grid-auto-rows:1fr; gap:6px;width:100%;height:100%;padding:4px}"
                + ".cell{position:relative;background:#0B111B;border:1px solid #1E2D40;border-radius:10px;overflow:hidden;min-height:180px}"
                + ".cell img,.cell iframe{width:100%;height:100%;border:0;display:block}"
                + ".lbl{position:absolute;left:8px;bottom:8px;background:rgba(8,13,20,0.82);color:#EAF0FA;padding:4px 9px;border-radius:6px;font:600 12px sans-serif;border:1px solid #26384F}</style></head>"
                + "<body><div class='grid'>" + cells + "</div></body></html>";
        multiCamWebView.loadDataWithBaseURL("http://localhost/", html, "text/html", "UTF-8", null);
    }

    private void showCameraSelectorDialog() {
        if (cachedAllCams.isEmpty()) {
            toast("Noch keine Kameras geladen.");
            return;
        }
        Set<String> hidden = config.getHiddenCameras();
        String[] labels = new String[cachedAllCams.size()];
        boolean[] checked = new boolean[cachedAllCams.size()];
        for (int i = 0; i < cachedAllCams.size(); i++) {
            Models.WebcamItem c = cachedAllCams.get(i);
            labels[i] = c.name;
            checked[i] = !hidden.contains(c.getKey());
        }
        new AlertDialog.Builder(this)
            .setTitle("Kameras & Displays auswählen")
            .setMultiChoiceItems(labels, checked, (d, which, isChecked) -> {
                String k = cachedAllCams.get(which).getKey();
                if (isChecked) hidden.remove(k);
                else hidden.add(k);
            })
            .setPositiveButton("Übernehmen", (d, w) -> {
                config.setHiddenCameras(hidden);
                loadMultiCamHtml();
            })
            .setNeutralButton("Alle zeigen", (d, w) -> {
                hidden.clear();
                config.setHiddenCameras(hidden);
                loadMultiCamHtml();
            })
            .show();
    }

    // ---------- Printer Detail View ----------

    private void renderPrinterDetailView(Models.Printer p) {
        Models.PrinterStatus st = statuses.get(p.id);
        if (st == null) st = new Models.PrinterStatus();

        ScrollView sc = new ScrollView(this);
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        int pad = UiTheme.dp(this, 14);
        col.setPadding(pad, pad, pad, pad);

        // Top Bar
        LinearLayout top = new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);
        Button bBack = UiTheme.makeButton(this, "← Übersicht", "ghost");
        bBack.setOnClickListener(v -> {
            printerSubMode = 0;
            renderPrintersTab();
        });
        top.addView(bBack);

        TextView title = UiTheme.makeTitle(this, "  " + p.name, 19f);
        top.addView(title, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        top.addView(makeStateBadge(st.online ? st.state : "offline"));
        col.addView(top);

        // 1. Status & Active Print Card
        LinearLayout statusCard = UiTheme.makeCard(this, 14);
        LinearLayout.LayoutParams sclp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        sclp.topMargin = UiTheme.dp(this, 12);
        statusCard.setLayoutParams(sclp);

        statusCard.addView(UiTheme.makeTitle(this, st.filename != null && !st.filename.isEmpty() ? st.filename : "Kein aktiver Druckauftrag", 15f));
        UiTheme.LevelBarView bar = new UiTheme.LevelBarView(this, 10);
        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, UiTheme.dp(this, 10));
        blp.topMargin = UiTheme.dp(this, 8);
        blp.bottomMargin = UiTheme.dp(this, 6);
        bar.setProgress(st.progress, UiTheme.ACCENT);
        statusCard.addView(bar, blp);

        statusCard.addView(UiTheme.makeDim(this, String.format(Locale.US,
                "Fortschritt: %.1f%%   ·   Laufzeit: %s   ·   Rest: %s\nPosition: X=%.1f  Y=%.1f  Z=%.2f   ·   Z-Offset: %+.3f mm",
                st.progress * 100.0, UiTheme.formatHms(st.duration), UiTheme.formatHms(st.remaining),
                st.position[0], st.position[1], st.position[2], st.zOffset), 12.5f));

        // Print Control Buttons
        if (config.isControlsEnabled()) {
            LinearLayout ctrlRow1 = new LinearLayout(this);
            ctrlRow1.setOrientation(LinearLayout.HORIZONTAL);
            ctrlRow1.setPadding(0, UiTheme.dp(this, 10), 0, 0);
            String[][] acts1 = new String[][]{
                {"Pause", "pause", "warn"},
                {"▶ Fortsetzen", "resume", "primary"},
                {"■ Abbrechen", "cancel", "danger"}
            };
            for (int i = 0; i < acts1.length; i++) {
                final String actName = acts1[i][1];
                Button b = UiTheme.makeButton(this, acts1[i][0], acts1[i][2]);
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
                if (i > 0) lp.leftMargin = UiTheme.dp(this, 6);
                b.setOnClickListener(v -> sendControlAction(p, actName));
                ctrlRow1.addView(b, lp);
            }
            statusCard.addView(ctrlRow1);

            LinearLayout ctrlRow2 = new LinearLayout(this);
            ctrlRow2.setOrientation(LinearLayout.HORIZONTAL);
            ctrlRow2.setPadding(0, UiTheme.dp(this, 6), 0, 0);
            Button bEstop = UiTheme.makeButton(this, "NOT-AUS (M112)", "danger");
            Button bFw = UiTheme.makeButton(this, "Firmware-Restart", "");
            bEstop.setOnClickListener(v -> sendControlAction(p, "emergency_stop"));
            bFw.setOnClickListener(v -> sendControlAction(p, "firmware_restart"));
            ctrlRow2.addView(bEstop, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
            LinearLayout.LayoutParams fwlp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
            fwlp.leftMargin = UiTheme.dp(this, 6);
            ctrlRow2.addView(bFw, fwlp);
            statusCard.addView(ctrlRow2);
        }
        col.addView(statusCard);

        // 2. Spoolman & T0-T3 Extruder Slots Card
        LinearLayout spoolCard = UiTheme.makeCard(this, 14);
        LinearLayout.LayoutParams spclp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        spclp.topMargin = UiTheme.dp(this, 12);
        spoolCard.setLayoutParams(spclp);
        spoolCard.addView(UiTheme.makeTitle(this, "Spoolman & Extruder-Slots", 15f));

        Models.Spool activeSpool = resolveActiveSpoolForPrinter(p, st);
        if (activeSpool != null) {
            LinearLayout sRow = new LinearLayout(this);
            sRow.setOrientation(LinearLayout.HORIZONTAL);
            sRow.setGravity(Gravity.CENTER_VERTICAL);
            sRow.setPadding(0, UiTheme.dp(this, 8), 0, UiTheme.dp(this, 8));
            UiTheme.SpoolIconView sIcon = new UiTheme.SpoolIconView(this, 42);
            sIcon.setSpoolData(activeSpool.getColors(), activeSpool.getFillFraction());
            sRow.addView(sIcon);

            LinearLayout sInfo = new LinearLayout(this);
            sInfo.setOrientation(LinearLayout.VERTICAL);
            sInfo.setPadding(UiTheme.dp(this, 10), 0, 0, 0);
            sInfo.addView(UiTheme.makeTitle(this, activeSpool.getDisplayName(), 14f));
            sInfo.addView(UiTheme.makeDim(this, String.format(Locale.US, "Rest: %.1f g (%.0f%%) · %.1f m",
                    activeSpool.remainingWeight, activeSpool.getFillFraction() * 100.0, activeSpool.remainingLength / 1000.0), 12f));
            sRow.addView(sInfo, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

            Button bInspect = UiTheme.makeButton(this, "Details", "ghost");
            bInspect.setOnClickListener(v -> SpoolmanDialogs.showSpoolSheet(this, activeSpool));
            sRow.addView(bInspect);
            spoolCard.addView(sRow);
        } else {
            spoolCard.addView(UiTheme.makeDim(this, "Keine aktive Spule zugewiesen.", 13f));
        }

        Models.PrinterSpoolState ps = printerSpoolStates.get(p.id);
        if (ps != null && !ps.slots.isEmpty()) {
            for (Models.PrinterSlot sl : ps.slots) {
                Models.Spool slSpool = sl.spoolId != null ? spoolById.get(sl.spoolId) : null;
                String slText = sl.label + (sl.active ? " " : "") + ": "
                        + (slSpool != null ? slSpool.getDisplayName() + String.format(Locale.US, " (%.0fg)", slSpool.remainingWeight) : "Leer")
                        + (!sl.cardUid.isEmpty() ? " [NFC " + sl.cardUid + "]" : "");
                Button bSlot = UiTheme.makeButton(this, slText, sl.active ? "primary" : "");
                LinearLayout.LayoutParams sllp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                sllp.topMargin = UiTheme.dp(this, 6);
                bSlot.setOnClickListener(v -> showPickSpoolForPrinterSlotDialog(p, sl.channel));
                spoolCard.addView(bSlot, sllp);
            }
        } else {
            Button bPickSpool = UiTheme.makeButton(this, "Spule auswählen / zuweisen …", "primary");
            LinearLayout.LayoutParams plp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            plp.topMargin = UiTheme.dp(this, 8);
            bPickSpool.setOnClickListener(v -> showPickSpoolForPrinterSlotDialog(p, null));
            spoolCard.addView(bPickSpool, plp);
        }
        col.addView(spoolCard);

        // 3. Temperatures & Fan Control Card
        LinearLayout tempCard = UiTheme.makeCard(this, 14);
        LinearLayout.LayoutParams tclp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        tclp.topMargin = UiTheme.dp(this, 12);
        tempCard.setLayoutParams(tclp);
        tempCard.addView(UiTheme.makeTitle(this, "Temperaturen & Lüfter (Tippen zum Setzen)", 15f));

        for (Models.TempReading tr : st.temps) {
            if (Double.isNaN(tr.temperature)) continue;
            boolean isHeater = st.heaters.contains(tr.rawHeater);
            String lbl = String.format(Locale.US, "%s: %.1f °C%s",
                    tr.label, tr.temperature, (!Double.isNaN(tr.target) && tr.target > 0) ? String.format(Locale.US, "  →  Ziel: %.0f °C", tr.target) : "");
            Button bTemp = UiTheme.makeButton(this, lbl, isHeater ? "" : "ghost");
            LinearLayout.LayoutParams tlp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            tlp.topMargin = UiTheme.dp(this, 6);
            if (isHeater && config.isControlsEnabled()) {
                bTemp.setOnClickListener(v -> showSetTempDialog(p, tr));
            }
            tempCard.addView(bTemp, tlp);
        }

        int fanPct = (int) Math.round(st.fanSpeed * 100.0);
        Button bFan = UiTheme.makeButton(this, "Bauteillüfter: " + fanPct + "% (Tippen zum Ändern)", "");
        LinearLayout.LayoutParams fanLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        fanLp.topMargin = UiTheme.dp(this, 6);
        bFan.setOnClickListener(v -> showSetFanDialog(p, fanPct));
        tempCard.addView(bFan, fanLp);
        col.addView(tempCard);

        // 4. Homing, XYZ/E Jogging & Z-Offset Babystepping Card
        if (config.isControlsEnabled()) {
            LinearLayout moveCard = UiTheme.makeCard(this, 14);
            LinearLayout.LayoutParams mclp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            mclp.topMargin = UiTheme.dp(this, 12);
            moveCard.setLayoutParams(mclp);
            moveCard.addView(UiTheme.makeTitle(this, "Homing, Achsen-Jog & Z-Offset", 15f));

            LinearLayout homeRow = new LinearLayout(this);
            homeRow.setOrientation(LinearLayout.HORIZONTAL);
            homeRow.setPadding(0, UiTheme.dp(this, 8), 0, UiTheme.dp(this, 8));
            String[][] homes = new String[][]{{"Alle", ""}, {"Home X", "X"}, {"Home Y", "Y"}, {"Home Z", "Z"}};
            for (int i = 0; i < homes.length; i++) {
                final String ax = homes[i][1];
                Button bh = UiTheme.makeButton(this, homes[i][0], i == 0 ? "primary" : "");
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
                if (i > 0) lp.leftMargin = UiTheme.dp(this, 6);
                bh.setOnClickListener(v -> runAsync(() -> ApiClient.homeAxes(p, ax), r -> toast("Homing " + (ax.isEmpty() ? "XYZ" : ax) + " gesendet")));
                homeRow.addView(bh, lp);
            }
            moveCard.addView(homeRow);

            // Step size selector
            LinearLayout stepRow = new LinearLayout(this);
            stepRow.setOrientation(LinearLayout.HORIZONTAL);
            double[] steps = new double[]{0.1, 1.0, 10.0, 50.0};
            for (int i = 0; i < steps.length; i++) {
                final double sVal = steps[i];
                Button bs = UiTheme.makeButton(this, sVal + " mm", Math.abs(detailJogStep - sVal) < 0.01 ? "primary" : "ghost");
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
                if (i > 0) lp.leftMargin = UiTheme.dp(this, 6);
                bs.setOnClickListener(v -> {
                    detailJogStep = sVal;
                    renderPrinterDetailView(p);
                });
                stepRow.addView(bs, lp);
            }
            moveCard.addView(stepRow);

            // Jog buttons
            String[][][] jogGrid = new String[][][]{
                {{"X -", "X", "-1"}, {"X +", "X", "1"}, {"Y -", "Y", "-1"}, {"Y +", "Y", "1"}},
                {{"Z -", "Z", "-1"}, {"Z +", "Z", "1"}, {"Extrude", "E", "1"}, {"Retract", "E", "-1"}}
            };
            for (String[][] rowDef : jogGrid) {
                LinearLayout jr = new LinearLayout(this);
                jr.setOrientation(LinearLayout.HORIZONTAL);
                jr.setPadding(0, UiTheme.dp(this, 6), 0, 0);
                for (int i = 0; i < rowDef.length; i++) {
                    final String axis = rowDef[i][1];
                    final int dir = Integer.parseInt(rowDef[i][2]);
                    Button bj = UiTheme.makeButton(this, rowDef[i][0], "");
                    LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
                    if (i > 0) lp.leftMargin = UiTheme.dp(this, 6);
                    bj.setOnClickListener(v -> {
                        int spd = "Z".equals(axis) ? 600 : ("E".equals(axis) ? 300 : 3000);
                        runAsync(() -> ApiClient.jogAxis(p, axis, dir * detailJogStep, spd), r -> toast(axis + " " + (dir * detailJogStep) + "mm"));
                    });
                    jr.addView(bj, lp);
                }
                moveCard.addView(jr);
            }

            // Z-Offset Babystepping
            LinearLayout zRow = new LinearLayout(this);
            zRow.setOrientation(LinearLayout.HORIZONTAL);
            zRow.setPadding(0, UiTheme.dp(this, 8), 0, 0);
            double[] zDeltas = new double[]{-0.05, -0.01, 0.0, +0.01, +0.05};
            for (int i = 0; i < zDeltas.length; i++) {
                final double zd = zDeltas[i];
                final boolean isReset = (zd == 0.0);
                Button bz = UiTheme.makeButton(this, isReset ? "Z=0" : String.format(Locale.US, "%+.2f", zd), isReset ? "ghost" : "");
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
                if (i > 0) lp.leftMargin = UiTheme.dp(this, 4);
                bz.setOnClickListener(v -> runAsync(() -> ApiClient.adjustZOffset(p, zd, isReset), r -> {
                    toast("Z-Offset angepasst");
                    pollAllPrinters();
                }));
                zRow.addView(bz, lp);
            }
            moveCard.addView(zRow);
            col.addView(moveCard);
        }

        // 5. G-Code Files & Console Quick Actions Card
        LinearLayout toolsCard = UiTheme.makeCard(this, 14);
        LinearLayout.LayoutParams toolLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        toolLp.topMargin = UiTheme.dp(this, 12);
        toolsCard.setLayoutParams(toolLp);
        toolsCard.addView(UiTheme.makeTitle(this, "G-Code Dateimanager & Konsole", 15f));

        Button bFiles = UiTheme.makeButton(this, "G-Code Dateien auf Drucker öffnen …", "primary");
        LinearLayout.LayoutParams flp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        flp.topMargin = UiTheme.dp(this, 8);
        bFiles.setOnClickListener(v -> showRemoteFilesDialog(p));
        toolsCard.addView(bFiles, flp);

        Button bUpload = UiTheme.makeButton(this, ".gcode vom Smartphone hochladen …", "");
        LinearLayout.LayoutParams ulp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        ulp.topMargin = UiTheme.dp(this, 6);
        bUpload.setOnClickListener(v -> promptUploadGcode(p));
        toolsCard.addView(bUpload, ulp);

        Button bConsole = UiTheme.makeButton(this, "⌨ Klipper G-Code Konsole & Makros …", "");
        LinearLayout.LayoutParams colp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        colp.topMargin = UiTheme.dp(this, 6);
        bConsole.setOnClickListener(v -> showGcodeConsoleDialog(p));
        toolsCard.addView(bConsole, colp);

        col.addView(toolsCard);

        sc.addView(col);
        contentContainer.removeAllViews();
        contentContainer.addView(sc);
    }

    private void sendControlAction(Models.Printer p, String action) {
        if ("cancel".equals(action) || "emergency_stop".equals(action)) {
            new AlertDialog.Builder(this)
                .setTitle("Aktion bestätigen")
                .setMessage("Soll „" + action + "“ wirklich auf " + p.name + " ausgeführt werden?")
                .setPositiveButton("Ja, ausführen", (d, w) -> runAsync(() -> ApiClient.controlAction(p, action), r -> {
                    toast("" + action + " ausgeführt");
                    pollAllPrinters();
                }))
                .setNegativeButton("Abbrechen", null)
                .show();
            return;
        }
        runAsync(() -> ApiClient.controlAction(p, action), r -> {
            toast("" + action + " ausgeführt");
            pollAllPrinters();
        });
    }

    private void showPickSpoolForPrinterSlotDialog(Models.Printer p, Integer channel) {
        if (spools.isEmpty()) {
            toast("Keine Spulen in Spoolman geladen.");
            return;
        }
        String[] items = new String[spools.size() + 1];
        items[0] = "— Keine Spule (Slot leeren) —";
        for (int i = 0; i < spools.size(); i++) {
            Models.Spool s = spools.get(i);
            items[i + 1] = String.format(Locale.US, "%s (%.0f g)", s.getDisplayName(), s.remainingWeight);
        }
        new AlertDialog.Builder(this)
            .setTitle(p.name + (channel != null ? " · Slot T" + channel : " · Aktive Spule"))
            .setItems(items, (d, which) -> {
                final Integer spoolId = which == 0 ? 0 : spools.get(which - 1).id;
                runAsync(() -> {
                    SpoolmanClient.assignSpoolToPrinter(p, spoolId, channel);
                    if (channel == null || channel == 0) {
                        config.setLocalPrinterSpool(p.id, spoolId);
                    }
                    return true;
                }, res -> {
                    toast("Spule zugewiesen!");
                    refreshSpoolmanData();
                    pollAllPrinters();
                });
            })
            .show();
    }

    private void showSetTempDialog(Models.Printer p, Models.TempReading tr) {
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        int pad = UiTheme.dp(this, 16);
        col.setPadding(pad, pad, pad, pad);

        EditText et = UiTheme.makeInput(this, "Zieltemperatur in °C (0 = Aus)", !Double.isNaN(tr.target) && tr.target > 0 ? String.format(Locale.US, "%.0f", tr.target) : "210");
        et.setInputType(InputType.TYPE_CLASS_NUMBER);
        col.addView(et);

        // Presets
        LinearLayout presets = new LinearLayout(this);
        presets.setOrientation(LinearLayout.HORIZONTAL);
        presets.setPadding(0, UiTheme.dp(this, 8), 0, 0);
        int[] vals = "heater_bed".equals(tr.rawHeater) ? new int[]{0, 55, 60, 75, 100} : new int[]{0, 200, 215, 240, 260};
        for (int v : vals) {
            Button b = UiTheme.makeButton(this, v + "°", "ghost");
            b.setOnClickListener(vw -> et.setText(String.valueOf(v)));
            presets.addView(b, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        }
        col.addView(presets);

        new AlertDialog.Builder(this)
            .setTitle("" + tr.label + " setzen")
            .setView(col)
            .setPositiveButton("Setzen", (d, w) -> {
                try {
                    double target = Double.parseDouble(et.getText().toString().trim());
                    runAsync(() -> ApiClient.setHeaterTemp(p, tr.rawHeater, target), r -> {
                        toast("" + tr.label + " → " + target + " °C");
                        pollAllPrinters();
                    });
                } catch (Exception ignored) {
                }
            })
            .setNegativeButton("Abbrechen", null)
            .show();
    }

    private void showSetFanDialog(Models.Printer p, int currentPct) {
        String[] opts = new String[]{"0% (Aus)", "25%", "50%", "75%", "100% (Max)"};
        int[] vals = new int[]{0, 25, 50, 75, 100};
        new AlertDialog.Builder(this)
            .setTitle("Lüftergeschwindigkeit (" + currentPct + "%)")
            .setItems(opts, (d, which) -> {
                int pct = vals[which];
                runAsync(() -> ApiClient.setFanPercent(p, pct), r -> {
                    toast("Lüfter auf " + pct + "% gesetzt");
                    pollAllPrinters();
                });
            })
            .show();
    }

    private void showRemoteFilesDialog(Models.Printer p) {
        runAsync(() -> ApiClient.listRemoteFiles(p), files -> {
            if (files == null || files.isEmpty()) {
                toast("Keine G-Code Dateien auf " + p.name + " gefunden.");
                return;
            }
            String[] names = new String[Math.min(files.size(), 50)];
            for (int i = 0; i < names.length; i++) {
                Models.RemoteFile rf = files.get(i);
                names[i] = rf.path + String.format(Locale.US, " (%.1f MB)", rf.size / (1024.0 * 1024.0));
            }
            new AlertDialog.Builder(this)
                .setTitle("G-Code Dateien auf " + p.name)
                .setItems(names, (d, which) -> {
                    Models.RemoteFile chosen = files.get(which);
                    new AlertDialog.Builder(this)
                        .setTitle(chosen.path)
                        .setItems(new String[]{"▶ Jetzt drucken", "Datei löschen"}, (d2, actIdx) -> {
                            if (actIdx == 0) {
                                runAsync(() -> ApiClient.startPrint(p, chosen.path), r -> {
                                    toast("▶ Druck gestartet: " + chosen.path);
                                    pollAllPrinters();
                                });
                            } else {
                                runAsync(() -> ApiClient.deleteRemoteFile(p, chosen.path), r -> toast("Gelöscht: " + chosen.path));
                            }
                        })
                        .show();
                })
                .setNegativeButton("Schließen", null)
                .show();
        });
    }

    private void promptUploadGcode(Models.Printer p) {
        new AlertDialog.Builder(this)
            .setTitle("G-Code hochladen auf " + p.name)
            .setItems(new String[]{"Nur hochladen", "▶ Hochladen & direkt drucken"}, (d, which) -> {
                pendingUploadPrinter = p;
                pendingUploadStartNow = (which == 1);
                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.setType("*/*");
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                startActivityForResult(Intent.createChooser(intent, "G-Code Datei wählen"), REQ_PICK_GCODE);
            })
            .show();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQ_PICK_GCODE && resultCode == RESULT_OK && data != null && data.getData() != null && pendingUploadPrinter != null) {
            final Uri uri = data.getData();
            final Models.Printer targetPrinter = pendingUploadPrinter;
            final boolean startNow = pendingUploadStartNow;
            runAsync(() -> {
                String fname = "upload.gcode";
                try (Cursor c = getContentResolver().query(uri, null, null, null, null)) {
                    if (c != null && c.moveToFirst()) {
                        int idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                        if (idx >= 0) fname = c.getString(idx);
                    }
                }
                ByteArrayOutputStream bos = new ByteArrayOutputStream();
                try (InputStream is = getContentResolver().openInputStream(uri)) {
                    byte[] buf = new byte[16384];
                    int n;
                    while (is != null && (n = is.read(buf)) != -1) {
                        bos.write(buf, 0, n);
                    }
                }
                return ApiClient.uploadGcodeBytes(targetPrinter, fname, bos.toByteArray(), startNow);
            }, res -> {
                toast("G-Code erfolgreich auf " + targetPrinter.name + " hochgeladen!");
                pollAllPrinters();
            });
        }
    }

    private void showGcodeConsoleDialog(Models.Printer p) {
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        int pad = UiTheme.dp(this, 14);
        col.setPadding(pad, pad, pad, pad);

        TextView logTv = UiTheme.makeDim(this, "Lade G-Code Verlauf …", 11.5f);
        logTv.setTypeface(Typeface.MONOSPACE);
        ScrollView logScroll = new ScrollView(this);
        logScroll.addView(logTv);
        col.addView(logScroll, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, UiTheme.dp(this, 200)));

        EditText cmdInput = UiTheme.makeInput(this, "G-Code eingeben (z.B. G28, M114, SET_SPOOL_ID …)", "");
        col.addView(cmdInput);

        Runnable reloadLog = () -> runAsync(() -> ApiClient.getGcodeStore(p, 40), lines -> {
            StringBuilder sb = new StringBuilder();
            for (String l : lines) sb.append(l).append("\n");
            logTv.setText(sb.length() > 0 ? sb.toString() : "Keine Konsolenausgabe.");
            logScroll.post(() -> logScroll.fullScroll(View.FOCUS_DOWN));
        });
        reloadLog.run();

        new AlertDialog.Builder(this)
            .setTitle("⌨ G-Code Konsole · " + p.name)
            .setView(col)
            .setPositiveButton("Senden", (d, w) -> {
                String cmd = cmdInput.getText().toString().trim();
                if (!cmd.isEmpty()) {
                    runAsync(() -> ApiClient.sendGcode(p, cmd), r -> toast("Gesendet: " + cmd));
                }
            })
            .setNeutralButton("Makros …", (d, w) -> {
                runAsync(() -> ApiClient.listMacros(p), macros -> {
                    if (macros == null || macros.isEmpty()) {
                        toast("Keine Klipper-Makros gefunden.");
                        return;
                    }
                    String[] mArr = macros.toArray(new String[0]);
                    new AlertDialog.Builder(this)
                        .setTitle("Klipper Makro ausführen")
                        .setItems(mArr, (d2, idx) -> {
                            String m = mArr[idx];
                            runAsync(() -> ApiClient.sendGcode(p, m), r -> toast("Makro ausgeführt: " + m));
                        })
                        .show();
                });
            })
            .setNegativeButton("Schließen", null)
            .show();
    }

    // ---------- Add / Edit Printer & Network Discovery Dialog ----------

    private void showPrinterDialog(Models.Printer existing) {
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        int pad = UiTheme.dp(this, 16);
        col.setPadding(pad, pad, pad, pad);

        EditText nameInput = UiTheme.makeInput(this, "Name (z.B. U1, Q2, Voron)", existing != null ? existing.name : "");
        EditText hostInput = UiTheme.makeInput(this, "IP oder Hostname (z.B. 192.168.178.143)", existing != null ? existing.host : "");
        EditText portInput = UiTheme.makeInput(this, "Port (Standard 80 oder 7125)", existing != null ? String.valueOf(existing.port) : "80");
        portInput.setInputType(InputType.TYPE_CLASS_NUMBER);
        EditText displayInput = UiTheme.makeInput(this, "Display-URL optional (z.B. http://192.168.178.165:18080/)", existing != null ? existing.displayUrl : "");
        EditText tokenInput = UiTheme.makeInput(this, "API-Key optional", existing != null ? existing.token : "");

        col.addView(UiTheme.makeDim(this, "Druckername:", 12f));
        col.addView(nameInput);
        col.addView(UiTheme.makeDim(this, "IP-Adresse / Host:", 12f));
        col.addView(hostInput);
        col.addView(UiTheme.makeDim(this, "Moonraker-Port:", 12f));
        col.addView(portInput);
        col.addView(UiTheme.makeDim(this, "Display-URL (optional):", 12f));
        col.addView(displayInput);
        col.addView(UiTheme.makeDim(this, "API-Token (optional):", 12f));
        col.addView(tokenInput);

        Button bScan = UiTheme.makeButton(this, "Im WLAN nach Druckern scannen …", "ghost");
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        slp.topMargin = UiTheme.dp(this, 10);
        bScan.setOnClickListener(v -> {
            toast("Scanne lokales Netzwerk nach Moonraker-Druckern …");
            runAsync(ApiClient::discoverPrinters, found -> {
                if (found == null || found.isEmpty()) {
                    toast("Keine Drucker im Subnetz gefunden.");
                    return;
                }
                String[] labels = new String[found.size()];
                for (int i = 0; i < found.size(); i++) {
                    Models.Printer fp = found.get(i);
                    labels[i] = fp.name + " (" + fp.host + ":" + fp.port + ")";
                }
                new AlertDialog.Builder(this)
                    .setTitle("Gefundene Drucker")
                    .setItems(labels, (d2, idx) -> {
                        Models.Printer fp = found.get(idx);
                        nameInput.setText(fp.name);
                        hostInput.setText(fp.host);
                        portInput.setText(String.valueOf(fp.port));
                    })
                    .show();
            });
        });
        col.addView(bScan, slp);

        AlertDialog.Builder b = new AlertDialog.Builder(this)
            .setTitle(existing != null ? "Drucker bearbeiten" : "+ Drucker hinzufügen")
            .setView(col)
            .setPositiveButton("Speichern", (d, w) -> {
                String name = nameInput.getText().toString().trim();
                String host = hostInput.getText().toString().trim();
                int port = 80;
                try {
                    port = Integer.parseInt(portInput.getText().toString().trim());
                } catch (Exception ignored) {
                }
                if (host.isEmpty()) {
                    toast("Bitte IP-Adresse oder Hostnamen angeben.");
                    return;
                }
                if (name.isEmpty()) name = host;
                if (existing != null) {
                    existing.name = name;
                    existing.host = host;
                    existing.port = port;
                    existing.displayUrl = displayInput.getText().toString().trim();
                    existing.token = tokenInput.getText().toString().trim();
                } else {
                    printers.add(new Models.Printer(
                        UUID.randomUUID().toString().substring(0, 8),
                        name, host, port,
                        tokenInput.getText().toString().trim(),
                        false,
                        displayInput.getText().toString().trim()
                    ));
                }
                config.savePrinters(printers);
                pollAllPrinters();
                refreshSpoolmanData();
                renderPrintersTab();
            })
            .setNegativeButton("Abbrechen", null);

        if (existing != null) {
            b.setNeutralButton("Löschen", (d, w) -> {
                printers.remove(existing);
                config.savePrinters(printers);
                renderPrintersTab();
            });
        }
        b.show();
    }

    // =========================================================================
    // TAB 2: SPOOLMAN FILAMENT-MANAGER
    // =========================================================================

    private void renderSpoolmanTab() {
        contentContainer.removeAllViews();
        ScrollView sc = new ScrollView(this);
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        int pad = UiTheme.dp(this, 14);
        page.setPadding(pad, pad, pad, pad);

        // Header Row
        LinearLayout top = new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout tCol = new LinearLayout(this);
        tCol.setOrientation(LinearLayout.VERTICAL);
        tCol.addView(UiTheme.makeTitle(this, "Spoolman Manager", 20f));
        spoolmanServerBadge = UiTheme.makeDim(this, config.getSpoolmanUrl(), 12f);
        tCol.addView(spoolmanServerBadge);
        top.addView(tCol, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        Button bRefresh = UiTheme.makeButton(this, "Sync", "ghost");
        bRefresh.setOnClickListener(v -> {
            toast("Synchronisiere Spoolman …");
            refreshSpoolmanData();
        });
        top.addView(bRefresh);

        Button bNewSpool = UiTheme.makeButton(this, "+ Spule", "primary");
        LinearLayout.LayoutParams nlp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        nlp.leftMargin = UiTheme.dp(this, 6);
        bNewSpool.setOnClickListener(v -> SpoolmanDialogs.showSpoolEditDialog(this, null));
        top.addView(bNewSpool, nlp);
        page.addView(top);

        // 2x2 KPI Grid
        LinearLayout kpiRow1 = new LinearLayout(this);
        kpiRow1.setOrientation(LinearLayout.HORIZONTAL);
        kpiRow1.setPadding(0, UiTheme.dp(this, 10), 0, 0);
        kpiSpoolsVal = new TextView(this);
        kpiWeightVal = new TextView(this);
        kpiRow1.addView(makeKpiBox("Aktive Spulen", kpiSpoolsVal, UiTheme.ACCENT), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        LinearLayout.LayoutParams klp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        klp.leftMargin = UiTheme.dp(this, 8);
        kpiRow1.addView(makeKpiBox("Gesamtbestand", kpiWeightVal, UiTheme.GREEN), klp);
        page.addView(kpiRow1);

        LinearLayout kpiRow2 = new LinearLayout(this);
        kpiRow2.setOrientation(LinearLayout.HORIZONTAL);
        kpiRow2.setPadding(0, UiTheme.dp(this, 8), 0, UiTheme.dp(this, 10));
        kpiValueVal = new TextView(this);
        kpiLowVal = new TextView(this);
        kpiRow2.addView(makeKpiBox("Bestandswert", kpiValueVal, Color.parseColor("#A855F7")), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        kpiRow2.addView(makeKpiBox("Fast leer (<150g)", kpiLowVal, UiTheme.YELLOW), klp);
        page.addView(kpiRow2);

        // Sub-Tab Selector Pills
        LinearLayout subTabs = new LinearLayout(this);
        subTabs.setOrientation(LinearLayout.HORIZONTAL);
        String[] stLabels = new String[]{"Spulen", "Filamente", "Hersteller", "Slots/NFC"};
        for (int i = 0; i < stLabels.length; i++) {
            final int sIdx = i;
            Button b = UiTheme.makeButton(this, stLabels[i], spoolmanSubTab == i ? "primary" : "");
            b.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11.5f);
            b.setPadding(UiTheme.dp(this, 6), UiTheme.dp(this, 6), UiTheme.dp(this, 6), UiTheme.dp(this, 6));
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
            if (i > 0) lp.leftMargin = UiTheme.dp(this, 5);
            b.setOnClickListener(v -> {
                spoolmanSubTab = sIdx;
                renderSpoolmanTab();
            });
            subTabs.addView(b, lp);
        }
        page.addView(subTabs);

        // Search & Action Bar
        if (spoolmanSubTab == 0) {
            LinearLayout filterRow = new LinearLayout(this);
            filterRow.setOrientation(LinearLayout.HORIZONTAL);
            filterRow.setPadding(0, UiTheme.dp(this, 10), 0, UiTheme.dp(this, 6));
            EditText searchEt = UiTheme.makeInput(this, "Spule, Farbe, Material, NFC suchen …", spoolSearchQuery);
            searchEt.addTextChangedListener(new UiTheme.SimpleTextWatcher(txt -> {
                spoolSearchQuery = txt;
                populateSpoolmanSubTab();
            }));
            filterRow.addView(searchEt, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
            page.addView(filterRow);
        } else if (spoolmanSubTab == 1) {
            LinearLayout fActRow = new LinearLayout(this);
            fActRow.setOrientation(LinearLayout.HORIZONTAL);
            fActRow.setPadding(0, UiTheme.dp(this, 10), 0, UiTheme.dp(this, 6));
            Button bAddFil = UiTheme.makeButton(this, "+ Neues Filament", "primary");
            Button bCatalog = UiTheme.makeButton(this, "SpoolmanDB Import", "");
            bAddFil.setOnClickListener(v -> SpoolmanDialogs.showFilamentEditDialog(this, null));
            bCatalog.setOnClickListener(v -> SpoolmanDialogs.showExternalCatalogDialog(this));
            fActRow.addView(bAddFil, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
            LinearLayout.LayoutParams clp2 = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
            clp2.leftMargin = UiTheme.dp(this, 8);
            fActRow.addView(bCatalog, clp2);
            page.addView(fActRow);
        } else if (spoolmanSubTab == 2) {
            Button bAddVen = UiTheme.makeButton(this, "+ Neuer Hersteller", "primary");
            LinearLayout.LayoutParams vlp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            vlp.topMargin = UiTheme.dp(this, 10);
            bAddVen.setOnClickListener(v -> SpoolmanDialogs.showVendorEditDialog(this, null));
            page.addView(bAddVen, vlp);
        }

        spoolmanListContainer = new LinearLayout(this);
        spoolmanListContainer.setOrientation(LinearLayout.VERTICAL);
        spoolmanListContainer.setPadding(0, UiTheme.dp(this, 6), 0, UiTheme.dp(this, 20));
        page.addView(spoolmanListContainer);

        sc.addView(page);
        contentContainer.addView(sc);
        updateSpoolmanUI();
    }

    private LinearLayout makeKpiBox(String label, TextView valTv, int color) {
        LinearLayout box = UiTheme.makeAltCard(this, 11);
        valTv.setText("—");
        valTv.setTextColor(color);
        valTv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 17f);
        valTv.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
        box.addView(valTv);
        box.addView(UiTheme.makeDim(this, label, 11.5f));
        return box;
    }

    private void updateSpoolmanUI() {
        if (kpiSpoolsVal == null || spoolmanListContainer == null) return;

        if (spoolmanServerBadge != null) {
            spoolmanServerBadge.setText(spoolmanOnline
                    ? "● Verbunden (" + spoolmanVersion + ") · " + config.getSpoolmanUrl()
                    : "○ Nicht verbunden · " + config.getSpoolmanUrl());
            spoolmanServerBadge.setTextColor(spoolmanOnline ? UiTheme.GREEN : UiTheme.RED);
        }

        int activeCount = 0;
        int lowCount = 0;
        double totalWeightG = 0.0;
        double totalLengthM = 0.0;
        double totalValEur = 0.0;

        for (Models.Spool s : spools) {
            if (s.archived) continue;
            activeCount++;
            totalWeightG += s.remainingWeight;
            totalLengthM += s.remainingLength / 1000.0;
            if (s.remainingWeight < 150.0) lowCount++;
            Double pr = s.getEffectivePrice();
            if (pr != null && pr > 0) {
                totalValEur += pr * s.getFillFraction();
            }
        }

        kpiSpoolsVal.setText(activeCount + " Spulen");
        kpiWeightVal.setText(String.format(Locale.US, "%.2f kg (%.0f m)", totalWeightG / 1000.0, totalLengthM));
        kpiValueVal.setText(String.format(Locale.US, "%.2f €", totalValEur));
        kpiLowVal.setText(lowCount + " Spulen");

        populateSpoolmanSubTab();
    }

    private void populateSpoolmanSubTab() {
        if (spoolmanListContainer == null) return;
        spoolmanListContainer.removeAllViews();

        if (!spoolmanOnline && spools.isEmpty()) {
            LinearLayout errCard = UiTheme.makeCard(this, 18);
            errCard.addView(UiTheme.makeTitle(this, "Spoolman nicht erreichbar", 15f));
            errCard.addView(UiTheme.makeDim(this, "Prüfe im Tab „Setup“ die Spoolman Server-URL (" + config.getSpoolmanUrl() + ").", 13f));
            spoolmanListContainer.addView(errCard);
            return;
        }

        if (spoolmanSubTab == 0) {
            String q = spoolSearchQuery != null ? spoolSearchQuery.trim().toLowerCase(Locale.ROOT) : "";
            for (Models.Spool s : spools) {
                String hay = (s.getDisplayName() + " " + (s.filament != null ? s.filament.material : "")
                        + " " + s.location + " " + s.cardUids + " " + s.comment).toLowerCase(Locale.ROOT);
                if (!q.isEmpty() && !hay.contains(q)) continue;

                LinearLayout card = UiTheme.makeCard(this, 12);
                LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                clp.topMargin = UiTheme.dp(this, 8);
                card.setLayoutParams(clp);

                LinearLayout row = new LinearLayout(this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                row.setGravity(Gravity.CENTER_VERTICAL);

                UiTheme.SpoolIconView icon = new UiTheme.SpoolIconView(this, 44);
                icon.setSpoolData(s.getColors(), s.getFillFraction());
                row.addView(icon);

                LinearLayout info = new LinearLayout(this);
                info.setOrientation(LinearLayout.VERTICAL);
                info.setPadding(UiTheme.dp(this, 12), 0, UiTheme.dp(this, 8), 0);
                info.addView(UiTheme.makeTitle(this, s.getDisplayName(), 14.5f));
                String sub = String.format(Locale.US, "%s · %.1f g / %.0f g (%.0f%%) · %.0f m",
                        s.filament != null ? s.filament.material : "PLA",
                        s.remainingWeight, s.getEffectiveInitialWeight(), s.getFillFraction() * 100.0, s.remainingLength / 1000.0);
                if (s.location != null && !s.location.isEmpty()) sub += " · " + s.location;
                info.addView(UiTheme.makeDim(this, sub, 12f));

                UiTheme.LevelBarView bar = new UiTheme.LevelBarView(this, 7);
                LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, UiTheme.dp(this, 7));
                blp.topMargin = UiTheme.dp(this, 6);
                bar.setProgress(s.getFillFraction(), s.remainingWeight < 150 ? UiTheme.YELLOW : UiTheme.ACCENT);
                info.addView(bar, blp);

                row.addView(info, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
                card.addView(row);

                card.setOnClickListener(v -> SpoolmanDialogs.showSpoolSheet(this, s));
                spoolmanListContainer.addView(card);
            }
        } else if (spoolmanSubTab == 1) {
            for (Models.Filament f : filaments) {
                LinearLayout card = UiTheme.makeCard(this, 12);
                LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                clp.topMargin = UiTheme.dp(this, 8);
                card.setLayoutParams(clp);

                LinearLayout row = new LinearLayout(this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                row.setGravity(Gravity.CENTER_VERTICAL);

                UiTheme.SpoolIconView icon = new UiTheme.SpoolIconView(this, 38);
                icon.setSpoolData(f.getColors(), 1.0);
                row.addView(icon);

                LinearLayout info = new LinearLayout(this);
                info.setOrientation(LinearLayout.VERTICAL);
                info.setPadding(UiTheme.dp(this, 12), 0, UiTheme.dp(this, 8), 0);
                info.addView(UiTheme.makeTitle(this, "#" + f.id + " · " + f.getDisplayName(), 14.5f));
                info.addView(UiTheme.makeDim(this, String.format(Locale.US, "%s · %.2f g/cm³ · %.0f g · Düse %s°C / Bett %s°C",
                        f.material, f.density, f.weight,
                        f.extruderTemp != null ? f.extruderTemp : "—",
                        f.bedTemp != null ? f.bedTemp : "—"), 12f));
                row.addView(info, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

                Button bEdit = UiTheme.makeButton(this, "", "ghost");
                bEdit.setOnClickListener(v -> SpoolmanDialogs.showFilamentEditDialog(this, f));
                row.addView(bEdit);

                card.addView(row);
                spoolmanListContainer.addView(card);
            }
        } else if (spoolmanSubTab == 2) {
            for (Models.Vendor v : vendors) {
                LinearLayout card = UiTheme.makeCard(this, 12);
                LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                clp.topMargin = UiTheme.dp(this, 8);
                card.setLayoutParams(clp);

                LinearLayout row = new LinearLayout(this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                row.setGravity(Gravity.CENTER_VERTICAL);

                LinearLayout info = new LinearLayout(this);
                info.setOrientation(LinearLayout.VERTICAL);
                info.addView(UiTheme.makeTitle(this, "#" + v.id + " · " + v.name, 15f));
                info.addView(UiTheme.makeDim(this, "Leerspulen-Tara: " + (v.emptySpoolWeight != null ? String.format(Locale.US, "%.0f g", v.emptySpoolWeight) : "—"), 12f));
                row.addView(info, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

                Button bEdit = UiTheme.makeButton(this, "", "ghost");
                bEdit.setOnClickListener(vw -> SpoolmanDialogs.showVendorEditDialog(this, v));
                row.addView(bEdit);

                card.addView(row);
                spoolmanListContainer.addView(card);
            }
        } else if (spoolmanSubTab == 3) {
            for (Models.Printer p : printers) {
                Models.PrinterSpoolState ps = printerSpoolStates.get(p.id);
                LinearLayout pCard = UiTheme.makeCard(this, 14);
                LinearLayout.LayoutParams pclp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                pclp.topMargin = UiTheme.dp(this, 10);
                pCard.setLayoutParams(pclp);

                pCard.addView(UiTheme.makeTitle(this, "" + p.name + " (" + p.host + ")", 16f));
                if (ps == null || !ps.online) {
                    pCard.addView(UiTheme.makeDim(this, "Drucker aktuell offline.", 12.5f));
                } else if (ps.slots.isEmpty()) {
                    Models.Spool actS = resolveActiveSpoolForPrinter(p, statuses.get(p.id));
                    pCard.addView(UiTheme.makeDim(this, "Aktive Spule: " + (actS != null ? actS.getDisplayName() : "Keine"), 13f));
                    Button bSet = UiTheme.makeButton(this, "Spule zuweisen …", "primary");
                    LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                    blp.topMargin = UiTheme.dp(this, 8);
                    bSet.setOnClickListener(v -> showPickSpoolForPrinterSlotDialog(p, null));
                    pCard.addView(bSet, blp);
                } else {
                    for (Models.PrinterSlot sl : ps.slots) {
                        Models.Spool sp = sl.spoolId != null ? spoolById.get(sl.spoolId) : null;
                        LinearLayout slBox = UiTheme.makeAltCard(this, 10);
                        LinearLayout.LayoutParams sllp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                        sllp.topMargin = UiTheme.dp(this, 8);
                        slBox.setLayoutParams(sllp);

                        slBox.addView(UiTheme.makeTitle(this, "Slot " + sl.label + " (" + sl.extruder + ")" + (sl.active ? " AKTIV" : ""), 14f));
                        slBox.addView(UiTheme.makeDim(this,
                                "Spule: " + (sp != null ? sp.getDisplayName() + String.format(Locale.US, " (%.0f g)", sp.remainingWeight) : "Nicht zugewiesen")
                                + "\nSensor: " + (sl.exist ? "Filament erkannt (" + sl.type + ")" : "○ Kein Filament")
                                + (!sl.cardUid.isEmpty() ? " · NFC UID: " + sl.cardUid : ""), 12f));

                        Button bAssign = UiTheme.makeButton(this, "Spule für " + sl.label + " wählen …", sl.active ? "primary" : "");
                        LinearLayout.LayoutParams alp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                        alp.topMargin = UiTheme.dp(this, 6);
                        bAssign.setOnClickListener(v -> showPickSpoolForPrinterSlotDialog(p, sl.channel));
                        slBox.addView(bAssign, alp);
                        pCard.addView(slBox);
                    }
                }
                spoolmanListContainer.addView(pCard);
            }
        }
    }

    // =========================================================================
    // TAB 3: STATISTIK & KOSTENRECHNER
    // =========================================================================

    private void renderStatsTab() {
        contentContainer.removeAllViews();
        ScrollView sc = new ScrollView(this);
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        int pad = UiTheme.dp(this, 14);
        page.setPadding(pad, pad, pad, pad);

        page.addView(UiTheme.makeTitle(this, "Statistik & Kostenrechner", 20f));

        if (printers.isEmpty()) {
            page.addView(UiTheme.makeDim(this, "Bitte füge zuerst einen Drucker hinzu.", 13f));
            sc.addView(page);
            contentContainer.addView(sc);
            return;
        }

        // Printer selector pills
        LinearLayout pRow = new LinearLayout(this);
        pRow.setOrientation(LinearLayout.HORIZONTAL);
        pRow.setPadding(0, UiTheme.dp(this, 10), 0, UiTheme.dp(this, 10));
        for (int i = 0; i < printers.size(); i++) {
            final int idx = i;
            Models.Printer p = printers.get(i);
            Button b = UiTheme.makeButton(this, "" + p.name, statsPrinterIndex == i ? "primary" : "");
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
            if (i > 0) lp.leftMargin = UiTheme.dp(this, 6);
            b.setOnClickListener(v -> {
                statsPrinterIndex = idx;
                renderStatsTab();
            });
            pRow.addView(b, lp);
        }
        page.addView(pRow);

        TextView kpiSummary = UiTheme.makeDim(this, "Lade Druckhistorie …", 13f);
        LinearLayout summaryCard = UiTheme.makeCard(this, 14);
        summaryCard.addView(kpiSummary);
        page.addView(summaryCard);

        // Cost calculator card
        LinearLayout costCard = UiTheme.makeCard(this, 14);
        LinearLayout.LayoutParams cclp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        cclp.topMargin = UiTheme.dp(this, 10);
        costCard.setLayoutParams(cclp);
        costCard.addView(UiTheme.makeTitle(this, "Kosten-Parameter", 15f));

        LinearLayout cInputs = new LinearLayout(this);
        cInputs.setOrientation(LinearLayout.HORIZONTAL);
        cInputs.setPadding(0, UiTheme.dp(this, 6), 0, UiTheme.dp(this, 6));
        EditText etKg = UiTheme.makeInput(this, "€/kg", String.valueOf(config.getCostEurPerKg()));
        EditText etW = UiTheme.makeInput(this, "Watt", String.valueOf(config.getCostWatts()));
        EditText etKwh = UiTheme.makeInput(this, "€/kWh", String.valueOf(config.getCostEurPerKwh()));
        cInputs.addView(etKg, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        LinearLayout.LayoutParams mlp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        mlp.leftMargin = UiTheme.dp(this, 6);
        cInputs.addView(etW, mlp);
        cInputs.addView(etKwh, mlp);
        costCard.addView(cInputs);

        Button bSpoolPrice = UiTheme.makeButton(this, "€/kg aus aktiver Spoolman-Spule übernehmen", "ghost");
        bSpoolPrice.setOnClickListener(v -> {
            Models.Printer p = printers.get(Math.min(statsPrinterIndex, printers.size() - 1));
            Models.Spool sp = resolveActiveSpoolForPrinter(p, statuses.get(p.id));
            if (sp != null && sp.getEffectivePrice() != null && sp.getEffectiveInitialWeight() > 0) {
                float eurKg = (float) (sp.getEffectivePrice() / (sp.getEffectiveInitialWeight() / 1000.0));
                config.setCostEurPerKg(eurKg);
                etKg.setText(String.format(Locale.US, "%.2f", eurKg));
                toast("" + String.format(Locale.US, "%.2f €/kg", eurKg) + " aus " + sp.getDisplayName() + " übernommen");
                renderStatsTab();
            } else {
                toast("Keine aktive Spule mit hinterlegtem Preis gefunden.");
            }
        });
        costCard.addView(bSpoolPrice);
        page.addView(costCard);

        // Monthly Chart
        UiTheme.MonthlyChartView chart = new UiTheme.MonthlyChartView(this);
        LinearLayout.LayoutParams chlp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, UiTheme.dp(this, 180));
        chlp.topMargin = UiTheme.dp(this, 10);
        page.addView(chart, chlp);

        // History List Container
        LinearLayout histBox = new LinearLayout(this);
        histBox.setOrientation(LinearLayout.VERTICAL);
        histBox.setPadding(0, UiTheme.dp(this, 10), 0, UiTheme.dp(this, 20));
        page.addView(histBox);

        sc.addView(page);
        contentContainer.addView(sc);

        Models.Printer target = printers.get(Math.min(statsPrinterIndex, printers.size() - 1));
        runAsync(() -> ApiClient.getHistory(target, 150), jobs -> {
            currentStatsJobs = jobs != null ? jobs : new ArrayList<>();
            int total = currentStatsJobs.size();
            int ok = 0;
            double hours = 0.0;
            double filMeters = 0.0;
            Map<String, Double> byMonth = new HashMap<>();
            SimpleDateFormat mFmt = new SimpleDateFormat("yyyy-MM", Locale.US);
            SimpleDateFormat dFmt = new SimpleDateFormat("dd.MM.yyyy HH:mm", Locale.getDefault());

            for (Models.PrintJob j : currentStatsJobs) {
                if ("completed".equals(j.status)) ok++;
                double h = j.totalDuration / 3600.0;
                hours += h;
                filMeters += j.filamentUsedMm / 1000.0;
                if (j.startTime > 0) {
                    String mk = mFmt.format(new Date(j.startTime * 1000L));
                    byMonth.put(mk, byMonth.getOrDefault(mk, 0.0) + h);
                }
            }
            double grams = filMeters * 2.98;
            double matCost = (grams / 1000.0) * config.getCostEurPerKg();
            double pwrCost = hours * (config.getCostWatts() / 1000.0) * config.getCostEurPerKwh();
            double totalCost = matCost + pwrCost + (hours * config.getCostWearPerHour());

            kpiSummary.setText(String.format(Locale.US,
                    "Drucke gesamt: %d (Erfolgsquote: %d%%)\nDruckzeit: %.1f h   ·   Filament: %.1f m (~%.0f g)\nGeschätzte Gesamtkosten: %.2f € (Material %.2f € · Strom %.2f €)",
                    total, total > 0 ? (ok * 100 / total) : 0, hours, filMeters, grams, totalCost, matCost, pwrCost));

            chart.setData(byMonth);

            histBox.removeAllViews();
            histBox.addView(UiTheme.makeTitle(this, "Letzte Druckaufträge", 15f));
            int lim = Math.min(currentStatsJobs.size(), 30);
            for (int i = 0; i < lim; i++) {
                Models.PrintJob j = currentStatsJobs.get(i);
                LinearLayout jCard = UiTheme.makeAltCard(this, 10);
                LinearLayout.LayoutParams jlp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                jlp.topMargin = UiTheme.dp(this, 6);
                jCard.setLayoutParams(jlp);
                jCard.addView(UiTheme.makeTitle(this, j.filename, 13.5f));
                String dt = j.startTime > 0 ? dFmt.format(new Date(j.startTime * 1000L)) : "—";
                jCard.addView(UiTheme.makeDim(this, String.format(Locale.US, "%s · Status: %s · %s · %.1f m",
                        dt, j.status, UiTheme.formatHms(j.totalDuration), j.filamentUsedMm / 1000.0), 12f));
                histBox.addView(jCard);
            }
        });
    }

    // =========================================================================
    // TAB 4: 3D-MODELLE BROWSER
    // =========================================================================

    private void renderModelsTab() {
        contentContainer.removeAllViews();
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        int pad = UiTheme.dp(this, 10);
        page.setPadding(pad, pad, pad, 0);

        // Site selector pills
        HorizontalScrollView hsv = new HorizontalScrollView(this);
        hsv.setHorizontalScrollBarEnabled(false);
        LinearLayout siteRow = new LinearLayout(this);
        siteRow.setOrientation(LinearLayout.HORIZONTAL);
        String[][] sites = new String[][]{
            {"Printables", "https://www.printables.com/model"},
            {"MakerWorld", "https://makerworld.com/de"},
            {"Thingiverse", "https://www.thingiverse.com"},
            {"Thangs", "https://thangs.com"},
            {"MyMiniFactory", "https://www.myminifactory.com"},
            {"Cults3D", "https://cults3d.com"}
        };
        for (int i = 0; i < sites.length; i++) {
            final String u = sites[i][1];
            Button b = UiTheme.makeButton(this, sites[i][0], i == 0 ? "primary" : "");
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            if (i > 0) lp.leftMargin = UiTheme.dp(this, 6);
            b.setOnClickListener(v -> {
                if (modelsWebView != null) modelsWebView.loadUrl(u);
                if (modelsUrlInput != null) modelsUrlInput.setText(u);
            });
            siteRow.addView(b, lp);
        }
        hsv.addView(siteRow);
        page.addView(hsv);

        modelsWebView = new WebView(this);
        WebSettings ws = modelsWebView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        modelsWebView.setWebViewClient(new WebViewClient());
        modelsWebView.setWebChromeClient(new WebChromeClient());
        modelsWebView.loadUrl(sites[0][1]);

        LinearLayout.LayoutParams wlp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f);
        wlp.topMargin = UiTheme.dp(this, 8);
        page.addView(modelsWebView, wlp);

        contentContainer.addView(page);
    }

    // =========================================================================
    // TAB 5: SETUP & BENACHRICHTIGUNGEN (inkl. Discord Webhook-Test)
    // =========================================================================

    private void renderSettingsTab() {
        contentContainer.removeAllViews();
        ScrollView sc = new ScrollView(this);
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        int pad = UiTheme.dp(this, 14);
        page.setPadding(pad, pad, pad, pad);

        page.addView(UiTheme.makeTitle(this, "Einstellungen & Integration", 20f));

        // 1. Spoolman Card
        LinearLayout smCard = UiTheme.makeCard(this, 14);
        LinearLayout.LayoutParams smlp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        smlp.topMargin = UiTheme.dp(this, 12);
        smCard.setLayoutParams(smlp);
        smCard.addView(UiTheme.makeTitle(this, "Spoolman Server", 16f));
        smCard.addView(UiTheme.makeDim(this, "Zentrale Filament- & Spulendatenbank im lokalen Netzwerk:", 12.5f));

        EditText smUrlInput = UiTheme.makeInput(this, "http://192.168.178.170:7912", config.getSpoolmanUrl());
        LinearLayout.LayoutParams inLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        inLp.topMargin = UiTheme.dp(this, 8);
        smCard.addView(smUrlInput, inLp);

        LinearLayout smBtns = new LinearLayout(this);
        smBtns.setOrientation(LinearLayout.HORIZONTAL);
        smBtns.setPadding(0, UiTheme.dp(this, 8), 0, 0);
        Button bDetectSm = UiTheme.makeButton(this, "Erkennen", "");
        Button bTestSm = UiTheme.makeButton(this, "Testen", "");
        Button bBackupSm = UiTheme.makeButton(this, "Backup", "ghost");

        bDetectSm.setOnClickListener(v -> runAsync(() -> SpoolmanClient.discoverUrl(printers), found -> {
            smUrlInput.setText(found);
            config.setSpoolmanUrl(found);
            toast("Gefunden: " + found);
            refreshSpoolmanData();
        }));
        bTestSm.setOnClickListener(v -> {
            String u = smUrlInput.getText().toString().trim();
            config.setSpoolmanUrl(u);
            runAsync(() -> SpoolmanClient.getInfo(u), info -> {
                toast("Spoolman v" + info.optString("version", "?") + " erreichbar!");
                refreshSpoolmanData();
            });
        });
        bBackupSm.setOnClickListener(v -> {
            String u = smUrlInput.getText().toString().trim();
            runAsync(() -> SpoolmanClient.triggerBackup(u), res -> toast("Spoolman DB-Backup erstellt!"));
        });

        smBtns.addView(bDetectSm, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        blp.leftMargin = UiTheme.dp(this, 6);
        smBtns.addView(bTestSm, blp);
        smBtns.addView(bBackupSm, blp);
        smCard.addView(smBtns);
        page.addView(smCard);

        // 2. Discord Webhook & Telegram Card
        LinearLayout notifyCard = UiTheme.makeCard(this, 14);
        notifyCard.setLayoutParams(smlp);
        notifyCard.addView(UiTheme.makeTitle(this, "Discord & Telegram Benachrichtigungen", 16f));
        notifyCard.addView(UiTheme.makeDim(this, "Discord Webhook-URL für Druckfertig- & Fehlermeldungen:", 12.5f));

        EditText whInput = UiTheme.makeInput(this, "https://discord.com/api/webhooks/...", config.getDiscordWebhook());
        notifyCard.addView(whInput, inLp);

        Button bTestWebhook = UiTheme.makeButton(this, "Discord Webhook testen", "primary");
        bTestWebhook.setLayoutParams(inLp);
        bTestWebhook.setOnClickListener(v -> {
            String url = whInput.getText().toString().trim();
            config.setDiscordWebhook(url);
            toast("Sende Testnachricht an Discord …");
            runAsync(() -> ApiClient.sendDiscordWebhook(url, "**PrintBoard Android Webhook-Test:** Die Verbindung zu Discord funktioniert einwandfrei!"),
                ok -> toast("Testnachricht erfolgreich an Discord gesendet!"));
        });
        notifyCard.addView(bTestWebhook);

        notifyCard.addView(UiTheme.makeDim(this, "Telegram Bot-Token & Chat-ID (optional):", 12.5f));
        EditText tgTokenInput = UiTheme.makeInput(this, "Bot-Token", config.getTelegramToken());
        EditText tgChatInput = UiTheme.makeInput(this, "Chat-ID", config.getTelegramChatId());
        notifyCard.addView(tgTokenInput, inLp);
        notifyCard.addView(tgChatInput, inLp);
        page.addView(notifyCard);

        // 3. Printer Controls Switch & Save Button
        LinearLayout ctrlCard = UiTheme.makeCard(this, 14);
        ctrlCard.setLayoutParams(smlp);
        Switch swCtrl = new Switch(this);
        swCtrl.setText("Drucker-Steuerung aktivieren (Pause, Cancel, Homing, Temperaturen)");
        swCtrl.setTextColor(UiTheme.TEXT_PRIMARY);
        swCtrl.setChecked(config.isControlsEnabled());
        ctrlCard.addView(swCtrl);

        Button bSaveAll = UiTheme.makeButton(this, "Alle Einstellungen speichern", "primary");
        LinearLayout.LayoutParams savelp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        savelp.topMargin = UiTheme.dp(this, 14);
        bSaveAll.setOnClickListener(v -> {
            config.setSpoolmanUrl(smUrlInput.getText().toString());
            config.setDiscordWebhook(whInput.getText().toString());
            config.setTelegramToken(tgTokenInput.getText().toString());
            config.setTelegramChatId(tgChatInput.getText().toString());
            config.setControlsEnabled(swCtrl.isChecked());
            refreshSpoolmanData();
            toast("Einstellungen gespeichert!");
        });
        ctrlCard.addView(bSaveAll, savelp);
        page.addView(ctrlCard);

        sc.addView(page);
        contentContainer.addView(sc);
    }
}
