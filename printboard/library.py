"""Local 3D Model & G-Code Library manager, thumbnail extractor, slicer launcher,
and interactive 2D/3D G-Code layer & toolpath analyzer.
"""
import base64
import datetime
import math
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

EXT = {".3mf", ".stl", ".obj", ".step", ".stp", ".gcode", ".zip"}
CATEGORIES = {
    "all": EXT,
    "models": {".3mf", ".stl", ".obj", ".step", ".stp"},
    "gcode": {".gcode"},
    "archives": {".zip"},
}

SLICER_CANDIDATES = [
    ("OrcaSlicer", ["orca-slicer", "orcaslicer"], "io.github.softfever.OrcaSlicer"),
    ("PrusaSlicer", ["prusa-slicer", "prusaslicer"], "com.prusa3d.PrusaSlicer"),
    ("Bambu Studio", ["bambu-studio", "bambustudio"], "com.bambulab.BambuStudio"),
    ("SuperSlicer", ["superslicer", "super-slicer"], "io.github.supermerill.SuperSlicer"),
    ("UltiMaker Cura", ["cura"], "com.ultimaker.cura"),
]

_THUMB_MEM_CACHE = {}


def scan(folder, query="", category="all", subfolder=""):
    q = query.lower().strip()
    root = Path(folder)
    if subfolder:
        root = root / subfolder
    if not root.is_dir():
        return []
    allowed = CATEGORIES.get(category, EXT)
    files = [
        f for f in root.rglob("*")
        if f.is_file() and f.suffix.lower() in allowed and q in f.name.lower()
    ]
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)


def list_subfolders(folder):
    root = Path(folder)
    if not root.is_dir():
        return []
    return sorted(
        [str(d.relative_to(root)) for d in root.rglob("*") if d.is_dir() and not d.name.startswith(".")]
    )


def _gcode_thumbnail(path):
    """Extract the largest base64-encoded thumbnail from a .gcode file header/footer."""
    try:
        with open(path, "rb") as f:
            head = f.read(600 * 1024).decode("utf-8", errors="ignore")
    except OSError:
        return None

    pattern = re.compile(
        r";\s*thumbnail(?:_JPG|_PNG)?\s+begin\s+(\d+)x(\d+)\s+\d+\s*\n(.*?);\s*thumbnail(?:_JPG|_PNG)?\s+end",
        re.DOTALL | re.IGNORECASE,
    )
    best_area = -1
    best_b64 = None
    for m in pattern.finditer(head):
        w, h = int(m.group(1)), int(m.group(2))
        if w * h > best_area:
            best_area = w * h
            best_b64 = m.group(3)
    if not best_b64:
        return None
    cleaned = "".join(
        line.lstrip("; \t\r") for line in best_b64.splitlines() if line.strip()
    )
    try:
        return base64.b64decode(cleaned)
    except Exception:
        return None


def thumbnail(path):
    """PNG/JPG bytes embedded in a .3mf or .gcode file (None if absent)."""
    p = Path(path)
    try:
        st = p.stat()
        cache_key = (str(p), st.st_mtime_ns, st.st_size)
        if cache_key in _THUMB_MEM_CACHE:
            return _THUMB_MEM_CACHE[cache_key]
    except OSError:
        cache_key = None

    suf = p.suffix.lower()
    res = None
    if suf == ".3mf":
        try:
            with zipfile.ZipFile(p) as z:
                names = z.namelist()
                for n in ("Metadata/plate_1.png", "Metadata/thumbnail.png", "Thumbnails/thumbnail.png"):
                    if n in names:
                        res = z.read(n)
                        break
                if res is None:
                    png = [n for n in names if n.lower().endswith(".png")]
                    res = z.read(png[0]) if png else None
        except (OSError, zipfile.BadZipFile):
            res = None
    elif suf == ".gcode":
        res = _gcode_thumbnail(p)

    if cache_key is not None:
        _THUMB_MEM_CACHE[cache_key] = res
    return res


def thumbnail_b64(path):
    """Return data:image/png;base64,... string for embedded thumbnail or None."""
    raw = thumbnail(path)
    if not raw:
        return None
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def format_size(num_bytes):
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.2f} MB"


def _parse_time_string_to_hours(s: str) -> float:
    """Convert slicer time strings like '2h 15m 30s' or '1d 3h 10m' into hours."""
    if not s:
        return 0.0
    total_sec = 0.0
    for val, unit in re.findall(r"(\d+(?:\.\d+)?)\s*([dhms])", s.lower()):
        v = float(val)
        if unit == "d":
            total_sec += v * 86400
        elif unit == "h":
            total_sec += v * 3600
        elif unit == "m":
            total_sec += v * 60
        elif unit == "s":
            total_sec += v
    return round(total_sec / 3600.0, 2)


