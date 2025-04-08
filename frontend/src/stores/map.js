import { defineStore } from 'pinia';
import MapService from '@/services/map.service';

export const useMapStore = defineStore('map', {
  state: () => ({
    stations: [],
    hexGrid: null,
    hexData: [],
    loading: false,
    error: null
  }),
  
  actions: {
    async fetchStations() {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await MapService.getStations();
        if (response.success) {
          this.stations = response.result.stations;
        } else {
          this.error = response.detail || 'Failed to fetch stations';
        }
        return response;
      } catch (error) {
        this.error = error.message || 'Failed to fetch stations';
        return { success: false, detail: this.error };
      } finally {
        this.loading = false;
      }
    },
    
    async fetchHexGrid() {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await MapService.getHexGrid();
        if (response.success) {
          this.hexGrid = response.result;
        } else {
          this.error = response.detail || 'Failed to fetch hex grid';
        }
        return response;
      } catch (error) {
        this.error = error.message || 'Failed to fetch hex grid';
        return { success: false, detail: this.error };
      } finally {
        this.loading = false;
      }
    },
    
    async fetchHexData() {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await MapService.getHexData();
        if (response.success) {
          this.hexData = response.result;
        } else {
          this.error = response.detail || 'Failed to fetch hex data';
        }
        return response;
      } catch (error) {
        this.error = error.message || 'Failed to fetch hex data';
        return { success: false, detail: this.error };
      } finally {
        this.loading = false;
      }
    },
    
    async fetchAllMapData() {
      await this.fetchStations();
      await this.fetchHexGrid();
      await this.fetchHexData();
    },
    
    clearError() {
      this.error = null;
    }
  }
}); 