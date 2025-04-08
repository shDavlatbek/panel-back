import axios from 'axios';

const API_URL = 'http://localhost:8300/api/';

class MapService {
  /**
   * Get AQI station data
   * @returns {Promise} - Response promise
   */
  getStations() {
    return axios.get(API_URL + 'stations')
      .then(response => response.data);
  }

  /**
   * Get hexgrid geometry
   * @returns {Promise} - Response promise
   */
  getHexGrid() {
    return axios.get(API_URL + 'hexgrid')
      .then(response => response.data);
  }

  /**
   * Get hexagon data with AQI values
   * @returns {Promise} - Response promise
   */
  getHexData() {
    return axios.get(API_URL + 'hexdata')
      .then(response => response.data);
  }
}

export default new MapService(); 