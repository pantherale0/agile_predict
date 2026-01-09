import React from 'react';

function ForecastForm({ 
  days, 
  onDaysChange,
  showGenerationDemand,
  onGenerationDemandChange,
  showRangeOnForecast,
  onRangeOnForecastChange,
  showForecastOverlap,
  onForecastOverlapChange
}) {
  return (
    <div className="forecast-options">
      <div className="options-header" data-bs-toggle="collapse" data-bs-target="#optionsPanel" role="button">
        <h6>Options</h6>
        <i className="bi bi-chevron-down"></i>
      </div>

      <div id="optionsPanel" className="collapse show">
        <form className="forecast-form">
          <div className="mb-3">
            <label htmlFor="daysInput" className="form-label">Days to plot</label>
            <select
              className="form-select"
              id="daysInput"
              value={days}
              onChange={(e) => onDaysChange(parseInt(e.target.value))}
            >
              {[1, 2, 3, 4, 5, 6, 7, 10, 14, 21, 30].map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <div className="mb-3">
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                id="showGenerationDemand"
                checked={showGenerationDemand}
                onChange={(e) => onGenerationDemandChange(e.target.checked)}
              />
              <label className="form-check-label" htmlFor="showGenerationDemand">
                Show generation and demand
              </label>
              <small className="d-block form-text text-muted">
                Shows the generation and demand forecasts that were used to generate the most recent selected price forecast.
              </small>
            </div>
          </div>

          <div className="mb-3">
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                id="showRangeOnForecast"
                checked={showRangeOnForecast}
                onChange={(e) => onRangeOnForecastChange(e.target.checked)}
              />
              <label className="form-check-label" htmlFor="showRangeOnForecast">
                Show range on most recent forecast
              </label>
              <small className="d-block form-text text-muted">
                Show the 10th and 90th confidence level spread on the most recent forecast. This reflects the model uncertainty, not the weather uncertainty.
              </small>
            </div>
          </div>

          <div className="mb-3">
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                id="showForecastOverlap"
                checked={showForecastOverlap}
                onChange={(e) => onForecastOverlapChange(e.target.checked)}
              />
              <label className="form-check-label" htmlFor="showForecastOverlap">
                Show forecast overlap
              </label>
              <small className="d-block form-text text-muted">
                Show forecast prices which have now been superseded by the actual Agile prices.
              </small>
            </div>
          </div>

          <button type="button" className="btn btn-primary w-100" onClick={() => window.location.reload()}>
            Update Chart
          </button>
        </form>
      </div>
    </div>
  );
}

export default ForecastForm;