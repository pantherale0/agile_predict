import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { fetchRegionalForecast, fetchGenerationDemand, fetchActualPrices, fetchPriceHeatmap, fetchDailyBreakdown } from '../api/forecastAPI';
import ForecastChart from '../components/ForecastChart';
import ForecastForm from '../components/ForecastForm';
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
  const regionName = REGIONS[region.toUpperCase()] || 'Unknown Region';

  useEffect(() => {
    setLoading(true);
    setError(null);
    
    Promise.all([
      fetchRegionalForecast(region.toUpperCase(), days),
      fetchGenerationDemand(region.toUpperCase(), days),
      fetchActualPrices(days)
    ])
      .then(([priceRes, genRes, actualRes]) => {
        // Extract and map price data
        let priceData = [];
        if (priceRes.data && priceRes.data.results && priceRes.data.results.length > 0) {
          priceData = priceRes.data.results[0].prices.map(p => ({
            ...p,
            timestamp: p.date_time
          }));
        }

        // Extract and merge generation/demand data
        let genData = {};
        // Handle both array response (no pagination) and paginated response
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
        setHeatmapData(res.data);
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
    const dateStr = point.customdata;
    
    // Verify we have a valid date
    if (!dateStr || dateStr === '') {
      console.warn('No date data for clicked point');
      return;
    }
    
    setSelectedDate(dateStr);
    setDailyLoading(true);
    
    fetchDailyBreakdown(dateStr)
      .then(res => {
        setDailyBreakdown(res.data);
        setDailyLoading(false);
      })
      .catch(err => {
        console.error('Error fetching daily breakdown:', err);
        setDailyLoading(false);
      });
  };

  return (
    <div className="container-lg fluid">
      <div className="row bg-body text-center">
        <h3>{regionName} {region !== 'X' && `(DNO Region ${region})`}</h3>
      </div>
      <div className="row">
        <div className="col-lg-9">
          {loading && <div className="alert alert-info">Loading forecast...</div>}
          {error && <div className="alert alert-danger">Error: {error}</div>}
          {forecast && (
            <ForecastChart 
              data={forecast}
              showGenerationDemand={showGenerationDemand}
              showRangeOnForecast={showRangeOnForecast}
              showForecastOverlap={showForecastOverlap}
            />
          )}

          {/* 365-Day Price Heatmap Section */}
          <div className="card bg-dark border-secondary mt-4 mb-4">
            <div className="card-header bg-secondary">
              <h5 className="card-title mb-0">Historical Price Pattern (Last 365 Days)</h5>
            </div>
            <div className="card-body">
              {heatmapLoading && <div className="alert alert-info mb-0">Loading heatmap...</div>}
              {heatmapData?.heatmap && (
                <>
                  <Plot
                    data={heatmapData.heatmap.data}
                    layout={heatmapData.heatmap.layout}
                    config={{ scrollZoom: true, responsive: true }}
                    style={{ width: '100%' }}
                    useResizeHandler
                    onClick={handleHeatmapClick}
                  />
                  <div className="mt-3 row text-muted small">
                    <div className="col-md-6">
                      <p><strong>Min:</strong> £{heatmapData.stats.min_price.toFixed(2)}/MWh</p>
                      <p><strong>Max:</strong> £{heatmapData.stats.max_price.toFixed(2)}/MWh</p>
                    </div>
                    <div className="col-md-6">
                      <p><strong>Avg:</strong> £{heatmapData.stats.avg_price.toFixed(2)}/MWh</p>
                      <p><strong>Median:</strong> £{heatmapData.stats.median_price.toFixed(2)}/MWh</p>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="col-lg-3 bg-body">
          <ForecastForm 
            days={days} 
            onDaysChange={handleDaysChange}
            showGenerationDemand={showGenerationDemand}
            onGenerationDemandChange={setShowGenerationDemand}
            showRangeOnForecast={showRangeOnForecast}
            onRangeOnForecastChange={setShowRangeOnForecast}
            showForecastOverlap={showForecastOverlap}
            onForecastOverlapChange={setShowForecastOverlap}
          />
        </div>
      </div>

      {/* Daily Breakdown Modal */}
      {selectedDate && (
        <div className="modal show" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }} role="dialog">
          <div className="modal-dialog modal-lg" role="document">
            <div className="modal-content bg-dark border-secondary">
              <div className="modal-header border-secondary">
                <h5 className="modal-title">Hourly Prices for {new Date(selectedDate).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setSelectedDate(null)} aria-label="Close"></button>
              </div>
              <div className="modal-body">
                {dailyLoading && <div className="alert alert-info">Loading hourly data...</div>}
                {dailyBreakdown?.chart && !dailyLoading && (
                  <>
                    <Plot
                      data={dailyBreakdown.chart.data}
                      layout={dailyBreakdown.chart.layout}
                      config={{ scrollZoom: true, responsive: true }}
                      style={{ width: '100%' }}
                      useResizeHandler
                    />
                    <div className="mt-3 row text-muted small">
                      <div className="col-md-6">
                        <p><strong>Min:</strong> £{dailyBreakdown.stats.min_price.toFixed(2)}/MWh</p>
                        <p><strong>Max:</strong> £{dailyBreakdown.stats.max_price.toFixed(2)}/MWh</p>
                      </div>
                      <div className="col-md-6">
                        <p><strong>Avg:</strong> £{dailyBreakdown.stats.avg_price.toFixed(2)}/MWh</p>
                        <p><strong>Median:</strong> £{dailyBreakdown.stats.median_price.toFixed(2)}/MWh</p>
                      </div>
                    </div>
                  </>
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
