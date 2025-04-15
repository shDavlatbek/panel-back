// Wait for the DOM to be loaded
document.addEventListener('DOMContentLoaded', function() {
    // Variables to store map data
    let hexLayer = null;
    let loadingIndicator = null;
    let currentParameterName = 'temp'; // Default parameter to display
    let currentDateTime = null; // Default to latest data (null = latest)
    let datetimePicker = null; // Will store flatpickr instance
    let stationData = []; // Store station data
    
    // Create the map centered at a default location (will adjust to data)
    const map = L.map('map').setView([40.7128, -74.0060], 10); // Default to NYC coordinates
    
    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    // Initialize datetime picker
    initDatetimePicker();
    
    // Initialize table toggle
    initTableToggle();
    
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
    
    // Function to initialize table toggle
    function initTableToggle() {
        const toggleButton = document.getElementById('toggle-table');
        const tableContainer = document.getElementById('station-table-container');
        
        if (toggleButton && tableContainer) {
            toggleButton.addEventListener('click', function() {
                if (tableContainer.classList.contains('hidden')) {
                    tableContainer.classList.remove('hidden');
                    toggleButton.textContent = 'Hide Station Data Table';
                    // If datetime is selected, load the table data
                    if (currentDateTime) {
                        loadStationParametersTable();
                    }
                } else {
                    tableContainer.classList.add('hidden');
                    toggleButton.textContent = 'Show Station Data Table';
                }
            });
        }
    }
    
    // Function to initialize the datetime picker
    function initDatetimePicker() {
        const datetimeInput = document.getElementById('datetime-picker');
        const resetTimeButton = document.getElementById('reset-time');
        
        if (datetimeInput) {
            // Initialize flatpickr with time
            datetimePicker = flatpickr(datetimeInput, {
                enableTime: true,
                dateFormat: "Y-m-d H:i:S",
                time_24hr: true,
                defaultDate: new Date(),
                minuteIncrement: 60, // Increment by hour since our data is hourly
                onChange: function(selectedDates, dateStr) {
                    if (selectedDates && selectedDates.length > 0) {
                        currentDateTime = dateStr;
                        updateMapInfo();
                        loadAreaData();
                        // Load station parameters for table when datetime is selected
                        loadStationParametersTable();
                    }
                }
            });
            
            // Don't automatically load data on init - wait for user action
            datetimePicker.clear();
        }
        
        // Add event listener to reset button
        if (resetTimeButton) {
            resetTimeButton.addEventListener('click', function() {
                if (datetimePicker) {
                    datetimePicker.clear();
                }
                currentDateTime = null;
                updateMapInfo();
                loadAreaData();
                // Reset table when returning to latest data
                resetStationParametersTable();
            });
        }
    }
    
    // Function to load station parameters for table display
    function loadStationParametersTable() {
        if (!currentDateTime) {
            resetStationParametersTable();
            return;
        }
        
        const loadingMessage = document.getElementById('loading-message');
        const tableWrapper = document.getElementById('table-wrapper');
        
        if (loadingMessage && tableWrapper) {
            loadingMessage.textContent = 'Loading station data...';
            loadingMessage.style.display = 'block';
            tableWrapper.classList.add('hidden');
        }
        
        // Create date range for API request (same start and end date)
        const utcPlus5DateTime = currentDateTime; // Already in UTC+5 format
        
        // Fetch parameters for all stations at selected time
        fetch(`/api/parameters?start_date=${encodeURIComponent(utcPlus5DateTime)}&end_date=${encodeURIComponent(utcPlus5DateTime)}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
                'Authorization': 'Bearer ' + getCookie('token')
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to fetch station parameters: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Station parameters response:', data);
            if (data.success && data.result && data.result.items) {
                const parameters = data.result.items;
                const stations = data.result.stations || [];
                
                // Build station lookup for easy reference
                const stationLookup = {};
                stations.forEach(station => {
                    stationLookup[station.number] = station.name;
                });
                
                // Display data in the table
                displayStationParameters(parameters, stationLookup);
            } else {
                throw new Error('No parameter data available');
            }
        })
        .catch(error => {
            console.error('Error loading station parameters:', error);
            if (loadingMessage) {
                loadingMessage.textContent = `Error loading station data: ${error.message}`;
            }
        });
    }
    
    // Function to display station parameters in the table
    function displayStationParameters(parameters, stationLookup) {
        const tableBody = document.getElementById('station-parameters-body');
        const loadingMessage = document.getElementById('loading-message');
        const tableWrapper = document.getElementById('table-wrapper');
        
        if (!tableBody || !loadingMessage || !tableWrapper) return;
        
        // Clear existing table rows
        tableBody.innerHTML = '';
        
        if (parameters.length === 0) {
            loadingMessage.textContent = 'No station data available for the selected time.';
            loadingMessage.style.display = 'block';
            tableWrapper.classList.add('hidden');
            return;
        }
        
        // Group parameters by station
        const stationParameters = {};
        
        parameters.forEach(param => {
            const stationNumber = param.station_number;
            if (!stationParameters[stationNumber]) {
                stationParameters[stationNumber] = {
                    name: stationLookup[stationNumber] || stationNumber,
                    parameters: {}
                };
            }
            
            // Add all parameter values
            Object.keys(param).forEach(key => {
                // Skip non-parameter keys
                if (['station_number', 'datetime'].includes(key)) return;
                
                stationParameters[stationNumber].parameters[key] = param[key];
            });
        });
        
        // Create table rows
        Object.keys(stationParameters).forEach(stationNumber => {
            const station = stationParameters[stationNumber];
            const row = document.createElement('tr');
            
            // Station name column
            const nameCell = document.createElement('td');
            nameCell.textContent = station.name;
            row.appendChild(nameCell);
            
            // Parameter columns - add in fixed order to match headers
            const parameterOrder = ['temp', 'humidity', 'pressure', 'wind_speed', 'wind_direction', 'rainfall', 'ef_temp', 'dust_storm'];
            
            parameterOrder.forEach(paramKey => {
                const cell = document.createElement('td');
                const value = station.parameters[paramKey];
                
                // Format value or show N/A
                if (value !== null && value !== undefined) {
                    if (paramKey === 'wind_direction') {
                        cell.textContent = `${value}° (${degreesToCardinal(value)})`;
                    } else if (paramKey === 'rainfall' && value === -1) {
                        cell.textContent = 'None';
                    } else if (paramKey === 'dust_storm' && (value === 0 || value === 1)) {
                        cell.textContent = value === 1 ? 'Yes' : 'No';
                    } else {
                        cell.textContent = Number(value).toFixed(1);
                    }
                } else {
                    cell.textContent = 'N/A';
                }
                
                row.appendChild(cell);
            });
            
            tableBody.appendChild(row);
        });
        
        // Show the table
        loadingMessage.style.display = 'none';
        tableWrapper.classList.remove('hidden');
    }
    
    // Helper function to convert wind direction degrees to cardinal direction
    function degreesToCardinal(degrees) {
        if (degrees === null || degrees === undefined) return 'N/A';
        
        const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
        const index = Math.round(degrees / 22.5) % 16;
        return directions[index];
    }
    
    // Function to reset the station parameters table
    function resetStationParametersTable() {
        const loadingMessage = document.getElementById('loading-message');
        const tableWrapper = document.getElementById('table-wrapper');
        
        if (loadingMessage && tableWrapper) {
            loadingMessage.textContent = 'Please select a date and time to view station data.';
            loadingMessage.style.display = 'block';
            tableWrapper.classList.add('hidden');
        }
    }
    
    // Update the map info text
    function updateMapInfo() {
        const mapInfo = document.getElementById('map-info');
        if (mapInfo) {
            if (currentDateTime) {
                mapInfo.textContent = `Showing ${currentParameterName} data for ${currentDateTime} (UTC+5)`;
            } else {
                mapInfo.textContent = `Showing latest ${currentParameterName} data for all stations`;
            }
        }
    }
    
    // Define station marker style
    function createStationMarker(station) {
        // Leaflet expects [lat, lng] format for coordinates
        let popupContent = `
            <div class="station-tooltip">
                <div class="station-name">${station.station_name || station.name}</div>
                <div class="parameter-value">${currentParameterName}: ${station.parameter_value || 'N/A'} (${getValueDescription(station.parameter_value || 0)})</div>
                <div>Location: [${station.lat}, ${station.lng || station.lon}]</div>
        `;
        
        // Add datetime if available
        if (station.parameter_datetime) {
            popupContent += `<div>Time: ${formatDateTime(station.parameter_datetime)}</div>`;
        }
        
        popupContent += `</div>`;
        
        return L.circleMarker([station.lat, station.lng || station.lon], {
            radius: 8,
            fillColor: getValueColor(station.parameter_value || 0),
            color: '#000',
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8
        }).bindPopup(popupContent);
    }
    
    // Format datetime for display
    function formatDateTime(datetime) {
        if (typeof datetime === 'string') {
            return datetime;
        }
        const dt = new Date(datetime);
        return dt.toLocaleString();
    }
    
    // Helper function to get color based on parameter value
    function getValueColor(value) {
        // Determine how many steps of 2 the current value represents.
        const steps = Math.floor(value / 2);
        // Change hue by 10 degrees for each step, and wrap around at 360 degrees.
        const hue = (steps * 10) % 360;
        // Return a color using the HSL format. Here, saturation and lightness are fixed.
        return `hsl(${hue}, 70%, 50%)`;
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
        
        // Build the hexdata URL with query parameters
        let hexDataUrl = `/api/hexdata?parameter_name=${currentParameterName}`;
        if (currentDateTime) {
            hexDataUrl += `&datetime=${encodeURIComponent(currentDateTime)}`;
        }
        
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
            return fetch(hexDataUrl, {
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
            .then(data => {
                data = data.result;
                console.log('Received hex data:', data);
                
                // Extract hexagons from response
                const hexData = data.hexagons || data;
                
                if (!hexData || hexData.length === 0) {
                    console.warn('No hex data returned from server');
                    hideLoading();
                    showErrorMessage('No data could be interpolated. Check if there are stations with parameter data available.');
                    return;
                }
                
                // Update station markers if stations are included in response
                if (data.metadata && data.metadata.stations_count) {
                    updateMapInfo();
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
            stationData = stations; // Store station data for reference

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
    // const parameterControl = L.control({position: 'topright'});
    
    // parameterControl.onAdd = function(map) {
    //     const div = L.DomUtil.create('div', 'info parameter-control');
    //     div.innerHTML = `
    //         <h4>Select Parameter</h4>
    //         <select id="parameter-select">
    //             <option value="temp">Temperature</option>
    //             <option value="wind-speed">Wind Speed</option>
    //             <option value="pressure">Pressure</option>
    //             <option value="humidity">Humidity</option>
    //             <option value="rainfall">Rainfall</option>
    //             <option value="ef-temp">Effective Temperature</option>
    //             <option value="wind-direction">Wind Direction</option>
    //         </select>
    //     `;
    //     return div;
    // };
    
    // parameterControl.addTo(map);
    
    // Add event listener to parameter selector
    setTimeout(() => {
        const parameterSelect = document.getElementById('parameter-select');
        if (parameterSelect) {
            parameterSelect.addEventListener('change', function() {
                currentParameterName = this.value;
                updateMapInfo();
                loadAreaData(); // Reload data with the new parameter
            });
        }
    }, 1000); // Small delay to ensure the DOM is ready
}); 