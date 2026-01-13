import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { fetchRegionalForecast, fetchGenerationDemand, fetchActualPrices, fetchPriceHeatmap, fetchDailyBreakdown, fetchAvailableForecasts } from '../api/forecastAPI';
import ForecastChart from '../components/ForecastChart';
import ForecastSettings from '../components/ForecastSettings';
import Plot from 'react-plotly.js';
import './ForecastPage.css';

const REGIONS = {
  'X': 'National Average',
  'A': 'Eastern England',
  'B': 'East Midlands',
  'C': 'London',
  'D': 'Merseyside and Northern Wales',
  'E': 'West Midlands',
  'F': 'North Eastern England',
  'G': 'North Western England',
  'H': 'Southern England',
  'J': 'South Eastern England',
  'K': 'Southern Wales',
  'L': 'South Western England',
  'M': 'Yorkshire',
  'N': 'Southern Scotland',
  'P': 'Northern Scotland'
};

function ForecastPage() {
  const { region = 'X' } = useParams();
  const [forecast, setForecast] = useState(null);
  const [allForecasts, setAllForecasts] = useState([]);
  const [selectedForecasts, setSelectedForecasts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(7);
  const [showGenerationDemand, setShowGenerationDemand] = useState(true);
  const [showRangeOnForecast, setShowRangeOnForecast] = useState(true);
  const [showForecastOverlap, setShowForecastOverlap] = useState(false);
  const [heatmapData, setHeatmapData] = useState(null);
  const [heatmapLoading, setHeatmapLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(null);
  const [dailyBreakdown, setDailyBreakdown] = useState(null);
  const [dailyLoading, setDailyLoading] = useState(false);
  const [windowWidth, setWindowWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1024);
  const regionName = REGIONS[region.toUpperCase()] || 'Unknown Region';

  // Handle window resize for responsive layout
  useEffect(() => {
    const handleResize = () => {
      setWindowWidth(window.innerWidth);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Save the visited region to localStorage
  useEffect(() => {
    localStorage.setItem('lastVisitedRegion', region.toUpperCase());
  }, [region]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    
    Promise.all([
      fetchAvailableForecasts(10),
      fetchRegionalForecast(region.toUpperCase(), days),
      fetchGenerationDemand(region.toUpperCase(), days),
      fetchActualPrices(days)
    ])
      .then(([forecastRes, priceRes, genRes, actualRes]) => {
        // Extract and map price data from FastAPI response
        let priceData = [];
        const priceResults = Array.isArray(priceRes.data) ? priceRes.data : [];
        
        // Extract all forecast timestamps for the selector
        const forecasts = forecastRes.data.map(forecast => ({
          timestamp: forecast.forecast_date || forecast.created_at || new Date().toISOString(),
          id: forecast.id || forecast.forecast_date,
          name: forecast.name
        }));
        setAllForecasts(forecasts);
        // Select the first forecast by default
        if (forecasts.length > 0) {
          setSelectedForecasts([forecasts[0].id]);
        }
        
        if (priceResults.length > 0) {
          // The response is an array of forecast objects with agile_data nested inside
          const firstForecast = priceResults[0];
          if (firstForecast.agile_data) {
            priceData = firstForecast.agile_data.map(p => ({
              ...p,
              timestamp: p.date_time
            }));
          }
        }

        // Extract and merge generation/demand data
        let genData = {};
        // Generation endpoint returns a flat array of objects
        const genResults = Array.isArray(genRes.data) ? genRes.data : (genRes.data?.results || []);
        genResults.forEach(item => {
          genData[item.date_time] = {
            demand: item.demand,
            bm_wind: item.bm_wind,
            emb_wind: item.emb_wind,
            solar: item.solar,
            rad: item.rad
          };
        });

        // Extract actual prices
        let actualPrices = {};
        const actualResults = Array.isArray(actualRes.data) ? actualRes.data : (actualRes.data?.results || []);
        actualResults.forEach(item => {
          actualPrices[item.date_time] = item.agile;
        });

        // Merge all data into price data
        const mergedData = priceData.map(p => ({
          ...p,
          ...(genData[p.date_time] || {}),
          agile_actual: actualPrices[p.date_time] || null
        }));

        setForecast(mergedData);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [region, days]);

  // Fetch heatmap data separately (once on mount)
  useEffect(() => {
    setHeatmapLoading(true);
    fetchPriceHeatmap()
      .then(res => {
        // The backend returns stats_chart containing the heatmap Plotly figure
        setHeatmapData({
          heatmap: res.data.stats_chart
        });
        setHeatmapLoading(false);
      })
      .catch(err => {
        console.error('Heatmap error:', err);
        setHeatmapLoading(false);
      });
  }, []);

  const handleDaysChange = (newDays) => {
    setDays(newDays);
  };

  const handleHeatmapClick = (data) => {
    // Extract date from click event - the customdata contains the actual date
    if (!data.points || data.points.length === 0) return;
    
    const point = data.points[0];
    const dateStr = point.customdata; // customdata contains the date string
    
    // Verify we have a valid date
    if (!dateStr || dateStr === '') {
      console.warn('No date data for clicked point');
      return;
    }
    
    setSelectedDate(dateStr);
    setDailyLoading(true);
    
    fetchDailyBreakdown(dateStr, region.toUpperCase())
      .then(res => {
        // The backend returns stats_chart containing the breakdown with chart, stats, and daily_data
        setDailyBreakdown({
          chart: res.data.stats_chart?.chart
        });
        setDailyLoading(false);
      })
      .catch(err => {
        console.error('Error fetching daily breakdown:', err);
        setDailyLoading(false);
      });
  };

  const handleForecastToggle = (forecastId) => {
    setSelectedForecasts(prev =>
      prev.includes(forecastId)
        ? prev.filter(id => id !== forecastId)
        : [...prev, forecastId]
    );
  };

  const handleUpdateChart = () => {
    // Fetch data for selected forecasts
    if (selectedForecasts.length === 0) {
      setError('Please select at least one forecast');
      return;
    }

    setLoading(true);
    setError(null);

    Promise.all([
      fetchRegionalForecast(region.toUpperCase(), days),
      fetchGenerationDemand(region.toUpperCase(), days),
      fetchActualPrices(days)
    ])
      .then(([priceRes, genRes, actualRes]) => {
        const priceResults = Array.isArray(priceRes.data) ? priceRes.data : [];
        
        // Extract all forecast data that matches selected forecast IDs
        const allForecasts = priceResults.filter(forecast => 
          selectedForecasts.includes(forecast.id || forecast.forecast_date)
        );

        if (allForecasts.length === 0) {
          setError('No matching forecast data found');
          setLoading(false);
          return;
        }

        // Extract and merge generation/demand data
        let genData = {};
        const genResults = Array.isArray(genRes.data) ? genRes.data : (genRes.data?.results || []);
        genResults.forEach(item => {
          genData[item.date_time] = {
            demand: item.demand,
            bm_wind: item.bm_wind,
            emb_wind: item.emb_wind,
            solar: item.solar,
            rad: item.rad
          };
        });

        // Extract actual prices
        let actualPrices = {};
        const actualResults = Array.isArray(actualRes.data) ? actualRes.data : (actualRes.data?.results || []);
        actualResults.forEach(item => {
          actualPrices[item.date_time] = item.agile;
        });

        // Process all selected forecasts
        const forecastsData = allForecasts.map((forecast, idx) => {
          let priceData = [];
          if (forecast.agile_data) {
            priceData = forecast.agile_data.map(p => ({
              ...p,
              timestamp: p.date_time,
              forecast_index: idx,
              forecast_name: forecast.name
            }));
          }

          // Merge with generation/demand and actual prices (only for first forecast)
          if (idx === 0) {
            return priceData.map(p => ({
              ...p,
              ...(genData[p.date_time] || {}),
              agile_actual: actualPrices[p.date_time] || null
            }));
          }
          return priceData;
        });

        setForecast(forecastsData);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <div style={{ 
        display: 'flex', 
        flex: 1, 
        minHeight: 0, 
        overflow: 'hidden',
        flexDirection: windowWidth < 768 ? 'column' : 'row'
      }}>
        <div style={{ 
          flex: windowWidth < 768 ? '0 0 auto' : 1, 
          minWidth: 0, 
          overflow: 'auto', 
          display: 'flex', 
          flexDirection: 'column',
          minHeight: windowWidth < 768 ? 'auto' : 0,
          paddingLeft: windowWidth < 768 ? '0' : '0.5rem',
          paddingRight: windowWidth < 768 ? '0' : '0.5rem'
        }}>
          {loading && <div className="alert alert-info m-3">Loading forecast...</div>}
          {error && <div className="alert alert-danger m-3">Error: {error}</div>}
          {forecast && (
            <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '0.5rem 0' }}>
              <ForecastChart 
                data={forecast}
                showGenerationDemand={showGenerationDemand}
                showRangeOnForecast={showRangeOnForecast}
                showForecastOverlap={showForecastOverlap}
                heatmapData={heatmapData}
                heatmapLoading={heatmapLoading}
                windowWidth={windowWidth}
                onHeatmapClick={handleHeatmapClick}
              />
            </div>
          )}
        </div>
      </div>

      {/* Forecast Settings Modal */}
      <ForecastSettings
        days={days}
        onDaysChange={handleDaysChange}
        showGenerationDemand={showGenerationDemand}
        onGenerationDemandChange={setShowGenerationDemand}
        showRangeOnForecast={showRangeOnForecast}
        onRangeOnForecastChange={setShowRangeOnForecast}
        showForecastOverlap={showForecastOverlap}
        onForecastOverlapChange={setShowForecastOverlap}
        allForecasts={allForecasts}
        selectedForecasts={selectedForecasts}
        onForecastToggle={handleForecastToggle}
        onUpdateChart={handleUpdateChart}
      />

      {/* Daily Breakdown Modal */}
      {selectedDate && (
        <div className="modal show" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }} role="dialog">
          <div className="modal-dialog modal-lg" role="document" style={{ maxWidth: '90vw', margin: 'auto' }}>
            <div className="modal-content bg-dark border-secondary">
              <div className="modal-header border-secondary">
                <h5 className="modal-title" style={{ fontSize: 'clamp(0.9rem, 3vw, 1.25rem)' }}>Hourly Prices for {new Date(selectedDate).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setSelectedDate(null)} aria-label="Close"></button>
              </div>
              <div className="modal-body" style={{ maxHeight: '70vh', overflow: 'auto' }}>
                {dailyLoading && <div className="alert alert-info">Loading hourly data...</div>}
                {dailyBreakdown?.chart && !dailyLoading && (
                  <div style={{ height: '400px', width: '100%' }}>
                    <Plot
                      data={dailyBreakdown.chart.data}
                      layout={{ ...dailyBreakdown.chart.layout, autosize: true }}
                      config={{ scrollZoom: true, responsive: true }}
                      style={{ width: '100%', height: '100%' }}
                      useResizeHandler
                    />
                  </div>
                )}
                {!dailyLoading && !dailyBreakdown?.chart && (
                  <div className="alert alert-warning">No data available for this date</div>
                )}
              </div>
              <div className="modal-footer border-secondary">
                <button type="button" className="btn btn-secondary" onClick={() => setSelectedDate(null)}>Close</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ForecastPage;