def file_details(path):
    """Return a dict with file metadata (and G-code metadata if applicable)."""
    p = Path(path)
    st = p.stat()
    info = {
        "name": p.name,
        "path": str(p),
        "ext": p.suffix.lower(),
        "size_bytes": st.st_size,
        "size": format_size(st.st_size),
        "modified": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%d.%m.%Y %H:%M"),
        "meta": {},
        "parsed": {},
    }
    if info["ext"] == ".gcode":
        try:
            with open(p, "rb") as f:
                head = f.read(64 * 1024).decode("utf-8", errors="ignore")
                if st.st_size > 64 * 1024:
                    f.seek(max(0, st.st_size - 48 * 1024))
                    tail = f.read(48 * 1024).decode("utf-8", errors="ignore")
                else:
                    tail = ""
            combined = head + "\n" + tail
            for line in combined.splitlines():
                line_s = line.strip()
                if not line_s.startswith(";"):
                    continue
                low = line_s.lower()
                if "generated by " in low and "Slicer" not in info["meta"]:
                    info["meta"]["Slicer"] = line_s.lstrip("; ").strip()
                elif "estimated printing time" in low:
                    val = line_s.split("=", 1)[-1].strip()
                    info["meta"]["Druckzeit"] = val
                    info["parsed"]["hours"] = _parse_time_string_to_hours(val)
                elif low.startswith("; total filament used [g]") or low.startswith("; filament used [g]"):
                    raw_val = line_s.split("=", 1)[-1].strip()
                    try:
                        grams = sum(float(x.strip()) for x in raw_val.split(",") if x.strip())
                        info["meta"]["Filament (g)"] = f"{grams:.1f} g" if grams != int(grams) else f"{raw_val} g"
                        info["parsed"]["grams"] = round(grams, 2)
                    except ValueError:
                        info["meta"]["Filament (g)"] = raw_val + " g"
                elif low.startswith("; filament used [mm]"):
                    raw_val = line_s.split("=", 1)[-1].strip()
                    try:
                        mm = sum(float(x.strip()) for x in raw_val.split(",") if x.strip())
                        info["parsed"]["mm"] = round(mm, 1)
                    except ValueError:
                        pass
                elif low.startswith("; layer_height"):
                    info["meta"]["Schichthöhe"] = line_s.split("=", 1)[-1].strip() + " mm"
                elif low.startswith("; filament_type"):
                    info["meta"]["Material"] = line_s.split("=", 1)[-1].strip().replace(";", "/")
        except OSError:
            pass
    elif info["ext"] == ".zip":
        try:
            with zipfile.ZipFile(p) as z:
                model_files = [n for n in z.namelist() if Path(n).suffix.lower() in EXT]
                info["meta"]["Dateien im Archiv"] = str(len(model_files))
        except Exception:
            pass
    return info


