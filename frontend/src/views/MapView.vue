<template>
  <div class="map-container">
    <div class="map-card">
      <h1>AQI Map with IDW Interpolation</h1>
      
      <div v-if="mapStore.error" class="alert alert-danger">
        {{ mapStore.error }}
        <button class="close-btn" @click="mapStore.clearError">×</button>
      </div>
      
      <div id="map"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useMapStore } from '@/stores/map';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import * as d3 from 'd3';

// Workaround for marker icon issues with webpack
import { Icon } from 'leaflet';
delete Icon.Default.prototype._getIconUrl;
Icon.Default.mergeOptions({
  iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
  iconUrl: new URL('leaflet/dist/images/marker-icon.png', import.meta.url).href,
  shadowUrl: new URL('leaflet/dist/images/marker-shadow.png', import.meta.url).href,
});

const mapStore = useMapStore();
let map = null;
let hexLayer = null;
let stationLayer = null;
let loadingIndicator = null;

onMounted(async () => {
  // Initialize the map
  initMap();
  
  // Create loading indicator
  createLoadingIndicator();
  
  // Fetch data and render
  fetchDataAndRender();
});

onUnmounted(() => {
  if (map) {
    map.remove();
  }
});

// Initialize map
function initMap() {
  // Create the map centered at a default location (will adjust to data)
  map = L.map('map').setView([40.7128, -74.0060], 10); // Default to NYC coordinates
  
  // Add OpenStreetMap tile layer
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);
  
  // Add a legend to the map
  addLegend();
}

// Add legend to map
function addLegend() {
  const legend = L.control({position: 'bottomright'});
  
  legend.onAdd = function(map) {
    const div = L.DomUtil.create('div', 'info legend');
    const grades = [0, 50, 100, 150, 200, 300];
    const labels = ['Good', 'Moderate', 'Unhealthy for Sensitive Groups', 'Unhealthy', 'Very Unhealthy', 'Hazardous'];
    
    div.innerHTML = '<h4>AQI Legend</h4>';
    
    // Loop through our AQI intervals and generate a label with a colored square for each interval
    for (let i = 0; i < grades.length; i++) {
      const color = getAQIColor(grades[i] + 1);
      div.innerHTML +=
        '<div class="legend-item">' +
        '<div class="color-box" style="background:' + color + '"></div> ' +
        (grades[i + 1] ? grades[i] + '&ndash;' + grades[i + 1] + '<br>' : grades[i] + '+') + ' ' + labels[i] +
        '</div>';
    }
    
    return div;
  };
  
  legend.addTo(map);
}

// Function to create a loading indicator
function createLoadingIndicator() {
  loadingIndicator = L.control({position: 'topright'});
  
  loadingIndicator.onAdd = function(map) {
    const div = L.DomUtil.create('div', 'info loading-indicator');
    div.innerHTML = '<div class="spinner"></div> Loading data...';
    div.style.display = 'none';
    return div;
  };
  
  loadingIndicator.addTo(map);
}

// Function to show loading indicator
function showLoading() {
  if (loadingIndicator) {
    loadingIndicator.getContainer().style.display = 'block';
  }
}

// Function to hide loading indicator
function hideLoading() {
  if (loadingIndicator) {
    loadingIndicator.getContainer().style.display = 'none';
  }
}

// Fetch data and render map
async function fetchDataAndRender() {
  showLoading();
  
  try {
    // Fetch all map data
    await mapStore.fetchAllMapData();
    
    // Render stations
    renderStations();
    
    // Render hexagons
    renderHexagons();
    
    // Add controls
    addControls();
    
    // Adjust map view to station bounds if available
    if (mapStore.stations.length > 0) {
      const bounds = L.latLngBounds(mapStore.stations.map(s => [s.lat, s.lon]));
      map.fitBounds(bounds);
    }
  } catch (error) {
    console.error('Error fetching map data:', error);
    showErrorMessage('Error loading map data. Please try again later.');
  } finally {
    hideLoading();
  }
}

// Render station markers
function renderStations() {
  // Create a group for station markers
  stationLayer = L.layerGroup();
  
  // Add station markers to the map
  mapStore.stations.forEach(station => {
    createStationMarker(station).addTo(stationLayer);
  });
  
  stationLayer.addTo(map);
}

// Define station marker style
function createStationMarker(station) {
  // Leaflet expects [lat, lng] format for coordinates
  return L.circleMarker([station.lat, station.lon], {
    radius: 8,
    fillColor: getAQIColor(station.aqi_value || station.aqi),
    color: '#000',
    weight: 1,
    opacity: 1,
    fillOpacity: 0.8
  }).bindPopup(`
    <div class="station-tooltip">
      <div class="station-name">${station.name}</div>
      <div class="aqi-value">AQI: ${station.aqi_value || station.aqi} (${getAQIDescription(station.aqi_value || station.aqi)})</div>
      <div>Location: [${station.lat}, ${station.lon}]</div>
    </div>
  `);
}

