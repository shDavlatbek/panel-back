/**
 * Inverse Distance Weighting (IDW) interpolation implementation
 */
class IDWInterpolator {
    /**
     * Constructor for the IDW interpolator
     * @param {Array} points - Array of data points with lat, lng and value properties
     * @param {Number} power - Power parameter for IDW (default: 2)
     * @param {Number} smoothing - Smoothing factor (default: 0.5)
     * @param {Number} radius - Search radius for points (default: 1000 meters)
     */
    constructor(points, power = 2, smoothing = 0.5, radius = 100000) {
        this.points = points;
        this.power = power;
        this.smoothing = smoothing;
        this.radius = radius;
    }

    /**
     * Calculate the interpolated value at the given point
     * @param {Number} lat - Latitude of the point to interpolate
     * @param {Number} lng - Longitude of the point to interpolate
     * @returns {Number} Interpolated value
     */
    interpolate(lat, lng) {
        // Convert to meters first
        let totalWeight = 0;
        let weightedSum = 0;
        
        // Compute IDW
        for (const point of this.points) {
            // Calculate distance (in meters) using Haversine formula
            const distance = this.haversineDistance(lat, lng, point.lat, point.lng);
            
            // If the target point is the same as a known point, return its value
            if (distance < 1e-10) {
                return point.aqi;
            }
            
            // Skip points beyond the search radius
            if (distance > this.radius) {
                continue;
            }
            
            // Apply IDW formula with smoothing factor
            const weight = 1.0 / Math.pow(distance + this.smoothing, this.power);
            totalWeight += weight;
            weightedSum += weight * point.aqi;
        }
        
        // Return the weighted average or 0 if no points in range
        return totalWeight === 0 ? 0 : weightedSum / totalWeight;
    }
    
    /**
     * Calculate the haversine distance between two points
     * @param {Number} lat1 - Latitude of the first point
     * @param {Number} lng1 - Longitude of the first point
     * @param {Number} lat2 - Latitude of the second point
     * @param {Number} lng2 - Longitude of the second point
     * @returns {Number} Distance in meters
     */
    haversineDistance(lat1, lng1, lat2, lng2) {
        const R = 6371000; // Earth radius in meters
        const dLat = this.toRad(lat2 - lat1);
        const dLng = this.toRad(lng2 - lng1);
        
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(this.toRad(lat1)) * Math.cos(this.toRad(lat2)) *
                  Math.sin(dLng/2) * Math.sin(dLng/2);
        
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }
    
    /**
     * Convert degrees to radians
     * @param {Number} value - Value in degrees
     * @returns {Number} Value in radians
     */
    toRad(value) {
        return value * Math.PI / 180;
    }
    
    /**
     * Get the AQI color based on the AQI value
     * @param {Number} aqi - AQI value
     * @returns {String} Color in hex format
     */
    static getAQIColor(aqi) {
        if (aqi <= 50) {
            return '#00e400'; // Good
        } else if (aqi <= 100) {
            return '#ffff00'; // Moderate
        } else if (aqi <= 150) {
            return '#ff7e00'; // Unhealthy for Sensitive Groups
        } else if (aqi <= 200) {
            return '#ff0000'; // Unhealthy
        } else if (aqi <= 300) {
            return '#99004c'; // Very Unhealthy
        } else {
            return '#7e0023'; // Hazardous
        }
    }
    
    /**
     * Get the AQI description based on the AQI value
     * @param {Number} aqi - AQI value
     * @returns {String} AQI description
     */
    static getAQIDescription(aqi) {
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
} 