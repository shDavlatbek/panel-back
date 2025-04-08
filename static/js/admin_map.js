/**
 * JavaScript for GeographicArea admin polygon map
 * This file is loaded after the widget's inline script
 */
(function() {
    document.addEventListener('DOMContentLoaded', function() {
        // Make sure the map renders properly
        // Django admin uses tabs, and the map might be hidden initially
        
        // If the map is inside a tab, make sure it redraws when the tab is activated
        const tabLinks = document.querySelectorAll('.nav-tabs a');
        if (tabLinks.length > 0) {
            tabLinks.forEach(function(link) {
                link.addEventListener('click', function() {
                    // Get all map containers (in case there are multiple)
                    const mapContainers = document.querySelectorAll('.admin-map-widget');
                    setTimeout(function() {
                        mapContainers.forEach(function(container) {
                            if (typeof container._leaflet_id !== 'undefined') {
                                const map = container._leaflet_map;
                                if (map) {
                                    map.invalidateSize();
                                }
                            }
                        });
                    }, 100);
                });
            });
        }
        
        // Ensure map is properly sized on load
        window.addEventListener('resize', function() {
            const mapContainers = document.querySelectorAll('.admin-map-widget');
            mapContainers.forEach(function(container) {
                if (typeof container._leaflet_id !== 'undefined') {
                    const map = container._leaflet_map;
                    if (map) {
                        map.invalidateSize();
                    }
                }
            });
        });
        
        // The coordinates textarea is hidden, so add a link to toggle its visibility
        const coordsFields = document.querySelectorAll('[name$="coordinates"]');
        coordsFields.forEach(function(field) {
            // Create toggle link
            const toggleLink = document.createElement('a');
            toggleLink.href = '#';
            toggleLink.textContent = 'Show/hide JSON coordinates';
            toggleLink.style.display = 'block';
            toggleLink.style.marginBottom = '10px';
            toggleLink.className = 'toggle-coords-link';
            
            // Find the container for this field
            const container = field.closest('.field-coordinates') || field.parentNode;
            
            // Insert the toggle link at the top of the container
            container.insertBefore(toggleLink, container.firstChild);
            
            // Add click event
            toggleLink.addEventListener('click', function(e) {
                e.preventDefault();
                // Toggle the visibility of the field
                if (field.style.display === 'none') {
                    field.style.display = 'block';
                    toggleLink.textContent = 'Hide JSON coordinates';
                } else {
                    field.style.display = 'none';
                    toggleLink.textContent = 'Show JSON coordinates';
                }
            });
        });
        
        // Make sure all Leaflet maps are properly sized
        setTimeout(function() {
            document.querySelectorAll('.admin-map-widget').forEach(function(container) {
                if (typeof container._leaflet_id !== 'undefined') {
                    const map = container._leaflet_map;
                    if (map) {
                        map.invalidateSize();
                    }
                }
            });
        }, 500);
    });
})(); 