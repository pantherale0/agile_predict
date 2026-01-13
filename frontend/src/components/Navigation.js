import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useSettings } from '../contexts/SettingsContext';
import { ForecastSettingsButton } from './ForecastSettings';
import './Navigation.css';

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

const PAGE_TITLES = {
  '/X': 'National Average',
  '/A': 'Eastern England',
  '/B': 'East Midlands',
  '/C': 'London',
  '/D': 'Merseyside and Northern Wales',
  '/E': 'West Midlands',
  '/F': 'North Eastern England',
  '/G': 'North Western England',
  '/H': 'Southern England',
  '/J': 'South Eastern England',
  '/K': 'Southern Wales',
  '/L': 'South Western England',
  '/M': 'Yorkshire',
  '/N': 'Southern Scotland',
  '/P': 'Northern Scotland',
  '/api': 'API and Home Assistant',
  '/stats': 'Stats',
  '/about': 'About'
};

function Navigation() {
  const location = useLocation();
  const { setShowSettings } = useSettings();

  const getPageTitle = () => {
    return PAGE_TITLES[location.pathname] || 'Agile Predict';
  };

  const isForecastPage = () => {
    const path = location.pathname;
    // Forecast pages are region pages or home
    return path === '/X' || Object.keys(REGIONS).some(code => path === `/${code}`);
  };

  return (
    <header className="w-100">
      <nav className="navbar sticky-top navbar-expand-lg bg-primary-subtle w-100">
        <div className="navbar-container d-flex align-items-center justify-content-between w-100">
          {/* Left: Toggle button */}
          <button
            className="btn btn-outline-secondary navbar-toggler-left"
            type="button"
            data-bs-toggle="collapse"
            data-bs-target="#navbarSupportedContent"
            aria-controls="navbarSupportedContent"
            aria-expanded="false"
            aria-label="Toggle navigation"
          >
            <i className="fas fa-bars"></i>
          </button>

          {/* Center: Page Title */}
          <span className="navbar-brand mb-0 h1 navbar-title">{getPageTitle()}</span>

          {/* Right: Settings button */}
          {isForecastPage() && (
            <button
              className="btn btn-outline-secondary navbar-settings-btn"
              type="button"
              onClick={() => setShowSettings(true)}
              title="Forecast Settings"
              aria-label="Forecast Settings"
            >
              <i className="fas fa-cog"></i>
            </button>
          )}
        </div>

        {/* Collapsible navigation menu */}
        <div className="collapse navbar-collapse w-100" id="navbarSupportedContent">
          <ul className="navbar-nav w-100">
            <li className="nav-item">
              <Link className="nav-link" to="/X">Home</Link>
            </li>
            <li className="nav-item dropdown">
              <button
                className="nav-link dropdown-toggle btn btn-link"
                type="button"
                data-bs-toggle="dropdown"
                aria-expanded="false"
                style={{ border: 'none', background: 'none', padding: '0.5rem 1rem' }}
              >
                Region
              </button>
              <ul className="dropdown-menu">
                {Object.entries(REGIONS).map(([code, name]) => (
                  <li key={code}>
                    <Link className="dropdown-item" to={`/${code}`}>
                      {code} - {name}
                    </Link>
                  </li>
                ))}
              </ul>
            </li>
            <li className="nav-item">
              <Link className="nav-link" to="/api">API and Home Assistant</Link>
            </li>
            <li className="nav-item">
              <Link className="nav-link" to="/stats">Stats</Link>
            </li>
            <li className="nav-item">
              <Link className="nav-link" to="/about">About</Link>
            </li>
          </ul>
          <ForecastSettingsButton onClick={() => setShowSettings(true)} />
        </div>
      </nav>
    </header>
  );
}
  
  export default Navigation;
