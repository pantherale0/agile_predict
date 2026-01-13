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
        setStatsData(res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Stats error:', err);
        setError(err.message || 'Failed to load stats');
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="container-fluid stats-page">
        <div className="stats-container">
          <div className="alert alert-info">
            <span className="spinner-border spinner-border-sm me-2"></span>
            Loading model performance statistics...
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container-fluid stats-page">
        <div className="stats-container">
          <div className="alert alert-danger">
            <strong>Error:</strong> {error}
          </div>
        </div>
      </div>
    );
  }

  if (!statsData || (!statsData.stats_chart && statsData.message)) {
    return (
      <div className="container-fluid stats-page">
        <div className="stats-container">
          <h1 className="stats-title">Model Performance Statistics</h1>
          <div className="alert alert-warning">
            {statsData?.message || 'No statistics data available yet.'}
          </div>
        </div>
      </div>
    );
  }

  const statsChart = statsData?.stats_chart;
  const trendImage = statsData?.trend_image;
  const diagnosticPlots = statsData?.diagnostic_plots || [];

  return (
    <div className="container-fluid stats-page">
      <div className="stats-container">
        <h1 className="stats-title">Model Performance Statistics</h1>

        {/* Price History and Error Heatmap Section */}
        {statsChart && statsChart.data && statsChart.layout ? (
          <section className="stats-section">
            <h2 className="section-title">Agile Price Forecasts and Error Analysis</h2>
            <p className="section-description">
              The chart below shows the actual Agile prices (yellow line) over the last 7 days along with forecasts made at different times (grey lines).
              The heatmap below shows the absolute error for each forecast as a function of the forecast age and date.
            </p>
            <div className="chart-container">
              <Plot
                data={statsChart.data}
                layout={statsChart.layout}
                config={{ 
                  scrollZoom: true, 
                  responsive: true,
                  displayModeBar: true,
                  displaylogo: false
                }}
                style={{ width: '100%', height: '100%' }}
                useResizeHandler
              />
            </div>
          </section>
        ) : null}

        {/* Trend Analysis Section */}
        {trendImage && (
          <section className="stats-section">
            <h2 className="section-title">Model Robustness Analysis</h2>
            <p className="section-description">
              This plot shows how the model's accuracy (RMS Error) and robustness evolve over time as more data points are included in the training dataset.
            </p>
            <p className="section-description">
              The model is trained five times using 80% of the data for training and 20% for testing. Each iteration produces an RMS error for the model fit.
              The black line represents the mean error across these five iterations, while the pale yellow range shows ±1 standard deviation.
              As more data is added, the model should learn and improve, with the absolute error trending downwards and the uncertainty range narrowing.
            </p>
            <div className="image-container">
              <img 
                src={trendImage} 
                alt="Model RMS Error and Robustness vs Forecast Date" 
                className="trend-image"
              />
            </div>
          </section>
        )}

        {/* Diagnostic Plots Section */}
        {diagnosticPlots.length > 0 && (
          <section className="stats-section">
            <h2 className="section-title">Model Diagnostic Plots</h2>
            <p className="section-description">
              The following plots provide detailed analysis of the most recent forecast model's performance and characteristics.
            </p>

            <div className="diagnostic-grid">
              {diagnosticPlots.map((plot, index) => (
                <div 
                  key={index}
                  className={`diagnostic-card ${index === 0 ? 'full-width' : ''}`}
                >
                  <div className="diagnostic-header">
                    <h3 className="diagnostic-title">{plot.title}</h3>
                  </div>
                  <p className="diagnostic-description">
                    {plot.description}
                  </p>
                  <div className="diagnostic-image-wrapper">
                    <img
                      src={`/static/${plot.filename}`}
                      className="diagnostic-image"
                      alt={plot.title}
                      loading="lazy"
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

export default StatsPage;
