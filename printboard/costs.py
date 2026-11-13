"""Cost analytics, energy calculation, and 3D print quote/pricing calculator."""
import datetime
import math
from collections import defaultdict


def mm_to_g(mm, diameter=1.75, density=1.24):
    """Convert filament length (mm) to weight (grams)."""
    return (mm or 0) / 10 * math.pi * (diameter / 20) ** 2 * density


def job_cost(grams, seconds, eur_per_kg=25.0, watts=150.0, eur_per_kwh=0.30, wear_per_h=0.10):
    h = (seconds or 0) / 3600
    return grams / 1000 * eur_per_kg + h * watts / 1000 * eur_per_kwh + h * wear_per_h


def stats(jobs, eur_per_kg=25.0, eur_per_kwh=0.30, watts=150.0, wear_per_h=0.10):
    done = [j for j in jobs if j.get("status") == "completed"]
    month = defaultdict(float)
    for j in jobs:
        if j.get("start_time"):
            month[datetime.date.fromtimestamp(j["start_time"]).strftime("%Y-%m")] += (
                j.get("total_duration") or 0
            ) / 3600

    hours = sum((j.get("total_duration") or 0) for j in jobs) / 3600
    total_mm = sum((j.get("filament_used") or 0) for j in jobs)
    filament_g = sum(mm_to_g(j.get("filament_used")) for j in jobs)
    mat_eur = (filament_g / 1000.0) * eur_per_kg
    pwr_eur = hours * (watts / 1000.0) * eur_per_kwh
    wear_eur = hours * wear_per_h

    return {
        "count": len(jobs),
        "completed": len(done),
        "ok": len(done),
        "success": (len(done) / len(jobs) * 100) if jobs else 0.0,
        "hours": hours,
        "meters": total_mm / 1000.0,
        "grams": filament_g,
        "filament_g": filament_g,
        "mat_eur": mat_eur,
        "pwr_eur": pwr_eur,
        "wear_eur": wear_eur,
        "total_eur": mat_eur + pwr_eur,
        "total_with_wear_eur": mat_eur + pwr_eur + wear_eur,
        "per_month": dict(sorted(month.items())),
    }


def calculate_quote(
    grams: float,
    hours: float,
    eur_per_kg: float = 25.0,
    watts: float = 150.0,
    eur_per_kwh: float = 0.30,
    wear_per_h: float = 0.15,
    prep_mins: float = 10.0,
    labor_eur_h: float = 25.0,
    waste_pct: float = 5.0,
    fail_risk_pct: float = 8.0,
    margin_pct: float = 35.0,
    vat_pct: float = 19.0,
    copies: int = 1,
):
    """Calculate a complete manufacturing & customer quote breakdown for 3D print jobs."""
    copies = max(1, int(copies or 1))
    grams_eff = max(0.0, float(grams or 0.0)) * (1.0 + max(0.0, float(waste_pct or 0.0)) / 100.0)
    hours_eff = max(0.0, float(hours or 0.0))

    mat_unit = (grams_eff / 1000.0) * float(eur_per_kg or 0.0)
    pwr_unit = hours_eff * (float(watts or 0.0) / 1000.0) * float(eur_per_kwh or 0.0)
    wear_unit = hours_eff * float(wear_per_h or 0.0)
    labor_unit = (max(0.0, float(prep_mins or 0.0)) / 60.0) * float(labor_eur_h or 0.0)

    machine_base = mat_unit + pwr_unit + wear_unit
    risk_unit = machine_base * (max(0.0, float(fail_risk_pct or 0.0)) / 100.0)
    production_unit = machine_base + risk_unit + labor_unit
    profit_unit = production_unit * (max(0.0, float(margin_pct or 0.0)) / 100.0)
    net_unit = production_unit + profit_unit
    vat_unit = net_unit * (max(0.0, float(vat_pct or 0.0)) / 100.0)
    gross_unit = net_unit + vat_unit

    return {
        "copies": copies,
        "grams_effective": round(grams_eff * copies, 1),
        "hours_total": round(hours_eff * copies, 2),
        "material_eur": round(mat_unit * copies, 2),
        "energy_eur": round(pwr_unit * copies, 2),
        "wear_eur": round(wear_unit * copies, 2),
        "labor_eur": round(labor_unit * copies, 2),
        "risk_eur": round(risk_unit * copies, 2),
        "production_cost_eur": round(production_unit * copies, 2),
        "profit_eur": round(profit_unit * copies, 2),
        "net_price_eur": round(net_unit * copies, 2),
        "vat_eur": round(vat_unit * copies, 2),
        "gross_price_eur": round(gross_unit * copies, 2),
        "unit_production_eur": round(production_unit, 2),
        "unit_net_eur": round(net_unit, 2),
        "unit_gross_eur": round(gross_unit, 2),
    }