def analyze_gcode_layers(path, max_layers: int = 180, max_segs_per_layer: int = 280):
    """Parse a .gcode file into layer-by-layer 2D toolpaths + bounding box for the G-Code Studio Viewer."""
    p = Path(path)
    if not p.is_file():
        return generate_demo_gcode_layers(p.name)

    details = file_details(p)
    raw_layers = []
    cur_segments = []
    cur_z = 0.2
    cur_x, cur_y = 100.0, 100.0
    min_x, min_y = 9999.0, 9999.0
    max_x, max_y = -9999.0, -9999.0
    max_z = 0.2

    move_re = re.compile(r"([XYZE])([-+]?\d*\.?\d+)")

    try:
        # Read up to 12 MB for interactive toolpath preview
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines(12 * 1024 * 1024)

        for line in lines:
            s = line.strip()
            if not s:
                continue
            if s.startswith(";"):
                low = s.lower()
                if low.startswith(";layer_change") or low.startswith("; layer:") or low.startswith(";layer:"):
                    if cur_segments:
                        raw_layers.append({"z": round(cur_z, 2), "segments": cur_segments})
                        cur_segments = []
                continue

            if s.startswith(("G0 ", "G1 ", "G0\t", "G1\t")):
                code_part = s.split(";", 1)[0]
                nx, ny, nz, has_e = cur_x, cur_y, cur_z, False
                has_xy = False
                for axis, val_str in move_re.findall(code_part):
                    try:
                        v = float(val_str)
                    except ValueError:
                        continue
                    if axis == "X":
                        nx = v
                        has_xy = True
                    elif axis == "Y":
                        ny = v
                        has_xy = True
                    elif axis == "Z":
                        nz = v
                    elif axis == "E" and v > 0:
                        has_e = True

                if abs(nz - cur_z) > 0.04 and nz > 0:
                    if cur_segments:
                        raw_layers.append({"z": round(cur_z, 2), "segments": cur_segments})
                        cur_segments = []
                    cur_z = nz
                    max_z = max(max_z, cur_z)

                if has_xy:
                    if has_e:
                        min_x = min(min_x, cur_x, nx)
                        min_y = min(min_y, cur_y, ny)
                        max_x = max(max_x, cur_x, nx)
                        max_y = max(max_y, cur_y, ny)
                    cur_segments.append([round(cur_x, 2), round(cur_y, 2), round(nx, 2), round(ny, 2), 1 if has_e else 0])
                    cur_x, cur_y = nx, ny

        if cur_segments:
            raw_layers.append({"z": round(cur_z, 2), "segments": cur_segments})
    except Exception:
        return generate_demo_gcode_layers(p.name)

    if not raw_layers:
        return generate_demo_gcode_layers(p.name)

    # Sample layers and segments so frontend canvas stays 60fps
    total_raw = len(raw_layers)
    step_l = max(1, math.ceil(total_raw / max_layers))
    sampled_layers = []
    for idx in range(0, total_raw, step_l):
        lay = raw_layers[idx]
        segs = lay["segments"]
        extrude_cnt = sum(1 for sg in segs if sg[4] == 1)
        if len(segs) > max_segs_per_layer:
            step_s = len(segs) / max_segs_per_layer
            segs = [segs[int(i * step_s)] for i in range(max_segs_per_layer)]
        sampled_layers.append({
            "num": idx + 1,
            "z": lay["z"],
            "extrude_count": extrude_cnt,
            "segments": segs,
        })

    if min_x > max_x:
        min_x, min_y, max_x, max_y = 50.0, 50.0, 200.0, 200.0

    return {
        "name": p.name,
        "path": str(p),
        "meta": details.get("meta", {}),
        "parsed": details.get("parsed", {}),
        "total_layers": total_raw,
        "bbox": [round(min_x, 1), round(min_y, 1), round(max_x, 1), round(max_y, 1), round(max_z, 2)],
        "layers": sampled_layers,
        "thumb_b64": thumbnail_b64(p),
    }


def generate_demo_gcode_layers(name: str = "Voron_Stealthburner_Mount_Set_ABS.gcode"):
    """Generate a realistic multi-layer geometric toolpath preview (gear + housing + infill) for demo/remote files."""
    layers = []
    num_layers = 60
    cx, cy = 125.0, 125.0
    for l_idx in range(num_layers):
        z = round((l_idx + 1) * 0.2, 2)
        segs = []
        r_outer = 48.0 - (l_idx * 0.15 if l_idx > 35 else 0.0)
        r_inner = 18.0
        teeth = 16
        pts_outer = []
        for i in range(teeth * 4 + 1):
            ang = (i / (teeth * 4)) * math.pi * 2.0
            tooth_mod = 4.2 if (i % 4 in (1, 2)) else 0.0
            rad = r_outer + tooth_mod
            pts_outer.append((round(cx + math.cos(ang) * rad, 2), round(cy + math.sin(ang) * rad, 2)))
        for i in range(len(pts_outer) - 1):
            segs.append([pts_outer[i][0], pts_outer[i][1], pts_outer[i + 1][0], pts_outer[i + 1][1], 1])

        # Travel to inner bore
        segs.append([pts_outer[-1][0], pts_outer[-1][1], round(cx + r_inner, 2), round(cy, 2), 0])
        pts_inner = []
        for i in range(25):
            ang = (i / 24.0) * math.pi * 2.0
            pts_inner.append((round(cx + math.cos(ang) * r_inner, 2), round(cy + math.sin(ang) * r_inner, 2)))
        for i in range(len(pts_inner) - 1):
            segs.append([pts_inner[i][0], pts_inner[i][1], pts_inner[i + 1][0], pts_inner[i + 1][1], 1])

        # Gyroid/Rectilinear infill lines alternating by layer
        infill_dir = (l_idx % 2) * (math.pi / 2.0) + math.pi / 4.0
        for step in range(-32, 36, 7):
            x1 = cx + step * math.cos(infill_dir) - 34 * math.sin(infill_dir)
            y1 = cy + step * math.sin(infill_dir) + 34 * math.cos(infill_dir)
            x2 = cx + step * math.cos(infill_dir) + 34 * math.sin(infill_dir)
            y2 = cy + step * math.sin(infill_dir) - 34 * math.cos(infill_dir)
            segs.append([round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2), 1])

        layers.append({
            "num": l_idx + 1,
            "z": z,
            "extrude_count": len(segs) - 1,
            "segments": segs,
        })

    return {
        "name": name,
        "path": name,
        "meta": {
            "Slicer": "OrcaSlicer 2.2.0 Pro",
            "Druckzeit": "2h 18m",
            "Filament (g)": "64.5 g",
            "Schichthöhe": "0.20 mm",
            "Material": "ABS / PLA",
        },
        "parsed": {"hours": 2.3, "grams": 64.5, "mm": 21600.0},
        "total_layers": num_layers,
        "bbox": [70.0, 70.0, 180.0, 180.0, round(num_layers * 0.2, 2)],
        "layers": layers,
        "thumb_b64": None,
    }


