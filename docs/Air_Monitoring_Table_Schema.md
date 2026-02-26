# Air Monitoring Table — Schema, Merge Spec & Acceptance Criteria

**Owner:** business-analyst  
**Consumers:** `scripts/build_data.py` (merge output), PWA shell (esri-sme), air sheet UI (ui-engineer)  
**Design refs:** `docs/ERG_Offline_PWA_Data_Plan.md` §0, §2, §4; `docs/Air_Monitoring_Data_Model.md` §3; `docs/ERG_Handoff_Implementation.md`; `docs/ERG_PWA_ExB_Decision.md` §4.

This document **locks** the column set and merge output shape so the build script and PWA stay in sync. ui-engineer uses this column set for the frozen table; esri-sme/build script produce this shape.

---

## 1. Output shape (locked)

The merge script MUST write a **JSON array of objects**. One object per row; keys = column names (exact strings below). Order of keys in each object SHOULD match the column order in §2 for consistency; consumers MAY rely on key order or iterate keys in the order listed.

**Example:**

```json
[
  {
    "Target Compound": "Acetic Acid",
    "Device": "MultiRAE Pro",
    "Sensor": "PID 10.6 eV",
    "Detection Level": "0.1 ppm",
    "PID Lamp / CF": "10.6 eV / 1.0",
    "PEL": "10 ppm",
    "REL": "10 ppm (ST) 15 ppm",
    "TLV": "10 ppm",
    "IDLH": "50 ppm",
    "PAC-1": "—",
    "PAC-2": "—",
    "PAC-3": "—",
    "Air Sampling Method": "—"
  }
]
```

**Output path:** `data_reference/out/air_monitoring_table.json`. Copy to `pwa/air_monitoring_table.json` for PWA to serve (per build/deploy process).

---

## 2. Column set and order (locked)

| # | Column name (exact)   | Description (for UI/labels) |
|---|------------------------|-----------------------------|
| 1 | Target Compound        | Chemical name (display). **Show once per chemical** (merged/grouped in UI). |
| 2 | Device                 | Device model (e.g. "MultiRAE Pro"). **Show once per device** (merged/grouped in UI). |
| 3 | Sensor                 | Sensor name (e.g. "Combustible Gases (LEL-1)"). **One row per sensor** (independent rows). |
| 4 | Detection Level        | Human-readable range (e.g. "0.1 ppm", "0–100 %LEL"). |
| 5 | Ionization Potential (eV) | From Chemicals (IP (eV)); **show once per chemical** (merged in UI). |
| 6 | Correction Factor      | From Sensor_Chemical (per sensor/chemical); "—" when not applicable (e.g. non-PID). |
| 7 | PEL                    | Permissible Exposure Limit. **Show once per chemical** (same row as Target Compound). |
| 8 | REL                    | Recommended Exposure Limit. **Show once per chemical**. |
| 9 | TLV                    | Threshold Limit Value. **Show once per chemical**. |
|10 | IDLH                   | Immediately Dangerous to Life or Health. **Show once per chemical**. |
|11 | PAC-1                  | AEGL-1 / PAC-1. **Show once per chemical**. |
|12 | PAC-2                  | AEGL-2 / PAC-2. **Show once per chemical**. |
|13 | PAC-3                  | AEGL-3 / PAC-3. **Show once per chemical**. |
|14 | Air Sampling Method    | Method(s) from Sampling_Methods; "—" if none. |

**Note:** The placeholder `pwa/air_monitoring_table.json` currently uses a subset of keys and no PAC columns. **Final keys** for ui-engineer/esri-sme alignment: use the 12 names above. If the placeholder is kept for dev, align it to this set (add missing keys with placeholder values like `"—"`).

---

## 3. Merge spec (source → output column)

Merge logic follows `docs/Air_Monitoring_Data_Model.md` §3: start from **Sensor_Chemical**, join **Sensors** → **Device_Sensor** → **Devices**, join **Chemicals**; optionally **Chemical_Method** → **Sampling_Methods**. One row per **(chemical, device, sensor)**.

**Source tables (CSV names after Excel export):**

- `Air_Monitoring_Relationships-2_Sensor_Chemical.csv`
- `Air_Monitoring_Relationships-2_Sensors.csv`
- `Air_Monitoring_Relationships-2_Device_Sensor.csv`
- `Air_Monitoring_Relationships-2_Devices.csv`
- `Air_Monitoring_Relationships-2_Chemicals.csv`
- (Optional) `Air_Monitoring_Relationships-2_Chemical_Method.csv`, `Air_Monitoring_Relationships-2_Sampling_Methods.csv`

**Join keys:**  
`Sensor_Chemical.chemical_id` → `Chemicals.cas_number`  
`Sensor_Chemical.sensor_id` → `Sensors.sensor_id`  
`Sensors.sensor_id` → `Device_Sensor.sensor_id`  
`Device_Sensor.device_id` → `Devices.device_id`  
(Optional) `Chemical_Method.chemical_id` → `Chemicals.cas_number`, `Chemical_Method.method_id` → `Sampling_Methods.method_id`.

