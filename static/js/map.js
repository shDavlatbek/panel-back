// Wait for the DOM to be loaded
document.addEventListener('DOMContentLoaded', function() {
    // Variables to store map data
    let hexLayer = null;
    let loadingIndicator = null;
    let currentParameterName = 'temp'; // Default parameter to display
    
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
        
        div.innerHTML = '<h4>Parameter Legend</h4>';
        
        // Loop through our value intervals and generate a label with a colored square for each interval
        for (let i = 0; i < grades.length; i++) {
            const color = getValueColor(grades[i] + 1);
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
            fillColor: getValueColor(station.parameter_value || 0),
            color: '#000',
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8
        }).bindPopup(`
            <div class="station-tooltip">
                <div class="station-name">${station.name}</div>
                <div class="parameter-value">${currentParameterName}: ${station.parameter_value || 'N/A'} (${getValueDescription(station.parameter_value || 0)})</div>
                <div>Location: [${station.lat}, ${station.lon}]</div>
            </div>
        `);
    }
    
    // Helper function to get color based on parameter value
    function getValueColor(value) {
        if(value <= 50){
            return 'rgba(159, 211, 92, 1)'
          }else if(value > 50 && value <= 100){
            return 'rgba(247, 213, 67, 1)'
          }else if(value > 100 && value <= 150){
            return 'rgba(236, 142, 79, 1)'
          }else if(value > 150 && value < 200){
            return 'rgba(233, 95, 94, 1)'
          }else if(value >= 200 && value <= 300){
            return 'rgba(145, 104, 161, 1)'
          }else if(value > 300){
            return 'rgba(157, 104, 120, 1)'
          }
    }
    
    // Helper function to get description based on parameter value
    function getValueDescription(value) {
        if (value <= 50) {
            return 'Good';
        } else if (value <= 100) {
            return 'Moderate';
        } else if (value <= 150) {
            return 'Unhealthy for Sensitive Groups';
        } else if (value <= 200) {
            return 'Unhealthy';
        } else if (value <= 300) {
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
                'X-CSRFToken': getCookie('csrftoken'),
                'Authorization': 'Bearer ' + getCookie('token')
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to fetch hexgrid: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(geojson => {
            geojson = geojson.result;
            console.log('Received hexgrid:', geojson);
            if (!geojson || !geojson.features || geojson.features.length === 0) {
                console.warn('No hexagons returned from server');
                hideLoading();
                showErrorMessage('No hexagons could be generated. Please define an area in the admin interface.');
                return Promise.reject(new Error('No hexagons returned'));
            }
            
            // Now load the hexagon data using GET with the current parameter
            return fetch(`/api/hexdata?parameter_name=${currentParameterName}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Authorization': 'Bearer ' + getCookie('token')
                },
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to fetch hex data: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(hexData => {
                hexData = hexData.result;
                console.log('Received hex data:', hexData);
                if (!hexData || hexData.length === 0) {
                    console.warn('No hex data returned from server');
                    hideLoading();
                    showErrorMessage('No data could be interpolated. Check if there are stations with parameter data available.');
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
    
    // Fetch station data from the API
    fetch(`/api/stations`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
            'Authorization': 'Bearer ' + getCookie('token')
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to fetch stations: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(stations => {
            stations = stations.result.items;

            console.log('Fetched stations:', stations);
            // If no data, show a message
            if (stations.length === 0) {
                console.warn('No station data available');
                showErrorMessage('No station data available. Please add some stations first.');
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
                "Weather Stations": stationLayer
            };
            
            L.control.layers(baseLayers, overlays).addTo(map);
        })
        .catch(error => {
            console.error('Error fetching station data:', error);
            showErrorMessage('Error loading station data. Please try again later.');
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
                const hexData = hexDataMap[hexId];
                
                return {
                    fillColor: getValueColor(hexData?.value || 0),
                    weight: 0,  // Border weight
                    opacity: 0,
                    color: '#000',  // Border color
                    fillOpacity: 0.5  // Fill opacity
                };
            },
            onEachFeature: function(feature, layer) {
                const hexId = feature.properties.hex_id;
                const hexData = hexDataMap[hexId];
                
                if (hexData && hexData.value !== undefined) {
                    layer.bindTooltip(`${currentParameterName}: ${hexData.value.toFixed(2)}`, {
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
    
    // Create parameter selector control
    const parameterControl = L.control({position: 'topright'});
    
    parameterControl.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'info parameter-control');
        div.innerHTML = `
            <h4>Select Parameter</h4>
            <select id="parameter-select">
                <option value="temp">Temperature</option>
                <option value="wind-speed">Wind Speed</option>
                <option value="pressure">Pressure</option>
                <option value="humidity">Humidity</option>
                <option value="rainfall">Rainfall</option>
                <option value="ef-temp">Effective Temperature</option>
                <option value="wind-direction">Wind Direction</option>
            </select>
        `;
        return div;
    };
    
    parameterControl.addTo(map);
    
    // Add event listener to parameter selector
    setTimeout(() => {
        const parameterSelect = document.getElementById('parameter-select');
        if (parameterSelect) {
            parameterSelect.addEventListener('change', function() {
                currentParameterName = this.value;
                loadAreaData(); // Reload data with the new parameter
            });
        }
    }, 1000); // Small delay to ensure the DOM is ready
}); 