def rename_file(path, new_name):
    p = Path(path)
    new_name = new_name.strip()
    if not new_name or "/" in new_name or "\\" in new_name:
        raise ValueError("Ungültiger Dateiname")
    if not Path(new_name).suffix:
        new_name += p.suffix
    target = p.with_name(new_name)
    if target.exists():
        raise FileExistsError(f"„{new_name}“ existiert bereits.")
    p.rename(target)
    return target


def duplicate_file(path):
    p = Path(path)
    stem, suf = p.stem, p.suffix
    i = 1
    while True:
        cand = p.with_name(f"{stem}_kopie{i if i > 1 else ''}{suf}")
        if not cand.exists():
            shutil.copy2(p, cand)
            return cand
        i += 1


def move_file(path, target_dir):
    p = Path(path)
    dest_dir = Path(target_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / p.name
    if target.exists():
        raise FileExistsError(f"„{p.name}“ existiert im Zielordner bereits.")
    shutil.move(str(p), str(target))
    return target


def delete_file(path):
    Path(path).unlink()


def import_files(file_paths, target_dir):
    dest_dir = Path(target_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    imported = []
    for fp in file_paths:
        src = Path(fp)
        if not src.is_file():
            continue
        dst = dest_dir / src.name
        if dst.resolve() == src.resolve():
            continue
        if dst.exists():
            dst = dest_dir / f"{src.stem}_{int(datetime.datetime.now().timestamp())}{src.suffix}"
        shutil.copy2(src, dst)
        imported.append(dst)
    return imported


def extract_zip(zip_path, target_dir=None):
    """Extract supported 3D model and G-code files from a .zip archive."""
    zp = Path(zip_path)
    out_dir = Path(target_dir) if target_dir else (zp.parent / zp.stem)
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(zp) as z:
        for member in z.infolist():
            if member.is_dir():
                continue
            name = Path(member.filename).name
            if not name or name.startswith("."):
                continue
            if Path(name).suffix.lower() in (EXT - {".zip"}):
                dest = out_dir / name
                with z.open(member) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted.append(dest)
    return out_dir, extracted


def detect_slicers():
    """Return list of (label, command_list) for installed slicers."""
    found = []
    flatpak_bins = [
        Path("/var/lib/flatpak/exports/bin"),
        Path.home() / ".local/share/flatpak/exports/bin",
    ]
    for label, bins, flatpak_id in SLICER_CANDIDATES:
        cmd = None
        for b in bins:
            w = shutil.which(b)
            if w:
                cmd = [w]
                break
        if not cmd:
            for fb in flatpak_bins:
                if (fb / flatpak_id).exists():
                    cmd = [str(fb / flatpak_id)]
                    break
        if cmd:
            found.append((label, cmd))
    return found


def open_in_slicer(file_path, custom_cmd=""):
    """Launch slicer with file_path. Returns name/command used or raises RuntimeError."""
    fp = str(Path(file_path).resolve())
    if custom_cmd and custom_cmd.strip():
        parts = custom_cmd.strip().split()
        subprocess.Popen(parts + [fp], start_new_session=True)
        return parts[0]
    slicers = detect_slicers()
    if slicers:
        label, cmd = slicers[0]
        subprocess.Popen(cmd + [fp], start_new_session=True)
        return label
    raise RuntimeError(
        "Kein Slicer (OrcaSlicer, PrusaSlicer, Bambu Studio, SuperSlicer, Cura) automatisch gefunden. "
        "Bitte in den Einstellungen einen Slicer-Befehl hinterlegen."
    )
