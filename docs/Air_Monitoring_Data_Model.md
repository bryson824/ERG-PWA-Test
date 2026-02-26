# Air Monitoring Reference — How the Tables Work Together

Source: `data_reference/Air_Monitoring_Relationships-2.xlsx` (sheets exported to CSV for inspection).

---

## 1. Table roles and keys

| Table | Role | Primary key | Used as FK in |
|-------|------|-------------|----------------|
| **Chemicals** | Anchor: every chemical the system knows | `cas_number` (slug, e.g. `Acetic-Acid`, `*Benzene`) | Sensor_Chemical, Sensor_CrossSens, Chemical_Method, Chemical_Document |
| **Devices** | Physical instruments (MultiRAE, DustTrak, XAM-8000, etc.) | `device_id` (slug, e.g. `RAE-MULTIRAE-PRO`) | Device_Sensor |
| **Sensors** | Detection elements (PID, EC, LEL, etc.) | `sensor_id` (slug, e.g. `RAE-PID-10.6PPB`) | Device_Sensor, Sensor_Chemical, Sensor_CrossSens |
| **Sampling_Methods** | NIOSH/OSHA/EPA collection methods | `method_id` | Chemical_Method |
| **Documents** | SDSs, ERGs, tech bulletins | `document_id` | Chemical_Document |
| **Device_Sensor** | Junction: which sensors go in which devices | (device_id, sensor_id) | — |
| **Sensor_Chemical** | Junction: intended detection (sensor ↔ chemical) | (sensor_id, chemical_id) | — |
| **Sensor_CrossSens** | Junction: unintended interference (sensor sees wrong chemical) | (sensor_id, chemical_id) | — |
| **Chemical_Method** | Junction: which methods apply to which chemicals | (chemical_id, method_id) | — |
| **Chemical_Document** | Junction: which documents relate to which chemicals | (chemical_id, document_id) | — |

Slug convention: ALL CAPS, hyphens, no spaces (e.g. `RAE-MULTIRAE-PRO`, `RAE-PID-10.6PPB`).

---

## 2. How they join for common questions

### “What can detect chemical X?”

1. **Chemicals** — find the row for chemical X (e.g. by `cas_number` or `chemical_name`).
2. **Sensor_Chemical** — filter by that chemical’s key (`chemical_id`); get all `sensor_id`s that detect it.
3. **Sensors** — join to get sensor name, technology, range, resolution.
4. **Device_Sensor** — join to get which **Devices** can host each sensor.
5. **Devices** — get device name, model, type.

Result: list of (device, sensor) pairs that can detect chemical X, with correction factors and ranges from Sensor_Chemical and regulatory limits from Chemicals.

### “What does sensor Y detect (intended)?”

1. **Sensors** — get sensor Y.
2. **Sensor_Chemical** — filter by `sensor_id` = Y; get all `chemical_id`s and correction_factor, detection_range_low/high, range_unit.
3. **Chemicals** — join to get chemical names, PEL, REL, TLV, IDLH, AEGL, conversion.

Result: list of chemicals the sensor is meant to detect, with ranges and factors.

### “What interferes with sensor Y? (cross-sensitivity)”

1. **Sensors** — get sensor Y.
2. **Sensor_CrossSens** — filter by `sensor_id` = Y; get `chemical_id` (interferent), response_type, factor, test_concentration, response_reading, direction, source.
3. **Chemicals** — join to get name of the interfering chemical.

Result: list of chemicals that can cause false or skewed readings on sensor Y.

### “What sensors does device Z have?”

1. **Devices** — get device Z.
2. **Device_Sensor** — filter by `device_id` = Z; get `sensor_id`s (and slot_position, is_default if used).
3. **Sensors** — join to get sensor details.

Result: list of sensors that fit in device Z.

### “What methods / documents apply to chemical X?”

- **Chemical_Method**: chemical_id → method_id → **Sampling_Methods** (agency, method_number, method_name, url, etc.).
- **Chemical_Document**: chemical_id → document_id → **Documents** (title, doc_type, url).

---

## 3. Building the “air monitoring table” for the PWA

The [EPA R9 Air Monitoring Tables](https://r9data.response.epa.gov/r9responseguide/MainPage/AirMonitoringTables.html) style view is a **single flat table** with rows like:

| Target Compound | Instrument | Detection Level | PID Lamp, CF | … | PEL | REL | TLV | IDLH | PAC-1/2/3 | Air Sampling Method | … |

That corresponds to a **denormalized merge** of:

- **Chemicals** (compound, PEL, REL, TLV, IDLH, AEGL/PAC, conversion)
- **Sensor_Chemical** (detection range, correction factor, range unit)
- **Sensors** (instrument/sensor name, technology)
- **Device_Sensor** → **Devices** (instrument = device + sensor in practice; one row per device–sensor–chemical combination)
- Optionally **Sampling_Methods** via **Chemical_Method** for “Air Sampling Method”
- **Sensor_CrossSens** can be a separate section or extra columns (e.g. “Interferents”) rather than one row per interferent in the main table

So the **merge/tidy** step is:

1. Start from **Sensor_Chemical** (every intended sensor–chemical pair).
2. Join **Sensors** (sensor_id) for sensor name, technology, range, resolution.
3. Join **Devices** via **Device_Sensor** (sensor_id) so each row can show which device(s) host that sensor (may be multiple devices per sensor).
4. Join **Chemicals** (chemical_id) for compound name, PEL, REL, TLV, IDLH, AEGL, conversion.
5. Optionally join **Chemical_Method** → **Sampling_Methods** for method per chemical.
6. Flatten into one row per (chemical, device, sensor) or per (chemical, sensor) depending on desired granularity; add cross-sensitivity either as extra columns (e.g. “Key interferents”) or a separate lookup.

The PWA then caches this merged table (e.g. as JSON or CSV) for offline “air monitoring table” use; ExB can use the same join logic via AGOL view layers or a separate exported table.

---

## 4. Summary

- **Chemicals** is the anchor; devices and sensors link to it through **Sensor_Chemical** (and **Sensor_CrossSens** for interferents).
- **Device_Sensor** ties **Devices** and **Sensors**; **Sensor_Chemical** and **Sensor_CrossSens** tie **Sensors** and **Chemicals**.
- The “air monitoring table” is a **denormalized view** built by joining Sensor_Chemical → Sensors → Device_Sensor → Devices and Sensor_Chemical → Chemicals (plus optional method/document and cross-sensitivity), then flattening for the PWA and for the EPA-style reference view.
