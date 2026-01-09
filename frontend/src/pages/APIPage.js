import React from 'react';

function APIPage() {
  return (
    <div className="container-lg">
      <div className="row bg-body text-center py-4">
        <h2>API and Home Assistant</h2>
      </div>
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">API Documentation</h5>
              <p className="card-text">
                The AgilePredict API provides endpoints to access regional electricity price forecasts and historical data.
              </p>
              <h6>Base URL</h6>
              <code>http://localhost:8000/api</code>
              
              <h6 className="mt-4">Endpoints</h6>
              <ul>
                <li><code>GET /forecast/</code> - Get forecast data</li>
                <li><code>GET /forecast/?region=X&days=14</code> - Get forecast for specific region and days</li>
                <li><code>GET /history/</code> - Get historical price data</li>
              </ul>

              <h6 className="mt-4">Home Assistant Integration</h6>
              <p>You can integrate AgilePredict with Home Assistant using a REST sensor:</p>
              <pre><code>{`sensor:
  - platform: rest
    resource: http://localhost:8000/api/forecast/?region=X&days=1
    name: "Agile Price Forecast"
    value_template: "{{ value_json[0].agile_pred }}"
    unit_of_measurement: "p/kWh"`}</code></pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default APIPage;
