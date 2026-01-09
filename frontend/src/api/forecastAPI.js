import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export const fetchRegionalForecast = (region, days = 14) => {
  return axios.get(`${API_BASE}/${region}/`, {
    params: {
      days,
      forecast_count: 1,
      high_low: 'true'
    }
  });
};

export const fetchLatestForecast = () => {
  return axios.get(`${API_BASE}/`);
};

export const fetchGenerationDemand = (region, days = 14) => {
  return axios.get(`${API_BASE}/${region}/generation/`, {
    params: {
      days,
      forecast_count: 1
    }
  });
};

export const fetchActualPrices = (days = 14) => {
  return axios.get(`${API_BASE}/history/actual/`, {
    params: { days }
  });
};

export const fetchStats = () => {
  return axios.get(`${API_BASE}/stats/`);
};

export const fetchPriceHeatmap = () => {
  return axios.get(`${API_BASE}/history/heatmap/`);
};

export const fetchDailyBreakdown = (dateStr) => {
  return axios.get(`${API_BASE}/history/daily/${dateStr}/`);
};
