import React from 'react';
import './ForecastForm.css';

function ForecastForm({ 
  days, 
  onDaysChange,
  showGenerationDemand,
  onGenerationDemandChange,
  showRangeOnForecast,
  onRangeOnForecastChange,
  showForecastOverlap,
  onForecastOverlapChange,
  allForecasts,
  selectedForecasts,
  onForecastToggle,
  onUpdateChart,
  isModal = false
}) {
  return (
    <div className={`forecast-options ${isModal ? 'forecast-options-modal' : ''}`}>
      <form className="forecast-form">
        <div className="accordion">
          <div className="accordion-item">
            <h2 className="accordion-header" id="optionsPanelHeader">
              <button className="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#options" aria-expanded="true" aria-controls="options">
                <i className="fas fa-sliders-h"></i> Options
              </button>
            </h2>
            <div id="options" className="accordion-collapse collapse show" aria-labelledby="optionsPanelHeader">
              <div className="accordion-body">
                <div className="mb-3">
                  <label htmlFor="daysInput" className="form-label">
                    <i className="fas fa-calendar-days"></i> Days to plot
                  </label>
                  <select
                    className="form-select"
                    id="daysInput"
                    value={days}
                    onChange={(e) => onDaysChange(parseInt(e.target.value))}
                  >
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14].map(d => (
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
                      <i className="fas fa-bolt"></i> Show generation and demand
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
                      <i className="fas fa-chart-line"></i> Show range on most recent forecast
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
                      <i className="fas fa-layer-group"></i> Show forecast overlap
                    </label>
                    <small className="d-block form-text text-muted">
                      Show forecast prices which have now been superseded by the actual Agile prices.
                    </small>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="accordion-item">
            <h2 className="accordion-header" id="forecastsPanelHeader">
              <button className="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#forecasts" aria-expanded="true" aria-controls="forecasts">
                <i className="fas fa-list"></i> Available Forecasts
              </button>
            </h2>
            <div id="forecasts" className="accordion-collapse collapse" aria-labelledby="forecastsPanelHeader">
              <div className="accordion-body">
                {allForecasts.map((forecast, index) => (
                  <div key={index} className="form-check">
                    <input
                      type="checkbox"
                      className="form-check-input"
                      name={`forecasts_to_plot_${forecast.id}`}
                      value={forecast.id}
                      id={`id_forecasts_to_plot_${index}`}
                      checked={selectedForecasts.includes(forecast.id)}
                      onChange={() => onForecastToggle(forecast.id)}
                    />
                    <label htmlFor={`id_forecasts_to_plot_${index}`} className="form-check-label">
                      <i className="fas fa-chart-area"></i> {forecast.name}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
        <button type="button" className="btn btn-primary w-100 mt-3" onClick={onUpdateChart}>
          <i className="fas fa-refresh"></i> Update Chart
        </button>
      </form>
    </div>
  );
}

export default ForecastForm;