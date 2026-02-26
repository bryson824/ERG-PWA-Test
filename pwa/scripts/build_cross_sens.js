/**
 * Builds sensor_cross_sens.json from Sensors and Sensor_CrossSens CSVs.
 * Run from repo root: node pwa/scripts/build_cross_sens.js
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '../..');
const SENSORS_CSV = path.join(ROOT, 'data_reference', 'Air_Monitoring_Relationships-2_Sensors.csv');
const CROSS_CSV = path.join(ROOT, 'data_reference', 'Air_Monitoring_Relationships-2_Sensor_CrossSens.csv');
const OUT = path.join(ROOT, 'pwa', 'sensor_cross_sens.json');

function parseCSV(content) {
  const rows = [];
  let i = 0;
  while (i < content.length) {
    const row = [];
    let cell = '';
    let inq = false;
    while (i < content.length) {
      const c = content[i];
      if (c === '"') {
        inq = !inq;
        i++;
        continue;
      }
      if (!inq && (c === ',' || c === '\n' || c === '\r')) {
        row.push(cell.trim());
        cell = '';
        if (c === '\n' || c === '\r') {
          if (c === '\r' && content[i + 1] === '\n') i++;
          i++;
          break;
        }
        i++;
        continue;
      }
      cell += c;
      i++;
    }
    if (cell !== '' || row.length > 0) row.push(cell.trim());
    if (row.length > 0 && row.some((v) => v !== '')) rows.push(row);
  }
  return rows;
}

// Sensors: first row may be title; second is header
const sensorsContent = fs.readFileSync(SENSORS_CSV, 'utf8');
const sensorRows = parseCSV(sensorsContent);
const headerS = sensorRows[1] || sensorRows[0] || [];
const idxSensorId = headerS.findIndex((h) => h && h.toLowerCase().includes('sensor_id'));
const idxPlain = headerS.findIndex((h) => h && h.toLowerCase().includes('plain_name'));
const displayNameToSensorIds = {};
for (let r = 2; r < sensorRows.length; r++) {
  const row = sensorRows[r];
  const sid = row[idxSensorId];
  const plain = row[idxPlain];
  if (!sid || !plain) continue;
  if (!displayNameToSensorIds[plain]) displayNameToSensorIds[plain] = [];
  if (displayNameToSensorIds[plain].indexOf(sid) === -1) displayNameToSensorIds[plain].push(sid);
}

// Sensor_CrossSens: first row may be title; second is header
const crossContent = fs.readFileSync(CROSS_CSV, 'utf8');
const crossRows = parseCSV(crossContent);
const headerC = crossRows[1] || crossRows[0] || [];
const col = (name) => headerC.findIndex((h) => h && h.toLowerCase().includes(name.toLowerCase()));
const idxCSensorId = col('sensor_id');
const idxChemical = col('chemical_id');
const idxRespType = col('response_type');
const idxTestConc = col('test_concentration');
const idxTestUnit = col('test_conc_unit');
const idxRespRd = col('response_reading');
const idxObsUnit = col('observed_rdg_unit');
const idxFilteredRd = col('filtered_resp_reading');
const idxFilteredUnit = col('filtered_rdg_unit');
const idxNotes = col('notes');

const bySensorId = {};
for (let r = 2; r < crossRows.length; r++) {
  const row = crossRows[r];
  const sid = row[idxCSensorId];
  const chemical = row[idxChemical];
  if (!sid || !chemical) continue;
  if (!bySensorId[sid]) bySensorId[sid] = [];
  bySensorId[sid].push({
    chemical_id: chemical,
    response_type: row[idxRespType] || '',
    test_concentration: row[idxTestConc] || '',
    test_conc_unit: row[idxTestUnit] || '',
    response_reading: row[idxRespRd] || '',
    observed_rdg_unit: row[idxObsUnit] || '',
    filtered_resp_reading: row[idxFilteredRd] || '',
    filtered_rdg_unit: row[idxFilteredUnit] || '',
    notes: row[idxNotes] || ''
  });
}

const out = { displayNameToSensorIds, bySensorId };
fs.writeFileSync(OUT, JSON.stringify(out, null, 2));
console.log('Wrote', OUT);
console.log('Sensors with cross-sens:', Object.keys(bySensorId).length);
console.log('Display names mapped:', Object.keys(displayNameToSensorIds).length);
console.log('Total cross-sens rows:', Object.values(bySensorId).reduce((s, arr) => s + arr.length, 0));
