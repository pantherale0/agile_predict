import React, { useState, useEffect } from 'react';
import { fetchStats } from '../api/forecastAPI';
import Plot from 'react-plotly.js';
import './StatsPage.css';

function StatsPage() {
  const [statsData, setStatsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    
    fetchStats()
      .then(res => {
        console.log('Stats data received:', res.data);
        // Handle paginated response structure
        const data = Array.isArray(res.data.results) && res.data.results.length > 0 
          ? res.data.results[0] 
          : res.data;
        console.log('Extracted stats:', data);
        setStatsData(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Stats error:', err);
        setError(err.message || 'Failed to load stats');
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="alert alert-info">Loading stats...</div>;
  }

  if (error) {
    return <div className="alert alert-danger">Error: {error}</div>;
  }

  if (!statsData || (!statsData.stats_chart && !statsData.message)) {
    return <div className="alert alert-warning">No stats available</div>;
  }

  // Safely access nested properties
  const statsChart = statsData?.stats_chart;
  const trendImage = statsData?.trend_image;
  const diagnosticPlots = statsData?.diagnostic_plots || [];

  return (
    <div className="container-lg fluid">
      <div className="row">
        <div className="col-lg p-4">
          <h2 className="mb-4">Model Performance Statistics</h2>
          
          {statsData.message && (
            <div className="alert alert-info mb-4">{statsData.message}</div>
          )}

          {/* Stats Chart Section */}
          {statsChart && statsChart.data && statsChart.layout ? (
            <div className="stats-section mt-5">
              <h4 className="mb-4">Price History Chart</h4>
              <p className="text-muted">
                This chart shows the actual Agile prices and Day-Ahead prices over the selected period.
              </p>
              <div className="row mt-3">
                <Plot
                  data={statsChart.data}
                  layout={statsChart.layout}
                  config={{ scrollZoom: true, responsive: true }}
                  style={{ width: '100%' }}
                  useResizeHandler
                />
              </div>
            </div>
          ) : (
            <div className="alert alert-warning">No price chart data available</div>
          )}

          {/* Trend Section */}
          {trendImage && (
            <div className="stats-section mt-5">
              <h4 className="mb-4">Model RMS Error and Robustness vs Forecast Date</h4>
              <p className="text-muted">
                This plot shows how the model fit to the training data and its robustness evolve over time as more
                points are included.
              </p>
              <p className="text-muted">
                The model is trained five times using 80% of the data to train and the other 20% to test. Each iteration
                gives an RMS error for the fit. The mean of the five plotted as the black line and the range (as +/- 1
                standard deviation) is the pale yellow range. As more data is added the model should learn and so the
                absolute error should trend downwards and the range should narrow.
              </p>
              <div className="row mt-3">
                <img 
                  src={trendImage} 
                  alt="Trend" 
                  className="trend-image"
                />
              </div>
            </div>
          )}

          {/* Summary Statistics Section */}
          {statsData.summary_stats && (
            <div className="stats-section mt-5">
              <h4 className="mb-4">Summary Statistics</h4>
              <div className="row">
                {statsData.summary_stats.agile && (
                  <div className="col-md-6 mb-4">
                    <div className="card bg-dark border-secondary">
                      <div className="card-body">
                        <h5 className="card-title text-light">Agile Pricing Stats</h5>
                        <ul className="list-unstyled text-muted">
                          <li><strong>Min:</strong> £{statsData.summary_stats.agile.min?.toFixed(2) || 'N/A'}</li>
                          <li><strong>Max:</strong> £{statsData.summary_stats.agile.max?.toFixed(2) || 'N/A'}</li>
                          <li><strong>Mean:</strong> £{statsData.summary_stats.agile.mean?.toFixed(2) || 'N/A'}</li>
                          <li><strong>Median:</strong> £{statsData.summary_stats.agile.median?.toFixed(2) || 'N/A'}</li>
                          <li><strong>Std Dev:</strong> £{statsData.summary_stats.agile.std?.toFixed(2) || 'N/A'}</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
                {statsData.summary_stats.day_ahead && (
                  <div className="col-md-6 mb-4">
                    <div className="card bg-dark border-secondary">
                      <div className="card-body">
                        <h5 className="card-title text-light">Day-Ahead Pricing Stats</h5>
                        <ul className="list-unstyled text-muted">
                          <li><strong>Min:</strong> £{statsData.summary_stats.day_ahead.min?.toFixed(2) || 'N/A'}</li>
                          <li><strong>Max:</strong> £{statsData.summary_stats.day_ahead.max?.toFixed(2) || 'N/A'}</li>
                          <li><strong>Mean:</strong> £{statsData.summary_stats.day_ahead.mean?.toFixed(2) || 'N/A'}</li>
                          <li><strong>Median:</strong> £{statsData.summary_stats.day_ahead.median?.toFixed(2) || 'N/A'}</li>
                          <li><strong>Std Dev:</strong> £{statsData.summary_stats.day_ahead.std?.toFixed(2) || 'N/A'}</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Forecast Accuracy Section */}
          {statsData.forecast_accuracy && (
            <div className="stats-section mt-5">
              <h4 className="mb-4">Forecast Accuracy</h4>
              <div className="card bg-dark border-secondary">
                <div className="card-body">
                  <ul className="list-unstyled text-muted">
                    <li><strong>RMSE:</strong> {statsData.forecast_accuracy.rmse?.toFixed(2) || 'N/A'}</li>
                    <li><strong>MAE:</strong> {statsData.forecast_accuracy.mae?.toFixed(2) || 'N/A'}</li>
                    <li><strong>MAPE:</strong> {statsData.forecast_accuracy.mape?.toFixed(2) || 'N/A'}%</li>
                    <li><strong>Forecast Date:</strong> {statsData.forecast_accuracy.forecast_date || 'N/A'}</li>
                    <li><strong>Samples:</strong> {statsData.forecast_accuracy.samples || 'N/A'}</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Diagnostic Plots Section */}
          {statsData.diagnostic_plots && statsData.diagnostic_plots.length > 0 && (
            <div className="stats-section mt-5">
              <h4 className="mb-4">Model Diagnostic Plots - Most Recent Forecast</h4>
              <div className="row">
                {statsData.diagnostic_plots.map((plot, index) => (
                  <div 
                    key={index}
                    className={index === 0 ? "col-lg-12 mb-4" : "col-md-6 mb-4"}
                  >
                    <h5 className="text-light">{plot.title}</h5>
                    <p className="text-muted">{plot.description}</p>
                    <img
                      src={`/static/${plot.filename}`}
                      className="diagnostic-image"
                      alt={plot.filename}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default StatsPage;
