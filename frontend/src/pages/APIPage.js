import React from 'react';

function APIPage() {
  return (
    <div className="container-lg">
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">API Documentation</h5>
              <p className="card-text">
                The AgilePredict API provides endpoints to access regional electricity price forecasts and historical data.
              </p>
              <h6>Base URL</h6>
              <code>{window.CONFIG.API_URL}</code>
              <p/>
              <h6>Docs URL</h6>
              <code>{window.CONFIG.API_URL.replace('/api', '/')}docs</code>

              <h6 className="mt-4">Home Assistant Integration</h6>
              <p>You can integrate AgilePredict with Home Assistant using a REST sensor:</p>
              <pre><code>{`sensor:
  - platform: rest
    resource: ${window.CONFIG.API_URL}/forecasts/X/latest?days=7
    name: "Agile Price Forecast"
    value_template: "{{ value_json[0].agile_pred }}"
    unit_of_measurement: "p/kWh"`}</code></pre>
              <p>Replace <code>X</code> with your desired region code. A list can be found in the Region menu in the navigation bar.</p>

              <h6 className="mt-4">Authentication</h6>
              <p>No authentication is required to access the AgilePredict API.</p>

              <h6 className="mt-4">Rate Limiting</h6>
              <p>Please limit your requests to a maximum of 20 requests per hour to avoid being rate limited.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default APIPage;
