import axios from 'axios';

// Get API URL dynamically - checked at request time to ensure config.js is loaded
const getAPIBase = () => {
  // First, try to use the runtime config (set via environment variable in Docker)
  if (window.CONFIG && window.CONFIG.API_URL) {
    return window.CONFIG.API_URL;
  }
  
  // Fallback: use current host (works for same-origin deployments)
  const protocol = window.location.protocol;
  const host = window.location.host;
  return `${protocol}//${host}/api`;
};

// Add interceptor to log requests for debugging
axios.interceptors.request.use(
  config => {
    console.log('API Request to:', config.url);
    return config;
  },
  error => Promise.reject(error)
);

export const fetchRegionalForecast = (region, days = 14) => {
  return axios.get(`${getAPIBase()}/forecasts/${region}`, {
    params: {
      days,
      forecast_count: 1,
      high_low: 'true'
    }
  });
};

export const fetchLatestForecast = () => {
  return axios.get(`${getAPIBase()}/forecasts/latest`);
};

export const fetchGenerationDemand = (region, days = 14) => {
  return axios.get(`${getAPIBase()}/prices/${region}/generation`, {
    params: {
      days,
      forecast_count: 1
    }
  });
};

export const fetchActualPrices = (days = 14) => {
  return axios.get(`${getAPIBase()}/prices/history/actual/`, {
    params: { days }
  });
};

export const fetchStats = () => {
  return axios.get(`${getAPIBase()}/prices/stats/`);
};

export const fetchPriceHeatmap = () => {
  return axios.get(`${getAPIBase()}/prices/history/heatmap/`);
};

export const fetchDailyBreakdown = (dateStr) => {
  return axios.get(`${getAPIBase()}/prices/history/daily/${dateStr}`);
};
