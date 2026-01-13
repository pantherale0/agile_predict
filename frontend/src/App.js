import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { SettingsProvider } from './contexts/SettingsContext';
import Navigation from './components/Navigation';
import ForecastPage from './pages/ForecastPage';
import APIPage from './pages/APIPage';
import StatsPage from './pages/StatsPage';
import AboutPage from './pages/AboutPage';
import './App.css';

function App() {
  // Get the last visited region from localStorage, default to 'X'
  const getDefaultRegion = () => {
    const lastRegion = localStorage.getItem('lastVisitedRegion');
    return lastRegion || 'X';
  };

  return (
    <SettingsProvider>
      <Router>
        <div className="d-flex flex-column min-vh-100">
          <Navigation />
          <main className="flex-grow-1">
            <Routes>
              <Route path="/" element={<Navigate to={`/${getDefaultRegion()}`} replace />} />
              <Route path="/:region" element={<ForecastPage />} />
              <Route path="/api" element={<APIPage />} />
              <Route path="/stats" element={<StatsPage />} />
              <Route path="/about" element={<AboutPage />} />
            </Routes>
          </main>
        </div>
      </Router>
    </SettingsProvider>
  );
}

export default App;
