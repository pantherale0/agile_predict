import React from 'react';
import { useSettings } from '../contexts/SettingsContext';
import ForecastForm from './ForecastForm';
import './ForecastSettings.css';

export function ForecastSettingsButton({ onClick }) {
  return (
    <button
      className="btn btn-link nav-link forecast-settings-btn"
      onClick={onClick}
      title="Forecast Settings"
      aria-label="Forecast Settings"
    >
      <i className="fas fa-cog"></i>
    </button>
  );
}

function ForecastSettings({
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
  onUpdateChart
}) {
  const { showSettings, setShowSettings } = useSettings();

  const handleUpdateChart = () => {
    onUpdateChart();
    setShowSettings(false);
  };

  return (
    <>
      {/* Settings Modal */}
      {showSettings && (
        <div className="modal show forecast-settings-modal" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }} role="dialog">
          <div className="modal-dialog modal-dialog-scrollable" role="document" style={{ maxWidth: '600px' }}>
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">
                  <i className="fas fa-cog"></i> Forecast Settings
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowSettings(false)}
                  aria-label="Close"
                ></button>
              </div>
              <div className="modal-body">
                <ForecastForm
                  days={days}
                  onDaysChange={onDaysChange}
                  showGenerationDemand={showGenerationDemand}
                  onGenerationDemandChange={onGenerationDemandChange}
                  showRangeOnForecast={showRangeOnForecast}
                  onRangeOnForecastChange={onRangeOnForecastChange}
                  showForecastOverlap={showForecastOverlap}
                  onForecastOverlapChange={onForecastOverlapChange}
                  allForecasts={allForecasts}
                  selectedForecasts={selectedForecasts}
                  onForecastToggle={onForecastToggle}
                  onUpdateChart={handleUpdateChart}
                  isModal={true}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default ForecastSettings;
