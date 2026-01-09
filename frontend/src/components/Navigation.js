import React from 'react';
import { Link, useLocation } from 'react-router-dom';

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

function Navigation() {
  const location = useLocation();

  return (
    <header>
      <div className="container-lg">
        <nav className="navbar navbar-expand-lg bg-primary-subtle">
          <div className="container-fluid">
            <Link className="navbar-brand" to="/">AgilePredict</Link>
            <button
              className="navbar-toggler"
              type="button"
              data-bs-toggle="collapse"
              data-bs-target="#navbarSupportedContent"
              aria-controls="navbarSupportedContent"
              aria-expanded="false"
              aria-label="Toggle navigation"
            >
              <span className="navbar-toggler-icon"></span>
            </button>
            <div className="collapse navbar-collapse" id="navbarSupportedContent">
              <ul className="navbar-nav me-auto mb-2 mb-lg-0">
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
            </div>
          </div>
        </nav>
      </div>
    </header>
  );
}

export default Navigation;
