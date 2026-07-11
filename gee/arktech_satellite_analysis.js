// ============================================================
// ARKTECH - Satellite Feature Extraction
// Paste this entire file into code.earthengine.google.com
// Study region: Mandya district agricultural area, Karnataka
// Primary crop: Rice / paddy
// ============================================================

// 1. STUDY REGION
// Draw your own rectangle in the map, OR use this approximate
// Mandya-area bounding box:
var region = ee.Geometry.Rectangle([76.80, 12.40, 77.05, 12.65]);
Map.centerObject(region, 11);
Map.addLayer(region, {color: 'red'}, 'Study Region');

// 2. DATE RANGE - one crop season
var startDate = '2026-06-01';
var endDate   = '2026-08-31';

// 3. SENTINEL-2 (optical) - cloud-masked
function maskS2clouds(image) {
  var qa = image.select('QA60');
  var cloudBitMask = 1 << 10;
  var cirrusBitMask = 1 << 11;
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
      .and(qa.bitwiseAnd(cirrusBitMask).eq(0));
  return image.updateMask(mask).divide(10000);
}

var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(region)
  .filterDate(startDate, endDate)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
  .map(maskS2clouds)
  .median();

var ndvi = s2.normalizedDifference(['B8', 'B4']).rename('ndvi');
var ndwi = s2.normalizedDifference(['B3', 'B8']).rename('ndwi');

// 4. SENTINEL-1 (radar) - works through clouds
var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(region)
  .filterDate(startDate, endDate)
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
  .select(['VV', 'VH'])
  .median();

var vv = s1.select('VV').rename('vv');
var vh = s1.select('VH').rename('vh');
var vvVhRatio = vv.divide(vh).rename('vv_vh_ratio');

// 5. RAINFALL (CHIRPS)
var rainfall = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
  .filterBounds(region)
  .filterDate(startDate, endDate)
  .sum()
  .rename('rainfall');

// 6. LAND SURFACE TEMPERATURE (MODIS)
var lst = ee.ImageCollection('MODIS/061/MOD11A2')
  .filterBounds(region)
  .filterDate(startDate, endDate)
  .select('LST_Day_1km')
  .mean()
  .multiply(0.02).subtract(273.15) // Kelvin -> Celsius
  .rename('lst');

// 7. SOIL MOISTURE PROXY (NDWI-based, simple starting proxy)
var soilMoistureIndex = ndwi.add(1).divide(2).rename('soil_moisture_index');

// 8. COMBINE ALL FEATURES INTO ONE IMAGE
var combined = ndvi
  .addBands(ndwi)
  .addBands(vv)
  .addBands(vh)
  .addBands(vvVhRatio)
  .addBands(soilMoistureIndex)
  .addBands(rainfall)
  .addBands(lst);

Map.addLayer(ndvi, {min: 0, max: 1, palette: ['red', 'yellow', 'green']}, 'NDVI');

// 9. CREATE FIELD SAMPLE POINTS
// Replace this with your real field GPS points if you have them.
// This generates 30 random sample points inside the region as a starting point.
var samplePoints = ee.FeatureCollection.randomPoints(region, 30, 42);

// 10. EXTRACT VALUES AT EACH POINT
var sampled = combined.sampleRegions({
  collection: samplePoints,
  scale: 10,
  geometries: true
});

// Add lat/lon and a placeholder field_id + date + crop_stage
// (crop_stage and date should be set per-export if you sample multiple dates)
var withMeta = sampled.map(function(feature) {
  var coords = feature.geometry().coordinates();
  return feature.set({
    'longitude': coords.get(0),
    'latitude': coords.get(1),
    'date': startDate,
    'crop_stage': 'vegetative' // change this per export if sampling multiple stages
  });
});

// 11. EXPORT TO CSV (Google Drive)
Export.table.toDrive({
  collection: withMeta,
  description: 'arktech_gee_data',
  folder: 'ARKTECH',
  fileNamePrefix: 'arktech_gee_data',
  fileFormat: 'CSV'
});

// ============================================================
// After running: click "Run", then check the "Tasks" tab (top
// right), and click "Run" next to the export task. The CSV will
// appear in your Google Drive, in a folder called "ARKTECH".
//
// To build a real training set, repeat this for multiple date
// ranges (sowing / vegetative / flowering) and multiple regions
// if needed, then combine the CSVs together in
// data/raw/arktech_gee_data.csv
// ============================================================