**CSV headers:** First data row may be a title row; second row is typically the header. Normalize column names (e.g. strip `(PK)` / `(FK)` for joins). Use the **second row** as header if row 1 is title-only.

| Output column (exact) | Source | Source column(s) | Notes |
|----------------------|--------|-------------------|--------|
| Target Compound       | Chemicals | `chemical_name` | From Chemicals via Sensor_Chemical.chemical_id → cas_number. |
| Instrument            | Devices + Sensors | `Devices.model` (or device display name), `Sensors.plain_name` (or sensor display) | Format e.g. `"{device_display} / {sensor_display}"`. Prefer human-readable labels (e.g. "MultiRAE Pro", "PID 10.6 eV"). |
| Detection Level       | Sensor_Chemical + Sensors | `detection_range_low`, `detection_range_high`, `range_unit` (Sensor_Chemical); or `Sensors.detection_range`, `resolution` if needed | Format as readable string, e.g. "0.1 ppm", "0–100 %LEL". |
| PID Lamp / CF         | Sensors + Sensor_Chemical | Sensor technology/lamp info if present; `Sensor_Chemical.correction_factor` | Use "—" or "N/A" for non-PID sensors. |
| PEL                   | Chemicals | `pel_ppm` | Copy as-is (may contain text like "10 ppm (25 mg/m³)"). |
| REL                   | Chemicals | `rel` | Copy as-is. |
| TLV                   | Chemicals | `tlv_ppm` | Copy as-is. |
| IDLH                  | Chemicals | `idlh_ppm` | Copy as-is. |
| PAC-1                 | Chemicals | `aegl_1` | Map AEGL-1 to PAC-1; use "—" if empty. |
| PAC-2                 | Chemicals | `aegl_2` | Map AEGL-2 to PAC-2; use "—" if empty. |
| PAC-3                 | Chemicals | `aegl_3` | Map AEGL-3 to PAC-3; use "—" if empty. |
| Air Sampling Method   | Sampling_Methods (via Chemical_Method) | e.g. `method_name`, or `agency` + `method_number` | One method per chemical (e.g. first match), or concatenate; "—" if no method. |

**Row grain:** One row per (chemical, device, sensor) — i.e. each Sensor_Chemical row is expanded by each (device_id, sensor_id) pair from Device_Sensor for that sensor. No duplicate (chemical, device, sensor) rows unless the source data intentionally has duplicates (e.g. multiple method rows); if so, define rule (e.g. one row per method or collapse to one row with combined method text).

---

## 4. Acceptance criteria (correct table content)

- **AC1 — Row identity:** Every row has a non-empty **Target Compound** and non-empty **Instrument**. (No blank compound or instrument.)
- **AC2 — Key regulatory columns:** Every row has the columns **PEL**, **REL**, **TLV**, **IDLH**, **PAC-1**, **PAC-2**, **PAC-3**. Values may be "—", "N/A", or empty string if not defined in source; the key must exist.
- **AC3 — Detection Level:** Every row has a **Detection Level** value (formatted string or "—"/"N/A" if not applicable).
- **AC4 — No duplicate (chemical, device, sensor):** There is at most one row per unique (Target Compound, Instrument) pair, where Instrument is uniquely defined per (device, sensor). If Chemical_Method adds multiple methods per chemical, either one row per method or a single row with combined method text; the spec in §3 must be implemented accordingly and no unintended duplicate (chemical, device, sensor) rows appear.
- **AC5 — Column set:** The JSON array has exactly the 12 keys listed in §2; no extra keys required for minimal acceptance (optional keys allowed only if agreed).
- **AC6 — Offline usability:** When the PWA loads `air_monitoring_table.json`, the table renders without error; frozen header and frozen first column (ui-engineer) use these column names.

---

## 5. Coordination

| Role | Use this doc for |
|------|-------------------|
| **build script / build_data.py** | Implement merge per §3; write JSON array of objects with keys and order per §2 to `data_reference/out/air_monitoring_table.json`. |
| **esri-sme** | Consume this shape in the PWA shell; ensure cached `air_monitoring_table.json` matches this schema. Copy output to `pwa/air_monitoring_table.json` in build/deploy. |
| **ui-engineer** | Use the 12 column names in §2 for the frozen table (header row and first column = "Target Compound"). If placeholder JSON has different keys, replace with the final set above. |

**Placeholder vs final:** The current `pwa/air_monitoring_table.json` has keys: `Target Compound`, `Instrument`, `Detection Level`, `PEL`, `REL`, `TLV`, `IDLH`, `Air Sampling Method`. Final keys add: `PID Lamp / CF`, `PAC-1`, `PAC-2`, `PAC-3`. Column order in §2 is canonical.
