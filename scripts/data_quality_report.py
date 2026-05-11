#!/usr/bin/env python3
"""
Generate a static HTML data-quality report from Air_Monitoring_Relationships CSVs.
Uses the same CSV loading and Include filtering as build_data.py.

Usage:
  python scripts/data_quality_report.py
"""
from __future__ import annotations

import html
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

try:
    import pandas as pd
except ImportError:
    pd = None

# Reuse build pipeline helpers
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, os.path.join(_REPO, "scripts"))

from build_data import (  # noqa: E402
    _data_ref,
    filter_rows_by_include,
    normalize_header,
    read_csv_with_title_row,
    safe_str,
)


def _repo_root():
    return _REPO


def _out_dir():
    d = os.path.join(_data_ref(), "out")
    os.makedirs(d, exist_ok=True)
    return d


def _pwa_dir():
    return os.path.join(_repo_root(), "pwa")


def _base_csv(name: str) -> str:
    return os.path.join(_data_ref(), f"Air_Monitoring_Relationships-2_{name}.csv")


def _xlsx_path() -> str:
    return os.path.join(_data_ref(), "Air_Monitoring_Relationships-2.xlsx")


def _load_chemicals_raw() -> pd.DataFrame:
    """
    Prefer the workbook Chemicals sheet: the CSV export can split multiline cells into
    hundreds of thousands of spurious rows and is very slow to parse.
    """
    xlsx = _xlsx_path()
    if os.path.isfile(xlsx):
        df = pd.read_excel(xlsx, sheet_name="Chemicals", header=1, engine="openpyxl")
        df.columns = [normalize_header(c) for c in df.columns]
        return _valid_chemical_rows(df)
    path = _base_csv("Chemicals")
    if not os.path.isfile(path):
        return pd.DataFrame()
    df = read_csv_with_title_row(path)
    return _valid_chemical_rows(df)


def _load(name: str, label: str) -> pd.DataFrame | None:
    path = _base_csv(name)
    if not os.path.isfile(path):
        return None
    df = read_csv_with_title_row(path)
    return filter_rows_by_include(df, label)


def _load_optional(name: str, label: str) -> pd.DataFrame:
    df = _load(name, label)
    return df if df is not None else pd.DataFrame()


