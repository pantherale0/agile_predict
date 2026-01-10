import axios from 'axios';

// Get API URL from runtime configuration or use dynamic fallback
// window.CONFIG is loaded from public/config.js at runtime
const API_BASE = (() => {
  // First, try to use the runtime config (set via environment variable in Docker)
  if (window.CONFIG && window.CONFIG.API_URL) {
    console.log('Using API URL from config:', window.CONFIG.API_URL);
    return window.CONFIG.API_URL;
  }
  
  // Fallback: use current host (works for same-origin deployments)
  const protocol = window.location.protocol;
  const host = window.location.host;
  const url = `${protocol}//${host}/api`;
  console.log('Using API URL from current host:', url);
  return url;
})();

export const fetchRegionalForecast = (region, days = 14) => {
  return axios.get(`${API_BASE}/forecasts/${region}`, {
    params: {
      days,
      forecast_count: 1,
      high_low: 'true'
    }
  });
};

export const fetchLatestForecast = () => {
  return axios.get(`${API_BASE}/forecasts/latest`);
};

export const fetchGenerationDemand = (region, days = 14) => {
  return axios.get(`${API_BASE}/prices/${region}/generation`, {
    params: {
      days,
      forecast_count: 1
    }
  });
};

export const fetchActualPrices = (days = 14) => {
  return axios.get(`${API_BASE}/prices/history/actual/`, {
    params: { days }
  });
};

export const fetchStats = () => {
  return axios.get(`${API_BASE}/prices/stats/`);
};

export const fetchPriceHeatmap = () => {
  return axios.get(`${API_BASE}/prices/history/heatmap/`);
};

export const fetchDailyBreakdown = (dateStr) => {
  return axios.get(`${API_BASE}/prices/history/daily/${dateStr}`);
};
