import React from 'react';

function AboutPage() {
  return (
    <div className="container-lg">
      <div className="row bg-body text-center py-4">
        <h2>About AgilePredict</h2>
      </div>
      <div className="row">
        <div className="col-lg-8 offset-lg-2">
          <div className="card mb-4">
            <div className="card-body">
              <h5 className="card-title">What is AgilePredict?</h5>
              <p className="card-text">
                AgilePredict is a machine learning-powered forecasting tool for UK Agile electricity prices. 
                It uses advanced algorithms to predict hourly energy prices across 16 regional DNO areas, 
                helping consumers and businesses make informed decisions about their energy consumption.
              </p>
            </div>
          </div>

          <div className="card mb-4">
            <div className="card-body">
              <h5 className="card-title">How It Works</h5>
              <ul>
                <li>Collects historical price data from Octopus Energy's Agile tariff</li>
                <li>Analyzes weather patterns, demand forecasts, and generation data</li>
                <li>Uses machine learning models to predict future prices</li>
                <li>Updates forecasts regularly with the latest available data</li>
              </ul>
            </div>
          </div>

          <div className="card mb-4">
            <div className="card-body">
              <h5 className="card-title">Data Sources</h5>
              <ul>
                <li><strong>Price Data:</strong> Octopus Energy API</li>
                <li><strong>Weather:</strong> UK Met Office</li>
                <li><strong>Generation:</strong> National Grid ESO</li>
                <li><strong>Demand:</strong> BMRS (Balancing Mechanism Reporting Service)</li>
              </ul>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Disclaimer</h5>
              <p className="card-text text-muted small">
                AgilePredict is an independent project and is not affiliated with Octopus Energy or any other energy company. 
                Forecasts are provided on an as-is basis. Please verify prices with your energy supplier before making any decisions.
                The accuracy of forecasts varies and should not be relied upon for critical decisions.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AboutPage;