def _norm_id(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    if not s or s.lower() in ("nan", "na", "n/a"):
        return ""
    return " ".join(s.split())


def _valid_chemical_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chemicals CSV exports sometimes break multiline cells into extra physical rows.
    Keep only rows with a real cas_number slug (non-empty, not the literal 'nan').
    """
    if df is None or len(df) == 0 or "cas_number" not in df.columns:
        return df
    s = df["cas_number"].astype(str).str.strip()
    mask = s.ne("") & s.str.lower().ne("nan")
    return df.loc[mask].reset_index(drop=True)


def _field_missing_raw(val) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return True
    s = str(val).strip()
    if not s or s.lower() in ("nan", "na", "n/a", "—", "-"):
        return True
    return False


def _count_include_no(df: pd.DataFrame) -> int:
    for c in df.columns:
        if str(c).strip().lower() == "include":
            return int(df[c].astype(str).str.strip().str.lower().eq("no").sum())
    return 0


def _list_preview(items: list[str], limit: int = 120) -> str:
    if not items:
        return "<p class=\"muted\">None.</p>"
    extra = len(items) - limit
    show = items[:limit]
    lines = "".join(f"<li>{html.escape(x)}</li>" for x in show)
    more = f'<p class="muted">… and {extra} more.</p>' if extra > 0 else ""
    return f"<ul class=\"detail-list\">{lines}</ul>{more}"


def _section(title: str, body: str) -> str:
    return f'<section class="card"><h2>{html.escape(title)}</h2>{body}</section>'


def _stat_grid(pairs: list[tuple[str, str | int]]) -> str:
    cells = ""
    for label, val in pairs:
        cells += (
            f'<div class="stat"><span class="stat-label">{html.escape(label)}</span>'
            f'<span class="stat-value">{html.escape(str(val))}</span></div>'
        )
    return f'<div class="stat-grid">{cells}</div>'


def build_report() -> str:
    if pd is None:
        raise RuntimeError("pandas required")

    sc = _load("Sensor_Chemical", "Sensor_Chemical")
    sens = _load("Sensors", "Sensors")
    ds = _load("Device_Sensor", "Device_Sensor")
    dev = _load("Devices", "Devices")
    chem_u = _load_chemicals_raw()
    chem = filter_rows_by_include(chem_u.copy(), "Chemicals") if len(chem_u) else None
    cm = _load("Chemical_Method", "Chemical_Method")
    sm = _load("Sampling_Methods", "Sampling_Methods")
    xsen = _load_optional("Sensor_CrossSens", "Sensor_CrossSens")
    cdoc = _load_optional("Chemical_Document", "Chemical_Document")
    ddoc = _load_optional("Device_Document", "Device_Document")
    docs = _load_optional("Documents", "Documents")

    chem_raw = chem_u
    sens_raw = read_csv_with_title_row(_base_csv("Sensors")) if os.path.isfile(_base_csv("Sensors")) else pd.DataFrame()
    dev_raw = read_csv_with_title_row(_base_csv("Devices")) if os.path.isfile(_base_csv("Devices")) else pd.DataFrame()

    n_chem_excluded = _count_include_no(chem_raw) if len(chem_raw) else 0
    n_sens_excluded = _count_include_no(sens_raw) if len(sens_raw) else 0
    n_dev_excluded = _count_include_no(dev_raw) if len(dev_raw) else 0

    if sc is None or sens is None or ds is None or dev is None or chem is None:
        raise RuntimeError("Missing required CSVs / workbook in data_reference/")

    cas_set = set(chem["cas_number"].astype(str).map(_norm_id)) - {""}
    sensor_set = set(sens["sensor_id"].astype(str).map(_norm_id)) - {""}
    device_set = set(dev["device_id"].astype(str).map(_norm_id)) - {""}
    method_set = set(sm["method_id"].astype(str).map(_norm_id)) - {""} if len(sm) else set()
    doc_set = set(docs["document_id"].astype(str).map(_norm_id)) - {""} if len(docs) and "document_id" in docs.columns else set()

    # --- Orphans ---
    sc_bad_s = []
    sc_bad_c = []
    for _, row in sc.iterrows():
        sid = _norm_id(row.get("sensor_id"))
        cid = _norm_id(row.get("chemical_id"))
        if sid and sid not in sensor_set:
            sc_bad_s.append(f"Sensor_Chemical: sensor_id not in Sensors — {sid}")
        if cid and cid not in cas_set:
            sc_bad_c.append(f"Sensor_Chemical: chemical_id not in Chemicals — {cid}")

    ds_bad_d = []
    ds_bad_s = []
    for _, row in ds.iterrows():
        did = _norm_id(row.get("device_id"))
        sid = _norm_id(row.get("sensor_id"))
        if did and did not in device_set:
            ds_bad_d.append(f"Device_Sensor: device_id not in Devices — {did}")
        if sid and sid not in sensor_set:
            ds_bad_s.append(f"Device_Sensor: sensor_id not in Sensors — {sid}")

    cm_bad_c = []
    cm_bad_m = []
    for _, row in cm.iterrows():
        cid = _norm_id(row.get("chemical_id"))
        mid = _norm_id(row.get("method_id"))
        if cid and cid not in cas_set:
            cm_bad_c.append(f"Chemical_Method: chemical_id not in Chemicals — {cid}")
        if mid and mid not in method_set:
            cm_bad_m.append(f"Chemical_Method: method_id not in Sampling_Methods — {mid}")

    x_bad_s = []
    x_bad_c = []
    x_dup = []
    if len(xsen) and "sensor_id" in xsen.columns:
        seen_x = defaultdict(int)
        for _, row in xsen.iterrows():
            sid = _norm_id(row.get("sensor_id"))
            cid = _norm_id(row.get("chemical_id"))
            if not sid and not cid:
                continue
            if sid and sid not in sensor_set:
                x_bad_s.append(f"Sensor_CrossSens: sensor_id not in Sensors — {sid}")
            if cid and cid not in cas_set:
                x_bad_c.append(f"Sensor_CrossSens: chemical_id not in Chemicals — {cid}")
            if sid and cid:
                seen_x[(sid, cid)] += 1
        for (sid, cid), n in seen_x.items():
            if n > 1:
                x_dup.append(f"{sid} + {cid} ({n} rows)")

    cdoc_bad_c = []
    cdoc_bad_d = []
    if len(cdoc) and "chemical_id" in cdoc.columns:
        for _, row in cdoc.iterrows():
            cid = _norm_id(row.get("chemical_id"))
            did = _norm_id(row.get("document_id"))
            if not cid and not did:
                continue
            if cid and cid not in cas_set:
                cdoc_bad_c.append(f"Chemical_Document: chemical_id not in Chemicals — {cid}")
            if did and doc_set and did not in doc_set:
                cdoc_bad_d.append(f"Chemical_Document: document_id not in Documents — {did}")

    ddoc_bad_dev = []
    ddoc_bad_doc = []
    if len(ddoc) and "device_id" in ddoc.columns:
        for _, row in ddoc.iterrows():
            dv = _norm_id(row.get("device_id"))
            did = _norm_id(row.get("document_id"))
            if not dv and not did:
                continue
            if dv and dv not in device_set:
                ddoc_bad_dev.append(f"Device_Document: device_id not in Devices — {dv}")
            if did and doc_set and did not in doc_set:
                ddoc_bad_doc.append(f"Device_Document: document_id not in Documents — {did}")

    # Chemicals with no Sensor_Chemical
    chem_with_sc = set(sc["chemical_id"].astype(str).map(_norm_id)) - {""}
    chem_no_sensor = sorted(cas_set - chem_with_sc)

    # Sensors with no Sensor_Chemical
    sensors_with_sc = set(sc["sensor_id"].astype(str).map(_norm_id)) - {""}
    sens_no_chem = sorted(sensor_set - sensors_with_sc)

    # Devices with no Device_Sensor
    dev_with_ds = set(ds["device_id"].astype(str).map(_norm_id)) - {""}
    dev_no_sensor = sorted(device_set - dev_with_ds)

    # Sensor_Chemical rows whose sensor never appears on a device
    ds_sensors = set(ds["sensor_id"].astype(str).map(_norm_id)) - {""}
    sc_orphan_device = []
    for _, row in sc.iterrows():
        sid = _norm_id(row.get("sensor_id"))
        cid = _norm_id(row.get("chemical_id"))
        if sid and sid not in ds_sensors:
            sc_orphan_device.append(f"{sid} / {cid}")

    # PID rows missing correction_factor
    sens_tech = {}
    if "technology" in sens.columns:
        for _, row in sens.iterrows():
            sens_tech[_norm_id(row.get("sensor_id"))] = str(row.get("technology") or "").strip().upper()

    pid_missing_cf = []
    for _, row in sc.iterrows():
        sid = _norm_id(row.get("sensor_id"))
        cid = _norm_id(row.get("chemical_id"))
        if sens_tech.get(sid) != "PID":
            continue
        cf = row.get("correction_factor")
        if _field_missing_raw(cf):
            pid_missing_cf.append(f"{sid} / chemical {cid}")

    # Cross-sens: sensors with zero rows (optional table)
    xs_sensors = set()
    if len(xsen) and "sensor_id" in xsen.columns:
        xs_sensors = set(xsen["sensor_id"].astype(str).map(_norm_id)) - {""}
    sens_no_xs = sorted(sensor_set - xs_sensors)

    # Methods & docs coverage
    chem_with_method = set(cm["chemical_id"].astype(str).map(_norm_id)) - {""} if len(cm) else set()
    chem_no_method = sorted(cas_set - chem_with_method)

    chem_doc_counts: dict[str, int] = defaultdict(int)
    if len(cdoc) and "chemical_id" in cdoc.columns:
        for _, row in cdoc.iterrows():
            cid = _norm_id(row.get("chemical_id"))
            if cid:
                chem_doc_counts[cid] += 1
    chem_no_doc = sorted([c for c in cas_set if chem_doc_counts.get(c, 0) == 0])
    chem_one_doc = sorted([c for c in cas_set if chem_doc_counts.get(c, 0) == 1])

    dev_doc_counts: dict[str, int] = defaultdict(int)
    if len(ddoc) and "device_id" in ddoc.columns:
        for _, row in ddoc.iterrows():
            dv = _norm_id(row.get("device_id"))
            if dv:
                dev_doc_counts[dv] += 1
    dev_id_to_model = {}
    if "model" in dev.columns:
        for _, row in dev.iterrows():
            dev_id_to_model[_norm_id(row.get("device_id"))] = str(row.get("model") or "").strip()

    dev_0_doc = []
    dev_1_doc = []
    dev_2_doc = []
    for did in sorted(device_set):
        n = dev_doc_counts.get(did, 0)
        label = dev_id_to_model.get(did, did)
        if n == 0:
            dev_0_doc.append(f"{label} ({did})")
        elif n == 1:
            dev_1_doc.append(f"{label} ({did})")
        elif n == 2:
            dev_2_doc.append(f"{label} ({did})")

    # Unused parents
    used_methods = set(cm["method_id"].astype(str).map(_norm_id)) - {""} if len(cm) else set()
    unused_methods = sorted(method_set - used_methods) if method_set else []

    used_docs = set()
    if len(cdoc) and "document_id" in cdoc.columns:
        used_docs |= set(cdoc["document_id"].astype(str).map(_norm_id)) - {""}
    if len(ddoc) and "document_id" in ddoc.columns:
        used_docs |= set(ddoc["document_id"].astype(str).map(_norm_id)) - {""}
    unused_docs = sorted(doc_set - used_docs) if doc_set else []

    # Regulatory completeness (included chemicals only)
    reg_cols = [
        ("pel_ppm", "PEL"),
        ("rel", "REL"),
        ("tlv_ppm", "TLV"),
        ("stel_ppm", "STEL"),
        ("idlh_ppm", "IDLH"),
        ("aegl_1", "PAC-1 / AEGL-1"),
        ("aegl_2", "PAC-2 / AEGL-2"),
        ("aegl_3", "PAC-3 / AEGL-3"),
        ("IP (eV)", "IP (eV)"),
    ]
    chem_incomplete = []
    all_empty_rows = []
    for _, row in chem.iterrows():
        cas = _norm_id(row.get("cas_number"))
        name = str(row.get("chemical_name") or "").strip() or cas
        missing_labels = []
        for col_key, label in reg_cols:
            if col_key not in chem.columns:
                continue
            if _field_missing_raw(row.get(col_key)):
                missing_labels.append(label)
        if missing_labels:
            chem_incomplete.append(f"{name} ({cas}) — missing: {', '.join(missing_labels)}")
        if len(missing_labels) == len([c for c, _ in reg_cols if c in chem.columns]):
            all_empty_rows.append(f"{name} ({cas})")

    # Merge JSON checks
    merge_notes: list[str] = []
    json_path = os.path.join(_out_dir(), "air_monitoring_table.json")
    if not os.path.isfile(json_path):
        json_path = os.path.join(_pwa_dir(), "air_monitoring_table.json")
    if os.path.isfile(json_path):
        with open(json_path, encoding="utf-8") as f:
            merged = json.load(f)
        triplets = defaultdict(int)
        chem_only_dupes = defaultdict(int)
        blank_compound = 0
        for rec in merged:
            tc = str(rec.get("Target Compound") or "").strip()
            d = str(rec.get("Device") or "").strip()
            s = str(rec.get("Sensor") or "").strip()
            if tc in ("", "—"):
                blank_compound += 1
            if d == "—" and s == "—":
                chem_only_dupes[tc] += 1
            else:
                key = (tc, d, s)
                triplets[key] += 1
        dup_triplets = [f"{k[0]} | {k[1]} | {k[2]} ({n}×)" for k, n in triplets.items() if n > 1]
        dup_chem_only = [f"{k} ({n}×)" for k, n in chem_only_dupes.items() if n > 1]
        merge_notes.append(f"Rows in JSON: {len(merged)}")
        merge_notes.append(f"Blank Target Compound: {blank_compound}")
        merge_notes.append(f"Duplicate (Target, Device, Sensor) tuples: {len(dup_triplets)}")
        merge_notes.append(f"Chemical-only rows with duplicate Target Compound: {len(dup_chem_only)}")
    else:
        merged = None
        dup_triplets = []
        dup_chem_only = []
        merge_notes.append("air_monitoring_table.json not found — skipped merge checks.")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Summary block
    summary_pairs = [
        ("Chemicals (included)", len(chem)),
        ("Chemicals excluded (Include = No)", n_chem_excluded),
        ("Sensors (included)", len(sens)),
        ("Sensors excluded (Include = No)", n_sens_excluded),
        ("Devices (included)", len(dev)),
        ("Devices excluded (Include = No)", n_dev_excluded),
        ("Sensor_Chemical rows", len(sc)),
        ("Device_Sensor rows", len(ds)),
        ("Chemical_Method rows", len(cm)),
        ("Sensor_CrossSens rows", len(xsen)),
    ]
    summary_html = _stat_grid(summary_pairs)

    join_list_html = ""
    if x_dup:
        join_list_html += "<h4>Sensor_CrossSens duplicate (sensor, chemical) pairs</h4>" + _list_preview(sorted(set(x_dup)))
    orphan_lines = sorted(
        set(sc_bad_s + sc_bad_c + ds_bad_d + ds_bad_s + cm_bad_c + cm_bad_m + x_bad_s + x_bad_c + cdoc_bad_c + cdoc_bad_d + ddoc_bad_dev + ddoc_bad_doc)
    )
    join_list_html += "<h4>Orphan or invalid foreign keys</h4>" + _list_preview(orphan_lines)

    join_issues = (
        _stat_grid(
            [
                ("Sensor_Chemical bad sensor FK", len(sc_bad_s)),
                ("Sensor_Chemical bad chemical FK", len(sc_bad_c)),
                ("Device_Sensor bad device FK", len(ds_bad_d)),
                ("Device_Sensor bad sensor FK", len(ds_bad_s)),
                ("Chemical_Method bad chemical FK", len(cm_bad_c)),
                ("Chemical_Method bad method FK", len(cm_bad_m)),
                ("Sensor_CrossSens bad sensor FK", len(x_bad_s)),
                ("Sensor_CrossSens bad chemical FK", len(x_bad_c)),
                ("Sensor_CrossSens duplicate pairs", len(x_dup)),
                ("Chemical_Document bad chemical FK", len(cdoc_bad_c)),
                ("Chemical_Document bad document FK", len(cdoc_bad_d)),
                ("Device_Document bad device FK", len(ddoc_bad_dev)),
                ("Device_Document bad document FK", len(ddoc_bad_doc)),
            ]
        )
        + join_list_html
    )

    coverage_html = _stat_grid(
        [
            ("Chemicals with no Sensor_Chemical row", len(chem_no_sensor)),
            ("Sensors with no Sensor_Chemical row", len(sens_no_chem)),
            ("Devices with no Device_Sensor row", len(dev_no_sensor)),
            ("Sensor_Chemical rows (sensor not on any device)", len(sc_orphan_device)),
            ("PID Sensor_Chemical rows missing correction_factor", len(pid_missing_cf)),
            ("Sensors with no Sensor_CrossSens row", len(sens_no_xs)),
            ("Chemicals with no Chemical_Method row", len(chem_no_method)),
            ("Chemicals with no Chemical_Document link", len(chem_no_doc)),
            ("Chemicals with exactly one Chemical_Document", len(chem_one_doc)),
            ("Devices with zero Device_Document links", len(dev_0_doc)),
            ("Devices with exactly one Device_Document", len(dev_1_doc)),
            ("Devices with exactly two Device_Documents", len(dev_2_doc)),
            ("Sampling_Methods not referenced by Chemical_Method", len(unused_methods)),
            ("Documents not referenced (chemical or device)", len(unused_docs)),
        ]
    ) + "<h3>Detail lists</h3>"

    coverage_html += "<h4>Chemicals with no detection (no Sensor_Chemical)</h4>" + _list_preview(chem_no_sensor)
    coverage_html += "<h4>Sensors unused in Sensor_Chemical</h4>" + _list_preview(sens_no_chem)
    coverage_html += "<h4>Devices with no sensors (no Device_Sensor)</h4>" + _list_preview(dev_no_sensor)
    coverage_html += "<h4>Sensor_Chemical rows — sensor not on any device</h4>" + _list_preview(sorted(set(sc_orphan_device)))
    coverage_html += "<h4>PID rows missing correction_factor</h4>" + _list_preview(pid_missing_cf)
    coverage_html += "<h4>Sensors with no cross-sensitivity rows</h4>" + _list_preview(sens_no_xs)
    coverage_html += "<h4>Chemicals with no sampling method (Chemical_Method)</h4>" + _list_preview(chem_no_method)
    coverage_html += "<h4>Chemicals with no document link</h4>" + _list_preview(chem_no_doc)
    coverage_html += "<h4>Devices with zero documents</h4>" + _list_preview(dev_0_doc)
    coverage_html += "<h4>Devices with exactly one document</h4>" + _list_preview(dev_1_doc)
    coverage_html += "<h4>Devices with exactly two documents</h4>" + _list_preview(dev_2_doc)
    coverage_html += "<h4>Unreferenced sampling method IDs</h4>" + _list_preview(unused_methods)
    coverage_html += "<h4>Unreferenced document IDs</h4>" + _list_preview(unused_docs)

    reg_html = _stat_grid(
        [
            ("Included chemicals missing ≥1 regulatory field", len(chem_incomplete)),
            ("Included chemicals with all regulatory fields empty", len(all_empty_rows)),
        ]
    ) + "<h3>Chemicals with missing PEL, REL, TLV, STEL, IDLH, PAC, or IP</h3>"
    reg_html += _list_preview(sorted(chem_incomplete), limit=200)

    merge_html = "<p>" + "</p><p>".join(html.escape(x) for x in merge_notes) + "</p>"
    merge_html += "<h3>Duplicate instrument rows (same Target Compound + Device + Sensor)</h3>"
    merge_html += _list_preview(sorted(dup_triplets))
    merge_html += "<h3>Duplicate chemical-only rows (Device/Sensor = —)</h3>"
    merge_html += _list_preview(sorted(dup_chem_only))
    if not os.path.isfile(os.path.join(_out_dir(), "air_monitoring_table.json")) and not (
        os.path.isfile(os.path.join(_pwa_dir(), "air_monitoring_table.json"))
    ):
        merge_html += '<p class="muted">Build merged JSON with <code>python scripts/build_data.py</code> to populate merge checks.</p>'

    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="UTF-8" />',
        '<meta name="viewport" content="width=device-width, initial-scale=1" />',
        "<title>ERG — Data quality report</title>",
        "<style>",
        ":root { --epa: #002868; --bg: #e8eef7; --card: #fff; --muted: #555; }",
        "body { font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 0; background: var(--bg); color: #1c1c1c; line-height: 1.45; }",
        "header { background: var(--epa); color: #fff; padding: 1rem 1.25rem; }",
        "header h1 { margin: 0; font-size: 1.25rem; }",
        "header p { margin: 0.35rem 0 0 0; font-size: 0.875rem; opacity: 0.9; }",
        "main { max-width: 52rem; margin: 0 auto; padding: 1.25rem; }",
        ".card { background: var(--card); border: 1px solid #c5d4ed; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1rem; }",
        ".card h2 { margin: 0 0 0.75rem 0; font-size: 1.05rem; color: var(--epa); }",
        ".card h3 { font-size: 0.95rem; margin: 1rem 0 0.35rem 0; color: #333; }",
        ".card h4 { font-size: 0.85rem; margin: 0.75rem 0 0.25rem 0; color: var(--muted); }",
        ".stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr)); gap: 0.75rem; }",
        ".stat { background: #f4f7fc; border-radius: 6px; padding: 0.5rem 0.65rem; }",
        ".stat-label { display: block; font-size: 0.75rem; color: var(--muted); }",
        ".stat-value { font-size: 1.25rem; font-weight: 700; color: var(--epa); }",
        ".detail-list { margin: 0.25rem 0 0 1rem; padding: 0; font-size: 0.8125rem; max-height: 18rem; overflow: auto; }",
        ".detail-list li { margin-bottom: 0.2rem; }",
        ".muted { color: var(--muted); font-size: 0.875rem; }",
        "code { background: #eef2f8; padding: 0.1rem 0.3rem; border-radius: 3px; font-size: 0.85em; }",
        "</style>",
        "</head>",
        "<body>",
        "<header><h1>ERG data quality report</h1>",
        f"<p>Generated {html.escape(ts)} · Same <code>Include</code> filtering as <code>build_data.py</code></p>",
        "</header>",
        "<main>",
        _section("Summary", summary_html),
        _section("Join integrity (orphan foreign keys)", join_issues),
        _section("Coverage gaps", coverage_html),
        _section("Chemical regulatory fields", reg_html),
        _section("Merged table JSON", merge_html),
        "</main>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def main():
    if pd is None:
        print("Install pandas: pip install pandas", file=sys.stderr)
        sys.exit(1)
    html_out = build_report()
    out_path = os.path.join(_out_dir(), "data_quality_report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"Wrote {out_path}")
    pwa_path = os.path.join(_pwa_dir(), "data-quality.html")
    if os.path.isdir(_pwa_dir()):
        with open(pwa_path, "w", encoding="utf-8") as f:
            f.write(html_out)
        print(f"Copied to {pwa_path}")


if __name__ == "__main__":
    main()
