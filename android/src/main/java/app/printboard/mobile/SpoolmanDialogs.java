package app.printboard.mobile;

import android.app.AlertDialog;
import android.content.Context;
import android.graphics.Color;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class SpoolmanDialogs {

    private static AlertDialog buildDarkDialog(Context ctx, String titleText, android.view.View contentView) {
        LinearLayout wrap = new LinearLayout(ctx);
        wrap.setOrientation(LinearLayout.VERTICAL);
        int pad = UiTheme.dp(ctx, 18);
        wrap.setPadding(pad, pad, pad, pad);
        wrap.setBackground(UiTheme.roundRect(UiTheme.BG_CARD, UiTheme.BORDER_CARD, UiTheme.dp(ctx, 1), UiTheme.dp(ctx, 18)));

        TextView title = UiTheme.makeTitle(ctx, titleText, 18f);
        title.setPadding(0, 0, 0, UiTheme.dp(ctx, 12));
        wrap.addView(title);

        ScrollView sc = new ScrollView(ctx);
        sc.addView(contentView);
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f);
        wrap.addView(sc, slp);

        AlertDialog dlg = new AlertDialog.Builder(ctx).create();
        dlg.setView(wrap);
        if (dlg.getWindow() != null) {
            dlg.getWindow().setBackgroundDrawableResource(android.R.color.transparent);
        }
        return dlg;
    }

    private static void addField(Context ctx, LinearLayout parent, String label, android.view.View field) {
        TextView tv = UiTheme.makeDim(ctx, label, 12.5f);
        tv.setPadding(0, UiTheme.dp(ctx, 8), 0, UiTheme.dp(ctx, 4));
        parent.addView(tv);
        parent.addView(field);
    }

    // ---------- 1. Spool Inspector & Action Sheet ----------
    public static void showSpoolSheet(MainActivity act, Models.Spool s) {
        LinearLayout col = new LinearLayout(act);
        col.setOrientation(LinearLayout.VERTICAL);

        // Header with large spool icon + progress
        LinearLayout top = new LinearLayout(act);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);
        UiTheme.SpoolIconView icon = new UiTheme.SpoolIconView(act, 62);
        icon.setSpoolData(s.getColors(), s.getFillFraction());
        top.addView(icon);

        LinearLayout info = new LinearLayout(act);
        info.setOrientation(LinearLayout.VERTICAL);
        info.setPadding(UiTheme.dp(act, 14), 0, 0, 0);
        info.addView(UiTheme.makeTitle(act, s.getDisplayName(), 16f));
        String vendorName = (s.filament != null && s.filament.vendor != null && !s.filament.vendor.name.isEmpty())
                ? s.filament.vendor.name : "Kein Hersteller";
        String mat = s.filament != null ? s.filament.material : "PLA";
        info.addView(UiTheme.makeDim(act, vendorName + " · " + mat + " · " + (s.filament != null ? s.filament.diameter : 1.75) + " mm", 13f));
        top.addView(info, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        col.addView(top);

        UiTheme.LevelBarView bar = new UiTheme.LevelBarView(act, 10);
        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, UiTheme.dp(act, 10));
        blp.topMargin = UiTheme.dp(act, 12);
        blp.bottomMargin = UiTheme.dp(act, 10);
        int barCol = s.remainingWeight < 150 ? UiTheme.YELLOW : UiTheme.ACCENT;
        bar.setProgress(s.getFillFraction(), barCol);
        col.addView(bar, blp);

        // Metadata details card
        LinearLayout metaCard = UiTheme.makeAltCard(act, 12);
        double initW = s.getEffectiveInitialWeight();
        double pct = s.getFillFraction() * 100.0;
        StringBuilder sb = new StringBuilder();
        sb.append(String.format(Locale.US, "Restgewicht: %.1f g / %.0f g (%.0f%%)\n", s.remainingWeight, initW, pct));
        sb.append(String.format(Locale.US, "Verbraucht: %.1f g  ·  Restlänge: %.1f m\n", s.usedWeight, s.remainingLength / 1000.0));
        sb.append(String.format(Locale.US, "Leerspule (Tara): %.0f g", s.getEffectiveTareWeight()));
        if (s.filament != null && (s.filament.extruderTemp != null || s.filament.bedTemp != null)) {
            sb.append("\nTemperaturen: Düse ")
              .append(s.filament.extruderTemp != null ? s.filament.extruderTemp + "°C" : "—")
              .append(" / Bett ")
              .append(s.filament.bedTemp != null ? s.filament.bedTemp + "°C" : "—");
        }
        Double pr = s.getEffectivePrice();
        if (pr != null) {
            sb.append(String.format(Locale.US, "\nPreis: %.2f €", pr));
        }
        if (s.location != null && !s.location.isEmpty()) {
            sb.append("\nLagerort: ").append(s.location);
        }
        if (s.cardUids != null && !s.cardUids.isEmpty()) {
            sb.append("\nNFC-UID: ").append(s.cardUids);
        }
        if (s.comment != null && !s.comment.isEmpty()) {
            sb.append("\nNotiz: ").append(s.comment);
        }
        TextView metaTv = UiTheme.makeDim(act, sb.toString(), 13f);
        metaTv.setLineSpacing(0, 1.25f);
        metaCard.addView(metaTv);
        col.addView(metaCard);

        AlertDialog dlg = buildDarkDialog(act, "Spulen-Details & Aktionen", col);

        // Action buttons
        String[][] actions = new String[][]{
            {"Drucker / Slot (T0–T3) zuweisen …", "primary", "assign"},
            {"Auf Waage abwiegen …", "", "weigh"},
            {"Verbrauch buchen (g / mm) …", "", "use"},
            {"Spule bearbeiten …", "", "edit"},
            {"Spule duplizieren", "", "dup"},
            {s.archived ? "Wiederherstellen" : "Archivieren", "", "arch"},
            {"Spule löschen", "danger", "del"},
            {"Schließen", "ghost", "close"}
        };

        for (String[] a : actions) {
            Button b = UiTheme.makeButton(act, a[0], a[1]);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            lp.topMargin = UiTheme.dp(act, 7);
            col.addView(b, lp);
            final String code = a[2];
            b.setOnClickListener(v -> {
                dlg.dismiss();
                switch (code) {
                    case "assign":
                        showAssignSpoolDialog(act, s);
                        break;
                    case "weigh":
                        showMeasureSpoolDialog(act, s);
                        break;
                    case "use":
                        showUseSpoolDialog(act, s);
                        break;
                    case "edit":
                        showSpoolEditDialog(act, s);
                        break;
                    case "dup":
                        duplicateSpool(act, s);
                        break;
                    case "arch":
                        toggleArchiveSpool(act, s);
                        break;
                    case "del":
                        confirmDeleteSpool(act, s);
                        break;
                }
            });
        }

        dlg.show();
    }

    // ---------- 2. Weigh Spool on Scale Dialog ----------
    public static void showMeasureSpoolDialog(MainActivity act, Models.Spool s) {
        LinearLayout col = new LinearLayout(act);
        col.setOrientation(LinearLayout.VERTICAL);

        double tare = s.getEffectiveTareWeight();
        col.addView(UiTheme.makeDim(act,
            String.format(Locale.US, "%s\nLeerspulen-Tara: %.0f g · Aktuell: %.1f g", s.getDisplayName(), tare, s.remainingWeight), 13f));

        EditText grossInput = UiTheme.makeInput(act, "Bruttogewicht in g", String.format(Locale.US, "%.0f", tare + s.remainingWeight));
        grossInput.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        addField(act, col, "Aktuelles Bruttogewicht auf der Waage (g):", grossInput);

        TextView calcPreview = UiTheme.makeTitle(act, String.format(Locale.US, "Netto-Filament: %.1f g", s.remainingWeight), 15f);
        calcPreview.setTextColor(UiTheme.ACCENT);
        calcPreview.setPadding(0, UiTheme.dp(act, 10), 0, UiTheme.dp(act, 10));
        col.addView(calcPreview);

        grossInput.addTextChangedListener(new UiTheme.SimpleTextWatcher(txt -> {
            try {
                double g = Double.parseDouble(txt.trim());
                double net = Math.max(0.0, g - tare);
                calcPreview.setText(String.format(Locale.US, "Berechnetes Netto-Filament: %.1f g", net));
            } catch (Exception ex) {
                calcPreview.setText("Berechnetes Netto-Filament: —");
            }
        }));

        AlertDialog dlg = buildDarkDialog(act, "Spule abwiegen", col);

        LinearLayout brow = new LinearLayout(act);
        brow.setOrientation(LinearLayout.HORIZONTAL);
        Button bCancel = UiTheme.makeButton(act, "Abbrechen", "ghost");
        Button bSave = UiTheme.makeButton(act, "Messwert speichern", "primary");
        bCancel.setOnClickListener(v -> dlg.dismiss());
        bSave.setOnClickListener(v -> {
            try {
                double g = Double.parseDouble(grossInput.getText().toString().trim());
                dlg.dismiss();
                act.runAsync(() -> SpoolmanClient.measureSpool(act.config.getSpoolmanUrl(), s.id, g),
                    res -> {
                        act.toast("Gewicht aktualisiert!");
                        act.refreshSpoolmanData();
                    });
            } catch (Exception ex) {
                act.toast("Bitte gültige Gramm-Zahl eingeben.");
            }
        });
        brow.addView(bCancel, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        slp.leftMargin = UiTheme.dp(act, 8);
        brow.addView(bSave, slp);
        col.addView(brow);
        dlg.show();
    }

    // ---------- 3. Book Filament Usage Dialog ----------
    public static void showUseSpoolDialog(MainActivity act, Models.Spool s) {
        LinearLayout col = new LinearLayout(act);
        col.setOrientation(LinearLayout.VERTICAL);
        col.addView(UiTheme.makeDim(act, "Positiver Wert bucht Verbrauch ab; negativer Wert bucht Filament hinzu.", 13f));

        EditText weightInput = UiTheme.makeInput(act, "z.B. 25.0 (oder -25.0 für Korrektur)", "15");
        weightInput.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL | InputType.TYPE_NUMBER_FLAG_SIGNED);
        addField(act, col, "Verbrauch in Gramm (g):", weightInput);

        AlertDialog dlg = buildDarkDialog(act, "Verbrauch buchen (#" + s.id + ")", col);
        LinearLayout brow = new LinearLayout(act);
        brow.setOrientation(LinearLayout.HORIZONTAL);
        brow.setPadding(0, UiTheme.dp(act, 14), 0, 0);
        Button bCancel = UiTheme.makeButton(act, "Abbrechen", "ghost");
        Button bOk = UiTheme.makeButton(act, "Buchen", "primary");
        bCancel.setOnClickListener(v -> dlg.dismiss());
        bOk.setOnClickListener(v -> {
            try {
                double w = Double.parseDouble(weightInput.getText().toString().trim());
                dlg.dismiss();
                act.runAsync(() -> SpoolmanClient.useSpool(act.config.getSpoolmanUrl(), s.id, w, null),
                    res -> {
                        act.toast("Verbrauch gebucht!");
                        act.refreshSpoolmanData();
                    });
            } catch (Exception ex) {
                act.toast("Ungültige Eingabe.");
            }
        });
        brow.addView(bCancel, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        slp.leftMargin = UiTheme.dp(act, 8);
        brow.addView(bOk, slp);
        col.addView(brow);
        dlg.show();
    }

    // ---------- 4. Assign Spool to Printer / Slot Dialog ----------
    public static void showAssignSpoolDialog(MainActivity act, Models.Spool s) {
        LinearLayout col = new LinearLayout(act);
        col.setOrientation(LinearLayout.VERTICAL);
        col.addView(UiTheme.makeDim(act, "Wähle den Drucker oder Extruder-Slot für " + s.getDisplayName() + ":", 13f));

        AlertDialog dlg = buildDarkDialog(act, "Spule zuweisen", col);

        for (Models.Printer p : act.printers) {
            Models.PrinterSpoolState ps = act.printerSpoolStates.get(p.id);
            if (ps != null && !ps.slots.isEmpty()) {
                for (Models.PrinterSlot sl : ps.slots) {
                    String actStar = sl.active ? " AKTIV" : "";
                    String nfcStr = (sl.cardUid != null && !sl.cardUid.isEmpty()) ? " · NFC " + sl.cardUid : "";
                    Button b = UiTheme.makeButton(act, p.name + " · Slot " + sl.label + actStar + nfcStr, sl.active ? "primary" : "");
                    LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                    lp.topMargin = UiTheme.dp(act, 8);
                    col.addView(b, lp);
                    b.setOnClickListener(v -> {
                        dlg.dismiss();
                        act.runAsync(() -> {
                            if (sl.cardUid != null && !sl.cardUid.isEmpty()) {
                                SpoolmanClient.linkNfcUidToSpool(act.config.getSpoolmanUrl(), s, sl.cardUid);
                            }
                            SpoolmanClient.assignSpoolToPrinter(p, s.id, sl.channel);
                            if (sl.active) act.config.setLocalPrinterSpool(p.id, s.id);
                            return true;
                        }, res -> {
                            act.toast("Spule #" + s.id + " an " + p.name + " (" + sl.label + ") zugewiesen!");
                            act.refreshSpoolmanData();
                            act.pollAllPrinters();
                        });
                    });
                }
            }
            Button bMain = UiTheme.makeButton(act, p.name + " · Aktive Hauptspule", "");
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            lp.topMargin = UiTheme.dp(act, 8);
            col.addView(bMain, lp);
            bMain.setOnClickListener(v -> {
                dlg.dismiss();
                act.runAsync(() -> {
                    try {
                        SpoolmanClient.assignSpoolToPrinter(p, s.id, null);
                    } catch (Exception ignored) {
                    }
                    act.config.setLocalPrinterSpool(p.id, s.id);
                    return true;
                }, res -> {
                    act.toast("Spule #" + s.id + " für " + p.name + " gesetzt!");
                    act.refreshSpoolmanData();
                    act.pollAllPrinters();
                });
            });
        }

        Button bClose = UiTheme.makeButton(act, "Abbrechen", "ghost");
        LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        clp.topMargin = UiTheme.dp(act, 12);
        col.addView(bClose, clp);
        bClose.setOnClickListener(v -> dlg.dismiss());
        dlg.show();
    }

    // ---------- 5. Create / Edit Spool Dialog ----------
    public static void showSpoolEditDialog(MainActivity act, Models.Spool existing) {
        if (act.filaments.isEmpty()) {
            act.toast("Bitte zuerst ein Filament anlegen oder aus SpoolmanDB importieren.");
            return;
        }
        LinearLayout col = new LinearLayout(act);
        col.setOrientation(LinearLayout.VERTICAL);

        Spinner filSpinner = new Spinner(act);
        filSpinner.setBackground(UiTheme.roundRect(UiTheme.BG_INPUT, UiTheme.BORDER_INPUT, UiTheme.dp(act, 1), UiTheme.dp(act, 10)));
        List<String> filLabels = new ArrayList<>();
        int selIdx = 0;
        for (int i = 0; i < act.filaments.size(); i++) {
            Models.Filament f = act.filaments.get(i);
            filLabels.add("#" + f.id + " " + f.getDisplayName() + " (" + f.material + ")");
            if (existing != null && existing.filament != null && existing.filament.id == f.id) {
                selIdx = i;
            }
        }
        ArrayAdapter<String> adapter = new ArrayAdapter<>(act, android.R.layout.simple_spinner_dropdown_item, filLabels);
        filSpinner.setAdapter(adapter);
        filSpinner.setSelection(selIdx);
        addField(act, col, "Filament *:", filSpinner);

        double defInit = existing != null ? existing.getEffectiveInitialWeight() : 1000.0;
        double defRem = existing != null ? existing.remainingWeight : 1000.0;
        EditText initInput = UiTheme.makeInput(act, "1000", String.format(Locale.US, "%.0f", defInit));
        initInput.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        addField(act, col, "Netto-Anfangsgewicht (g):", initInput);

        EditText remInput = UiTheme.makeInput(act, "1000", String.format(Locale.US, "%.1f", defRem));
        remInput.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        addField(act, col, "Aktuelles Restgewicht (g):", remInput);

        EditText tareInput = UiTheme.makeInput(act, "optional (z.B. 200)", existing != null && existing.spoolWeight != null ? String.format(Locale.US, "%.0f", existing.spoolWeight) : "");
        tareInput.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        addField(act, col, "Leerspulen-Gewicht Tara (g):", tareInput);

        EditText priceInput = UiTheme.makeInput(act, "optional (z.B. 18.99)", existing != null && existing.price != null ? String.format(Locale.US, "%.2f", existing.price) : "");
        priceInput.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        addField(act, col, "Preis (€):", priceInput);

        EditText locInput = UiTheme.makeInput(act, "optional (z.B. Drybox 1, Regal A)", existing != null ? existing.location : "");
        addField(act, col, "Lagerort:", locInput);

        EditText nfcInput = UiTheme.makeInput(act, "optional (NFC Card-UID)", existing != null ? existing.cardUids : "");
        addField(act, col, "NFC Card-UID:", nfcInput);

        EditText commentInput = UiTheme.makeInput(act, "optional", existing != null ? existing.comment : "");
        addField(act, col, "Kommentar:", commentInput);

        AlertDialog dlg = buildDarkDialog(act, existing != null ? "Spule #" + existing.id + " bearbeiten" : "+ Neue Spule anlegen", col);

        LinearLayout brow = new LinearLayout(act);
        brow.setOrientation(LinearLayout.HORIZONTAL);
        brow.setPadding(0, UiTheme.dp(act, 14), 0, 0);
        Button bCancel = UiTheme.makeButton(act, "Abbrechen", "ghost");
        Button bSave = UiTheme.makeButton(act, "Speichern", "primary");
        bCancel.setOnClickListener(v -> dlg.dismiss());
        bSave.setOnClickListener(v -> {
            try {
                int fIdx = filSpinner.getSelectedItemPosition();
                Models.Filament chosenFil = act.filaments.get(fIdx);
                JSONObject payload = new JSONObject();
                payload.put("filament_id", chosenFil.id);
                payload.put("initial_weight", Double.parseDouble(initInput.getText().toString().trim()));
                payload.put("remaining_weight", Double.parseDouble(remInput.getText().toString().trim()));
                String tStr = tareInput.getText().toString().trim();
                payload.put("spool_weight", tStr.isEmpty() ? JSONObject.NULL : Double.parseDouble(tStr));
                String pStr = priceInput.getText().toString().trim();
                payload.put("price", pStr.isEmpty() ? JSONObject.NULL : Double.parseDouble(pStr));
                String locStr = locInput.getText().toString().trim();
                payload.put("location", locStr.isEmpty() ? JSONObject.NULL : locStr);
                String comStr = commentInput.getText().toString().trim();
                payload.put("comment", comStr.isEmpty() ? JSONObject.NULL : comStr);

                String uidStr = nfcInput.getText().toString().trim();
                if (!uidStr.isEmpty() || existing != null) {
                    JSONObject extra = new JSONObject();
                    extra.put("card_uids", SpoolmanClient.encodeExtraString(uidStr));
                    payload.put("extra", extra);
                }

                dlg.dismiss();
                act.runAsync(() -> {
                    if (existing != null) {
                        return SpoolmanClient.updateSpool(act.config.getSpoolmanUrl(), existing.id, payload);
                    } else {
                        return SpoolmanClient.createSpool(act.config.getSpoolmanUrl(), payload);
                    }
                }, res -> {
                    act.toast("Spule gespeichert!");
                    act.refreshSpoolmanData();
                });
            } catch (Exception ex) {
                act.toast("Fehler: " + ex.getMessage());
            }
        });
        brow.addView(bCancel, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        slp.leftMargin = UiTheme.dp(act, 8);
        brow.addView(bSave, slp);
        col.addView(brow);
        dlg.show();
    }

    // ---------- 6. Create / Edit Filament Dialog ----------
    public static void showFilamentEditDialog(MainActivity act, Models.Filament existing) {
        LinearLayout col = new LinearLayout(act);
        col.setOrientation(LinearLayout.VERTICAL);

        EditText nameInput = UiTheme.makeInput(act, "z.B. PLA Basic, PETG Rapid", existing != null ? existing.name : "");
        addField(act, col, "Filament-Name *:", nameInput);

        Spinner venSpinner = new Spinner(act);
        venSpinner.setBackground(UiTheme.roundRect(UiTheme.BG_INPUT, UiTheme.BORDER_INPUT, UiTheme.dp(act, 1), UiTheme.dp(act, 10)));
        List<String> venLabels = new ArrayList<>();
        venLabels.add("— Kein Hersteller —");
        int vSel = 0;
        for (int i = 0; i < act.vendors.size(); i++) {
            Models.Vendor v = act.vendors.get(i);
            venLabels.add(v.name);
            if (existing != null && existing.vendor != null && existing.vendor.id == v.id) {
                vSel = i + 1;
            }
        }
        venSpinner.setAdapter(new ArrayAdapter<>(act, android.R.layout.simple_spinner_dropdown_item, venLabels));
        venSpinner.setSelection(vSel);
        addField(act, col, "Hersteller:", venSpinner);

        EditText matInput = UiTheme.makeInput(act, "PLA, PETG, ASA, ABS, TPU …", existing != null ? existing.material : "PLA");
        addField(act, col, "Material *:", matInput);

        EditText colorInput = UiTheme.makeInput(act, "Hex RRGGBB (z.B. FF0000)", existing != null ? existing.colorHex : "38BDF8");
        addField(act, col, "Farbe (Hex RRGGBB):", colorInput);

        // Quick Color Palette Swatches
        LinearLayout palette = new LinearLayout(act);
        palette.setOrientation(LinearLayout.HORIZONTAL);
        palette.setPadding(0, UiTheme.dp(act, 6), 0, UiTheme.dp(act, 4));
        String[] presetColors = new String[]{"000000", "FFFFFF", "FF0000", "38BDF8", "34D399", "FACC15", "FB923C", "A855F7"};
        for (String hex : presetColors) {
            android.view.View swatch = new android.view.View(act);
            int sz = UiTheme.dp(act, 28);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(sz, sz);
            lp.rightMargin = UiTheme.dp(act, 6);
            swatch.setLayoutParams(lp);
            swatch.setBackground(UiTheme.roundRect(Color.parseColor("#" + hex), UiTheme.BORDER_INPUT, UiTheme.dp(act, 1), sz / 2f));
            swatch.setOnClickListener(v -> colorInput.setText(hex));
            palette.addView(swatch);
        }
        col.addView(palette);

        EditText weightInput = UiTheme.makeInput(act, "1000", String.format(Locale.US, "%.0f", existing != null ? existing.weight : 1000.0));
        weightInput.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        addField(act, col, "Netto-Gewicht (g):", weightInput);

        EditText densityInput = UiTheme.makeInput(act, "1.24", String.format(Locale.US, "%.2f", existing != null ? existing.density : 1.24));
        densityInput.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        addField(act, col, "Dichte (g/cm³):", densityInput);

        EditText nozzleInput = UiTheme.makeInput(act, "210", existing != null && existing.extruderTemp != null ? String.valueOf(existing.extruderTemp) : "210");
        nozzleInput.setInputType(InputType.TYPE_CLASS_NUMBER);
        addField(act, col, "Düsentemperatur (°C):", nozzleInput);

        EditText bedInput = UiTheme.makeInput(act, "60", existing != null && existing.bedTemp != null ? String.valueOf(existing.bedTemp) : "60");
        bedInput.setInputType(InputType.TYPE_CLASS_NUMBER);
        addField(act, col, "Betttemperatur (°C):", bedInput);

        EditText priceInput = UiTheme.makeInput(act, "optional (z.B. 19.99)", existing != null && existing.price != null ? String.format(Locale.US, "%.2f", existing.price) : "");
        priceInput.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        addField(act, col, "Standardpreis (€):", priceInput);

        AlertDialog dlg = buildDarkDialog(act, existing != null ? "Filament bearbeiten" : "+ Neues Filament", col);

        LinearLayout brow = new LinearLayout(act);
        brow.setOrientation(LinearLayout.HORIZONTAL);
        brow.setPadding(0, UiTheme.dp(act, 14), 0, 0);
        Button bCancel = UiTheme.makeButton(act, "Abbrechen", "ghost");
        Button bSave = UiTheme.makeButton(act, "Speichern", "primary");
        bCancel.setOnClickListener(v -> dlg.dismiss());
        bSave.setOnClickListener(v -> {
            String name = nameInput.getText().toString().trim();
            if (name.isEmpty()) {
                act.toast("Bitte Namen eingeben.");
                return;
            }
            try {
                JSONObject p = new JSONObject();
                p.put("name", name);
                int vIdx = venSpinner.getSelectedItemPosition();
                p.put("vendor_id", vIdx > 0 ? act.vendors.get(vIdx - 1).id : JSONObject.NULL);
                p.put("material", matInput.getText().toString().trim().isEmpty() ? "PLA" : matInput.getText().toString().trim());
                p.put("color_hex", colorInput.getText().toString().trim().replace("#", ""));
                p.put("diameter", 1.75);
                p.put("density", Double.parseDouble(densityInput.getText().toString().trim()));
                p.put("weight", Double.parseDouble(weightInput.getText().toString().trim()));
                String nt = nozzleInput.getText().toString().trim();
                if (!nt.isEmpty()) p.put("settings_extruder_temp", Integer.parseInt(nt));
                String bt = bedInput.getText().toString().trim();
                if (!bt.isEmpty()) p.put("settings_bed_temp", Integer.parseInt(bt));
                String pr = priceInput.getText().toString().trim();
                p.put("price", pr.isEmpty() ? JSONObject.NULL : Double.parseDouble(pr));

                dlg.dismiss();
                act.runAsync(() -> {
                    if (existing != null) {
                        return SpoolmanClient.updateFilament(act.config.getSpoolmanUrl(), existing.id, p);
                    } else {
                        return SpoolmanClient.createFilament(act.config.getSpoolmanUrl(), p);
                    }
                }, res -> {
                    act.toast("Filament gespeichert!");
                    act.refreshSpoolmanData();
                });
            } catch (Exception ex) {
                act.toast("Fehler: " + ex.getMessage());
            }
        });
        brow.addView(bCancel, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        slp.leftMargin = UiTheme.dp(act, 8);
        brow.addView(bSave, slp);
        col.addView(brow);
        dlg.show();
    }

    // ---------- 7. Import from SpoolmanDB Catalog Dialog ----------
    public static void showExternalCatalogDialog(MainActivity act) {
        LinearLayout col = new LinearLayout(act);
        col.setOrientation(LinearLayout.VERTICAL);

        col.addView(UiTheme.makeDim(act, "Durchsuche über 9.400 Filamente aus der SpoolmanDB und importiere sie mit 1 Klick:", 12.5f));

        LinearLayout srow = new LinearLayout(act);
        srow.setOrientation(LinearLayout.HORIZONTAL);
        srow.setPadding(0, UiTheme.dp(act, 8), 0, UiTheme.dp(act, 8));
        EditText qInput = UiTheme.makeInput(act, "z.B. Bambu PLA, Polymaker ASA, eSUN PETG …", "PLA");
        Button bSearch = UiTheme.makeButton(act, "Suchen", "primary");
        srow.addView(qInput, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        blp.leftMargin = UiTheme.dp(act, 8);
        srow.addView(bSearch, blp);
        col.addView(srow);

        CheckBox cbCreateSpool = new CheckBox(act);
        cbCreateSpool.setText("Direkt auch eine neue Spule (1000 g) anlegen");
        cbCreateSpool.setTextColor(UiTheme.TEXT_PRIMARY);
        cbCreateSpool.setChecked(true);
        col.addView(cbCreateSpool);

        LinearLayout resultsBox = new LinearLayout(act);
        resultsBox.setOrientation(LinearLayout.VERTICAL);
        col.addView(resultsBox);

        AlertDialog dlg = buildDarkDialog(act, "SpoolmanDB-Katalog", col);

        Runnable doSearch = () -> {
            String q = qInput.getText().toString().trim();
            resultsBox.removeAllViews();
            resultsBox.addView(UiTheme.makeDim(act, "Suche in SpoolmanDB …", 13f));
            act.runAsync(() -> SpoolmanClient.searchExternalFilaments(act.config.getSpoolmanUrl(), q, 35), res -> {
                resultsBox.removeAllViews();
                if (res == null || res.isEmpty()) {
                    resultsBox.addView(UiTheme.makeDim(act, "Keine Treffer gefunden.", 13f));
                    return;
                }
                for (Models.ExternalFilament ef : res) {
                    LinearLayout item = UiTheme.makeAltCard(act, 10);
                    LinearLayout.LayoutParams ilp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                    ilp.topMargin = UiTheme.dp(act, 6);
                    item.setLayoutParams(ilp);

                    LinearLayout r = new LinearLayout(act);
                    r.setOrientation(LinearLayout.HORIZONTAL);
                    r.setGravity(Gravity.CENTER_VERTICAL);

                    UiTheme.SpoolIconView icon = new UiTheme.SpoolIconView(act, 34);
                    icon.setSpoolData(new String[]{"#" + ef.colorHex.replace("#", "")}, 1.0);
                    r.addView(icon);

                    LinearLayout txt = new LinearLayout(act);
                    txt.setOrientation(LinearLayout.VERTICAL);
                    txt.setPadding(UiTheme.dp(act, 10), 0, UiTheme.dp(act, 8), 0);
                    txt.addView(UiTheme.makeTitle(act, ef.manufacturer + " · " + ef.name, 14f));
                    txt.addView(UiTheme.makeDim(act, ef.material + " · " + ef.weight + "g · " + ef.density + " g/cm³", 12f));
                    r.addView(txt, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

                    Button bImp = UiTheme.makeButton(act, "Import", "primary");
                    bImp.setOnClickListener(v -> {
                        boolean withSpool = cbCreateSpool.isChecked();
                        dlg.dismiss();
                        act.runAsync(() -> {
                            Models.Filament createdFil = SpoolmanClient.importExternalFilament(
                                act.config.getSpoolmanUrl(), ef, act.vendors
                            );
                            if (withSpool && createdFil != null && createdFil.id > 0) {
                                JSONObject sp = new JSONObject();
                                sp.put("filament_id", createdFil.id);
                                sp.put("initial_weight", ef.weight > 0 ? ef.weight : 1000.0);
                                sp.put("remaining_weight", ef.weight > 0 ? ef.weight : 1000.0);
                                if (ef.spoolWeight != null && ef.spoolWeight > 0) {
                                    sp.put("spool_weight", ef.spoolWeight);
                                }
                                SpoolmanClient.createSpool(act.config.getSpoolmanUrl(), sp);
                            }
                            return createdFil;
                        }, imported -> {
                            act.toast("Importiert: " + ef.manufacturer + " " + ef.name);
                            act.refreshSpoolmanData();
                        });
                    });
                    r.addView(bImp);
                    item.addView(r);
                    resultsBox.addView(item);
                }
            });
        };

        bSearch.setOnClickListener(v -> doSearch.run());

        Button bClose = UiTheme.makeButton(act, "Schließen", "ghost");
        LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        clp.topMargin = UiTheme.dp(act, 12);
        col.addView(bClose, clp);
        bClose.setOnClickListener(v -> dlg.dismiss());

        dlg.show();
        doSearch.run();
    }

    // ---------- 8. Create / Edit Vendor Dialog ----------
    public static void showVendorEditDialog(MainActivity act, Models.Vendor existing) {
        LinearLayout col = new LinearLayout(act);
        col.setOrientation(LinearLayout.VERTICAL);

        EditText nameInput = UiTheme.makeInput(act, "z.B. Polymaker, Bambu Lab, eSUN …", existing != null ? existing.name : "");
        addField(act, col, "Herstellername *:", nameInput);

        EditText tareInput = UiTheme.makeInput(act, "optional (z.B. 200)", existing != null && existing.emptySpoolWeight != null ? String.format(Locale.US, "%.0f", existing.emptySpoolWeight) : "");
        tareInput.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        addField(act, col, "Leerspulen-Gewicht Tara (g):", tareInput);

        EditText commentInput = UiTheme.makeInput(act, "optional", existing != null ? existing.comment : "");
        addField(act, col, "Kommentar:", commentInput);

        AlertDialog dlg = buildDarkDialog(act, existing != null ? "Hersteller bearbeiten" : "+ Neuer Hersteller", col);

        LinearLayout brow = new LinearLayout(act);
        brow.setOrientation(LinearLayout.HORIZONTAL);
        brow.setPadding(0, UiTheme.dp(act, 14), 0, 0);
        Button bCancel = UiTheme.makeButton(act, "Abbrechen", "ghost");
        Button bSave = UiTheme.makeButton(act, "Speichern", "primary");
        bCancel.setOnClickListener(v -> dlg.dismiss());
        bSave.setOnClickListener(v -> {
            String name = nameInput.getText().toString().trim();
            if (name.isEmpty()) {
                act.toast("Bitte Herstellernamen eingeben.");
                return;
            }
            try {
                JSONObject p = new JSONObject();
                p.put("name", name);
                String t = tareInput.getText().toString().trim();
                p.put("empty_spool_weight", t.isEmpty() ? JSONObject.NULL : Double.parseDouble(t));
                String c = commentInput.getText().toString().trim();
                p.put("comment", c.isEmpty() ? JSONObject.NULL : c);

                dlg.dismiss();
                act.runAsync(() -> {
                    if (existing != null) {
                        return SpoolmanClient.updateVendor(act.config.getSpoolmanUrl(), existing.id, p);
                    } else {
                        return SpoolmanClient.createVendor(act.config.getSpoolmanUrl(), p);
                    }
                }, res -> {
                    act.toast("Hersteller gespeichert!");
                    act.refreshSpoolmanData();
                });
            } catch (Exception ex) {
                act.toast("Fehler: " + ex.getMessage());
            }
        });
        brow.addView(bCancel, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        slp.leftMargin = UiTheme.dp(act, 8);
        brow.addView(bSave, slp);
        col.addView(brow);
        dlg.show();
    }

    // ---------- Helpers ----------
    private static void duplicateSpool(MainActivity act, Models.Spool s) {
        act.runAsync(() -> {
            JSONObject p = new JSONObject();
            p.put("filament_id", s.filament != null ? s.filament.id : 1);
            double init = s.getEffectiveInitialWeight();
            p.put("initial_weight", init);
            p.put("remaining_weight", init);
            if (s.spoolWeight != null) p.put("spool_weight", s.spoolWeight);
            if (s.price != null) p.put("price", s.price);
            if (s.location != null && !s.location.isEmpty()) p.put("location", s.location);
            return SpoolmanClient.createSpool(act.config.getSpoolmanUrl(), p);
        }, res -> {
            act.toast("Spule dupliziert!");
            act.refreshSpoolmanData();
        });
    }

    private static void toggleArchiveSpool(MainActivity act, Models.Spool s) {
        act.runAsync(() -> {
            JSONObject p = new JSONObject();
            p.put("archived", !s.archived);
            return SpoolmanClient.updateSpool(act.config.getSpoolmanUrl(), s.id, p);
        }, res -> {
            act.toast(s.archived ? "Spule wiederhergestellt!" : "Spule archiviert!");
            act.refreshSpoolmanData();
        });
    }

    private static void confirmDeleteSpool(MainActivity act, Models.Spool s) {
        new AlertDialog.Builder(act)
            .setTitle("Spule löschen")
            .setMessage("Soll „" + s.getDisplayName() + "“ wirklich dauerhaft aus Spoolman gelöscht werden?")
            .setPositiveButton("Löschen", (d, w) -> {
                act.runAsync(() -> {
                    SpoolmanClient.deleteSpool(act.config.getSpoolmanUrl(), s.id);
                    return true;
                }, res -> {
                    act.toast("Spule gelöscht.");
                    act.refreshSpoolmanData();
                });
            })
            .setNegativeButton("Abbrechen", null)
            .show();
    }
}
