package app.printboard.mobile;

import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.text.TextUtils;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class UiTheme {
    public static final int BG_MAIN = Color.parseColor("#080D14");
    public static final int BG_NAV = Color.parseColor("#0C1420");
    public static final int BG_CARD = Color.parseColor("#101A28");
    public static final int BG_CARD_ALT = Color.parseColor("#0C1522");
    public static final int BG_INPUT = Color.parseColor("#0D1623");
    public static final int BG_BTN = Color.parseColor("#162436");
    public static final int BORDER_CARD = Color.parseColor("#203247");
    public static final int BORDER_INPUT = Color.parseColor("#283E56");
    public static final int TEXT_PRIMARY = Color.parseColor("#EAF0FA");
    public static final int TEXT_DIM = Color.parseColor("#8198AF");
    public static final int ACCENT = Color.parseColor("#38BDF8");
    public static final int ACCENT_DARK = Color.parseColor("#0284C7");
    public static final int GREEN = Color.parseColor("#34D399");
    public static final int YELLOW = Color.parseColor("#FACC15");
    public static final int ORANGE = Color.parseColor("#FB923C");
    public static final int RED = Color.parseColor("#F87171");
    public static final int DANGER_BG = Color.parseColor("#7F1D1D");
    public static final int DANGER_BORDER = Color.parseColor("#DC2626");

    public static int dp(Context ctx, float dp) {
        return Math.round(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, dp, ctx.getResources().getDisplayMetrics()));
    }

    public static int safeParseColor(String hex, int fallback) {
        if (hex == null || hex.trim().isEmpty()) return fallback;
        String clean = hex.trim();
        if (!clean.startsWith("#")) clean = "#" + clean;
        if (clean.length() > 7) clean = clean.substring(0, 7);
        try {
            return Color.parseColor(clean);
        } catch (Exception e) {
            return fallback;
        }
    }

    public static GradientDrawable roundRect(int fillColor, int strokeColor, int strokeWidthPx, float radiusPx) {
        GradientDrawable gd = new GradientDrawable();
        gd.setColor(fillColor);
        gd.setCornerRadius(radiusPx);
        if (strokeWidthPx > 0) {
            gd.setStroke(strokeWidthPx, strokeColor);
        }
        return gd;
    }

    public static LinearLayout makeCard(Context ctx, int padDp) {
        LinearLayout l = new LinearLayout(ctx);
        l.setOrientation(LinearLayout.VERTICAL);
        int p = dp(ctx, padDp);
        l.setPadding(p, p, p, p);
        l.setBackground(roundRect(BG_CARD, BORDER_CARD, dp(ctx, 1), dp(ctx, 16)));
        return l;
    }

    public static LinearLayout makeAltCard(Context ctx, int padDp) {
        LinearLayout l = new LinearLayout(ctx);
        l.setOrientation(LinearLayout.VERTICAL);
        int p = dp(ctx, padDp);
        l.setPadding(p, p, p, p);
        l.setBackground(roundRect(BG_CARD_ALT, BORDER_CARD, dp(ctx, 1), dp(ctx, 12)));
        return l;
    }

    public static TextView makeTitle(Context ctx, String text, float sp) {
        TextView tv = new TextView(ctx);
        tv.setText(text);
        tv.setTextColor(TEXT_PRIMARY);
        tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        tv.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
        return tv;
    }

    public static TextView makeDim(Context ctx, String text, float sp) {
        TextView tv = new TextView(ctx);
        tv.setText(text);
        tv.setTextColor(TEXT_DIM);
        tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        return tv;
    }

    public static TextView makePill(Context ctx, String text, int fgColor, int bgColor) {
        TextView tv = new TextView(ctx);
        tv.setText(text);
        tv.setTextColor(fgColor);
        tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11.5f);
        tv.setTypeface(Typeface.create("sans-serif-medium", Typeface.BOLD));
        int px = dp(ctx, 9);
        int py = dp(ctx, 4);
        tv.setPadding(px, py, px, py);
        tv.setBackground(roundRect(bgColor, fgColor, dp(ctx, 1), dp(ctx, 20)));
        return tv;
    }

    public static Button makeButton(Context ctx, String text, String style) {
        Button b = new Button(ctx);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13f);
        b.setTypeface(Typeface.create("sans-serif-medium", Typeface.BOLD));
        int px = dp(ctx, 13);
        int py = dp(ctx, 8);
        b.setPadding(px, py, px, py);
        b.setMinimumHeight(dp(ctx, 40));
        b.setMinHeight(dp(ctx, 40));

        int fill = BG_BTN;
        int border = Color.parseColor("#29415C");
        int textColor = TEXT_PRIMARY;
        if ("primary".equals(style)) {
            fill = ACCENT;
            border = ACCENT;
            textColor = Color.parseColor("#04111D");
        } else if ("danger".equals(style)) {
            fill = DANGER_BG;
            border = DANGER_BORDER;
            textColor = Color.parseColor("#FECACA");
        } else if ("warn".equals(style)) {
            fill = Color.parseColor("#422006");
            border = Color.parseColor("#D97706");
            textColor = Color.parseColor("#FDE68A");
        } else if ("ghost".equals(style)) {
            fill = Color.parseColor("#0D1724");
            border = BORDER_CARD;
            textColor = ACCENT;
        }
        b.setTextColor(textColor);
        GradientDrawable base = roundRect(fill, border, dp(ctx, 1), dp(ctx, 10));
        RippleDrawable ripple = new RippleDrawable(ColorStateList.valueOf(Color.parseColor("#33FFFFFF")), base, null);
        b.setBackground(ripple);
        return b;
    }

    public static EditText makeInput(Context ctx, String hint, String initial) {
        EditText et = new EditText(ctx);
        et.setHint(hint);
        et.setHintTextColor(Color.parseColor("#5C738A"));
        et.setText(initial != null ? initial : "");
        et.setTextColor(TEXT_PRIMARY);
        et.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f);
        et.setSingleLine(true);
        int px = dp(ctx, 12);
        int py = dp(ctx, 10);
        et.setPadding(px, py, px, py);
        et.setBackground(roundRect(BG_INPUT, BORDER_INPUT, dp(ctx, 1), dp(ctx, 10)));
        return et;
    }

    public static String formatHms(double seconds) {
        if (seconds < 0) return "—";
        int s = (int) Math.round(seconds);
        int h = s / 3600;
        int m = (s % 3600) / 60;
        return String.format(Locale.US, "%dh %02dm", h, m);
    }

    // ---------- Custom Canvas View: 3D Spool Reel Icon ----------
    public static class SpoolIconView extends View {
        private String[] colors = new String[]{"#38BDF8"};
        private float fillFraction = 1.0f;
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF oval = new RectF();

        public SpoolIconView(Context ctx, int sizeDp) {
            super(ctx);
            int px = dp(ctx, sizeDp);
            setLayoutParams(new LinearLayout.LayoutParams(px, px));
        }

        public void setSpoolData(String[] hexColors, double fill) {
            this.colors = (hexColors != null && hexColors.length > 0) ? hexColors : new String[]{"#38BDF8"};
            this.fillFraction = (float) Math.max(0.0, Math.min(1.0, fill));
            invalidate();
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            float w = getWidth();
            float h = getHeight();
            float cx = w / 2f;
            float cy = h / 2f;
            float outerR = Math.min(w, h) * 0.45f;
            float innerR = Math.min(w, h) * 0.18f;
            float filR = innerR + (outerR - innerR - 2f) * (0.24f + 0.76f * fillFraction);

            // Outer spool rim
            paint.setShader(null);
            paint.setStyle(Paint.Style.FILL);
            paint.setColor(Color.parseColor("#0B131F"));
            oval.set(cx - outerR, cy - outerR, cx + outerR, cy + outerR);
            canvas.drawOval(oval, paint);

            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(Math.max(2f, w * 0.04f));
            paint.setColor(Color.parseColor("#334D6B"));
            canvas.drawOval(oval, paint);

            // Filament winding
            paint.setStyle(Paint.Style.FILL);
            if (colors.length == 1) {
                paint.setShader(null);
                paint.setColor(safeParseColor(colors[0], ACCENT));
            } else {
                int[] cArr = new int[colors.length];
                for (int i = 0; i < colors.length; i++) {
                    cArr[i] = safeParseColor(colors[i], ACCENT);
                }
                paint.setShader(new LinearGradient(
                    cx - filR, cy - filR, cx + filR, cy + filR,
                    cArr, null, Shader.TileMode.CLAMP
                ));
            }
            oval.set(cx - filR, cy - filR, cx + filR, cy + filR);
            canvas.drawOval(oval, paint);

            // Inner hub hole
            paint.setShader(null);
            paint.setStyle(Paint.Style.FILL);
            paint.setColor(BG_MAIN);
            oval.set(cx - innerR, cy - innerR, cx + innerR, cy + innerR);
            canvas.drawOval(oval, paint);

            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(Math.max(1.5f, w * 0.03f));
            paint.setColor(Color.parseColor("#2B425E"));
            canvas.drawOval(oval, paint);
        }
    }

    // ---------- Custom Canvas View: Rounded Gradient Progress / Level Bar ----------
    public static class LevelBarView extends View {
        private float progress = 0f;
        private int barColor = ACCENT;
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF rect = new RectF();

        public LevelBarView(Context ctx, int heightDp) {
            super(ctx);
            setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(ctx, heightDp)));
        }

        public void setProgress(double fraction, int color) {
            this.progress = (float) Math.max(0.0, Math.min(1.0, fraction));
            this.barColor = color;
            invalidate();
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            float w = getWidth();
            float h = getHeight();
            float r = h / 2f;

            paint.setShader(null);
            paint.setStyle(Paint.Style.FILL);
            paint.setColor(Color.parseColor("#18293B"));
            rect.set(0, 0, w, h);
            canvas.drawRoundRect(rect, r, r, paint);

            if (progress > 0.005f) {
                float pw = Math.max(h, w * progress);
                paint.setShader(new LinearGradient(0, 0, pw, 0, ACCENT_DARK, barColor, Shader.TileMode.CLAMP));
                rect.set(0, 0, pw, h);
                canvas.drawRoundRect(rect, r, r, paint);
            }
        }
    }

    // ---------- Custom Canvas View: Monthly Print Hours Bar Chart ----------
    public static class MonthlyChartView extends View {
        private final List<String> months = new ArrayList<>();
        private final List<Double> values = new ArrayList<>();
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF rect = new RectF();

        public MonthlyChartView(Context ctx) {
            super(ctx);
            setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(ctx, 175)));
            setBackground(roundRect(BG_CARD, BORDER_CARD, dp(ctx, 1), dp(ctx, 16)));
        }

        public void setData(Map<String, Double> data) {
            months.clear();
            values.clear();
            if (data != null) {
                List<String> keys = new ArrayList<>(data.keySet());
                java.util.Collections.sort(keys);
                int start = Math.max(0, keys.size() - 8);
                for (int i = start; i < keys.size(); i++) {
                    String k = keys.get(i);
                    months.add(k.length() == 7 ? k.substring(2) : k);
                    values.add(data.get(k));
                }
            }
            invalidate();
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            float w = getWidth();
            float h = getHeight();
            float pad = dp(getContext(), 16);

            paint.setColor(TEXT_PRIMARY);
            paint.setTextSize(dp(getContext(), 13));
            paint.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
            canvas.drawText("Druckstunden pro Monat", pad, pad + dp(getContext(), 6), paint);

            if (months.isEmpty()) {
                paint.setColor(TEXT_DIM);
                paint.setTextSize(dp(getContext(), 12));
                paint.setTypeface(Typeface.DEFAULT);
                String msg = "Noch keine Monatsdaten verfügbar";
                float tw = paint.measureText(msg);
                canvas.drawText(msg, (w - tw) / 2f, h / 2f + dp(getContext(), 6), paint);
                return;
            }

            double maxVal = 1.0;
            for (double v : values) {
                if (v > maxVal) maxVal = v;
            }

            float top = dp(getContext(), 44);
            float bottom = h - dp(getContext(), 28);
            float availH = Math.max(20f, bottom - top);
            float availW = w - pad * 2f;
            int n = months.size();
            float slotW = availW / n;
            float barW = Math.min(dp(getContext(), 34), Math.max(dp(getContext(), 12), slotW * 0.56f));

            paint.setColor(Color.parseColor("#22344A"));
            paint.setStrokeWidth(dp(getContext(), 1));
            canvas.drawLine(pad, bottom, w - pad, bottom, paint);

            for (int i = 0; i < n; i++) {
                double val = values.get(i);
                float cx = pad + (i + 0.5f) * slotW;
                float bh = (float) Math.max(dp(getContext(), 4), (val / maxVal) * (availH - dp(getContext(), 18)));
                rect.set(cx - barW / 2f, bottom - bh, cx + barW / 2f, bottom);

                paint.setStyle(Paint.Style.FILL);
                paint.setColor(ACCENT);
                canvas.drawRoundRect(rect, dp(getContext(), 5), dp(getContext(), 5), paint);

                String vStr = String.format(Locale.US, "%.1fh", val);
                paint.setColor(Color.parseColor("#CFE6FF"));
                paint.setTextSize(dp(getContext(), 10));
                float vw = paint.measureText(vStr);
                canvas.drawText(vStr, cx - vw / 2f, bottom - bh - dp(getContext(), 5), paint);

                String mStr = months.get(i);
                paint.setColor(TEXT_DIM);
                float mw = paint.measureText(mStr);
                canvas.drawText(mStr, cx - mw / 2f, bottom + dp(getContext(), 16), paint);
            }
        }
    }

    public interface TextChangeCallback {
        void onTextChanged(String text);
    }

    public static class SimpleTextWatcher implements android.text.TextWatcher {
        private final TextChangeCallback callback;

        public SimpleTextWatcher(TextChangeCallback callback) {
            this.callback = callback;
        }

        @Override
        public void beforeTextChanged(CharSequence s, int start, int count, int after) {}

        @Override
        public void onTextChanged(CharSequence s, int start, int before, int count) {}

        @Override
        public void afterTextChanged(android.text.Editable s) {
            if (callback != null) {
                callback.onTextChanged(s != null ? s.toString() : "");
            }
        }
    }
}
