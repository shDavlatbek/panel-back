// Wait for the DOM to be loaded
document.addEventListener('DOMContentLoaded', function() {
    // Variables to store map data
    let hexLayer = null;
    let loadingIndicator = null;
    
    // Create the map centered at a default location (will adjust to data)
    const map = L.map('map').setView([40.7128, -74.0060], 10); // Default to NYC coordinates
    
    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    // Add loading indicator to the map
    createLoadingIndicator();
    
    // Add a legend to the map
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
    
    // Helper function to get AQI color
    function getAQIColor(aqi) {
        if(aqi <= 50){
            return 'rgba(159, 211, 92, 1)'
          }else if(aqi > 50 && aqi <= 100){
            return 'rgba(247, 213, 67, 1)'
          }else if(aqi > 100 && aqi <= 150){
            return 'rgba(236, 142, 79, 1)'
          }else if(aqi > 150 && aqi < 200){
            return 'rgba(233, 95, 94, 1)'
          }else if(aqi >= 200 && aqi <= 300){
            return 'rgba(145, 104, 161, 1)'
          }else if(aqi > 300){
            return 'rgba(157, 104, 120, 1)'
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
    
    // Load data for the single area from the server
    function loadAreaData() {
        showLoading();
        
        // First, load the hexagon geometries using GET
        fetch('/api/hexgrid', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to fetch hexgrid: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(geojson => {
            console.log('Received hexgrid:', geojson);
            if (!geojson || !geojson.result.features || geojson.result.features.length === 0) {
                console.warn('No hexagons returned from server');
                hideLoading();
                showErrorMessage('No hexagons could be generated. Please define an area in the admin interface.');
                return Promise.reject(new Error('No hexagons returned'));
            }
            
            // Now load the hexagon data using GET
            return fetch('/api/hexdata', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to fetch hex data: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(hexData => {
                console.log('Received hex data:', hexData);
                if (!hexData || hexData.length === 0) {
                    console.warn('No hex data returned from server');
                    hideLoading();
                    showErrorMessage('No data could be interpolated. Check if there are AQI stations available.');
                    return;
                }
                
                renderHexagons(geojson, hexData);
                hideLoading();
            });
        })
        .catch(error => {
            console.error('Error loading hexagon data:', error);
            hideLoading();
            showErrorMessage('Error loading hexagon data: ' + error.message);
        });
    }
    
    // Fetch AQI station data from the API
    fetch('/api/stations')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to fetch stations: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(stations => {
            stations = stations.result.stations;

            console.log('Fetched stations:', stations);
            // If no data, show a message
            if (stations.length === 0) {
                console.warn('No station data available');
                showErrorMessage('No AQI station data available. Please add some stations first.');
                return;
            }
            
            // Find bounds of the data and fit map to these bounds
            if (stations.length > 0) {
                const bounds = L.latLngBounds(stations.map(s => [s.lat, s.lon]));
                map.fitBounds(bounds);
            }
            
            // Create a group for station markers
            const stationLayer = L.layerGroup();
            
            // Add station markers to the map
            stations.forEach(station => {
                createStationMarker(station).addTo(stationLayer);
            });
            
            stationLayer.addTo(map);
            
            // Load hexagon data for the single area
            loadAreaData();
            
            // Add controls
            const baseLayers = {
                "OpenStreetMap": L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')
            };
            
            const overlays = {
                "AQI Stations": stationLayer
            };
            
            L.control.layers(baseLayers, overlays).addTo(map);
        })
        .catch(error => {
            console.error('Error fetching AQI data:', error);
            showErrorMessage('Error loading AQI data. Please try again later.');
        });
    
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
    
    // Function to render hexagons on the map
    function renderHexagons(geojson, hexData) {
        // Create a lookup table for hex data
        const hexDataMap = {};
        hexData.forEach(hex => {
            hexDataMap[hex.hex_id] = hex;
        });
        
        // If we already have a layer, remove it
        if (hexLayer) {
            map.removeLayer(hexLayer);
        }
        
        // Create the hexagon layer
        hexLayer = L.geoJSON(geojson, {
            style: function(feature) {
                const hexId = feature.properties.hex_id;
                const hexData = hexDataMap[hexId] || { color: '#cccccc' };
                
                return {
                    fillColor: getAQIColor(hexData.aqi) || '#cccccc',
                    weight: 0,  // Increased for better visibility
                    opacity: 0,
                    color: '#000',  // Border color
                    fillOpacity: 0.5  // Increased for better visibility
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
    
    // Get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}); 