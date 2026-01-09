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

  if (statsData.message) {
    return (
      <div className="container-lg fluid">
        <div className="row">
          <div className="col-lg p-4">
            <h2 className="mb-4">Model Performance Statistics</h2>
            <div className="alert alert-info">{statsData.message}</div>
          </div>
        </div>
      </div>
    );
  }

  // Safely access nested properties
  const statsChart = statsData?.stats_chart;
  const trendImage = statsData?.trend_image;
  const diagnosticPlots = statsData?.diagnostic_plots || [];

  if (!statsChart || !statsChart.data || !statsChart.layout) {
    return <div className="alert alert-warning">Stats data is incomplete or malformed</div>;
  }

  return (
    <div className="container-lg fluid">
      <div className="row">
        <div className="col-lg p-4">
          <h2 className="mb-4">Model Performance Statistics</h2>

          {/* Trend Section */}
          {trendImage && (
            <div className="stats-section">
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

          {/* Stats Chart Section */}
          <div className="stats-section mt-5">
            <h4 className="mb-4">Model Error Heatmap</h4>
            <p className="text-muted">
              The top plot shows the last week's actual Agile Price in yellow; the thin grey lines are the
              historical forecasts. The heatmap below shows how the errors in the grey lines have evolved over
              time with warm colours being big errors and blue being a perfect match.
            </p>
            <p className="text-muted">
              If the model is behaving well you should see warmer colours bottom right (ie errors due to
              forecasting a week ahead) and cooler colours towards the top and left.
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

          {/* Diagnostic Plots Section */}
          <div className="stats-section mt-5">
            <h4 className="mb-4">Model Diagnostic Plots - Most Recent Forecast</h4>
            <div className="row">
              {diagnosticPlots && diagnosticPlots.length > 0 ? (
                diagnosticPlots.map((plot, index) => (
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
                ))
              ) : (
                <div className="col-12">
                  <p className="text-muted">No diagnostic plots available. Run a forecast to generate them.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default StatsPage;