// Function to render hexagons on the map
function renderHexagons() {
  // If we don't have both hex grid and hex data, return
  if (!mapStore.hexGrid || !mapStore.hexData || mapStore.hexData.length === 0) {
    showErrorMessage('No hex data available. Check if there are AQI stations available.');
    return;
  }
  
  // Create a lookup table for hex data
  const hexDataMap = {};
  mapStore.hexData.forEach(hex => {
    hexDataMap[hex.hex_id] = hex;
  });
  
  // If we already have a layer, remove it
  if (hexLayer) {
    map.removeLayer(hexLayer);
  }
  
  // Create the hexagon layer
  hexLayer = L.geoJSON(mapStore.hexGrid, {
    style: function(feature) {
      const hexId = feature.properties.hex_id;
      const hexData = hexDataMap[hexId] || { color: '#cccccc' };
      
      return {
        fillColor: getAQIColor(hexData.aqi) || '#cccccc',
        weight: 0,
        opacity: 0,
        color: '#000',
        fillOpacity: 0.5
      };
    },
    onEachFeature: function(feature, layer) {
      const hexId = feature.properties.hex_id;
      const hexData = hexDataMap[hexId];
      
      if (hexData) {
        layer.bindTooltip(hexData.aqi.toFixed(1), {
          direction: "top",
          offset: [0, 0]
        });
      } else {
        layer.bindTooltip("No data available for this hexagon");
      }
    },
    // Fix the coordinate order
    coordsToLatLng: function(coords) {
      // Convert from GeoJSON [lng, lat] to Leaflet [lat, lng]
      return new L.LatLng(coords[1], coords[0]);
    }
  }).addTo(map);
  
  // Ensure hexagons stay behind other layers
  hexLayer.bringToBack();
}

function addControls() {
  // Add controls
  const baseLayers = {
    "OpenStreetMap": L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')
  };
  
  const overlays = {
    "AQI Stations": stationLayer,
    "AQI Hexagons": hexLayer
  };
  
  L.control.layers(baseLayers, overlays).addTo(map);
}

// Function to show error messages on the map
function showErrorMessage(message) {
  // Remove any existing error message
  const existingError = document.querySelector('.error-message');
  if (existingError) {
    existingError.remove();
  }
  
  const errorControl = L.control({position: 'bottomleft'});
  errorControl.onAdd = function(map) {
    const div = L.DomUtil.create('div', 'info error-message');
    div.innerHTML = `<h4 style="color: red;">${message}</h4>`;
    return div;
  };
  errorControl.addTo(map);
}

// Helper function to get AQI color
function getAQIColor(aqi) {
  if (aqi <= 50) {
    return 'rgba(159, 211, 92, 1)';
  } else if (aqi > 50 && aqi <= 100) {
    return 'rgba(247, 213, 67, 1)';
  } else if (aqi > 100 && aqi <= 150) {
    return 'rgba(236, 142, 79, 1)';
  } else if (aqi > 150 && aqi < 200) {
    return 'rgba(233, 95, 94, 1)';
  } else if (aqi >= 200 && aqi <= 300) {
    return 'rgba(145, 104, 161, 1)';
  } else if (aqi > 300) {
    return 'rgba(157, 104, 120, 1)';
  }
}

// Helper function to get AQI description
function getAQIDescription(aqi) {
  if (aqi <= 50) {
    return 'Good';
  } else if (aqi <= 100) {
    return 'Moderate';
  } else if (aqi <= 150) {
    return 'Unhealthy for Sensitive Groups';
  } else if (aqi <= 200) {
    return 'Unhealthy';
  } else if (aqi <= 300) {
    return 'Very Unhealthy';
  } else {
    return 'Hazardous';
  }
}
</script>

<style scoped>
.map-container {
  width: 100%;
  padding: 20px;
}

.map-card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 20px;
}

h1 {
  text-align: center;
  margin-bottom: 20px;
  color: #333;
}

#map {
  height: 600px;
  width: 100%;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.alert {
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-danger {
  background-color: #ffe3e3;
  color: #e03131;
}

.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
}

/* Leaflet specific styles */
:global(.info) {
  padding: 6px 8px;
  font: 14px/16px Arial, Helvetica, sans-serif;
  background: white;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 0 15px rgba(0, 0, 0, 0.2);
  border-radius: 5px;
}

:global(.legend) {
  text-align: left;
  line-height: 18px;
  color: #555;
}

:global(.legend h4) {
  margin: 0 0 5px;
  color: #777;
}

:global(.legend-item) {
  margin-bottom: 5px;
}

:global(.color-box) {
  width: 18px;
  height: 18px;
  float: left;
  margin-right: 8px;
  opacity: 0.7;
}

:global(.loading-indicator) {
  display: flex;
  align-items: center;
}

:global(.spinner) {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 3px solid rgba(0, 0, 0, 0.3);
  border-radius: 50%;
  border-top-color: #4c6ef5;
  animation: spin 1s linear infinite;
  margin-right: 8px;
}

:global(.station-tooltip) {
  padding: 5px;
}

:global(.station-name) {
  font-weight: bold;
  margin-bottom: 5px;
}

:global(.aqi-value) {
  margin-bottom: 5px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style> 