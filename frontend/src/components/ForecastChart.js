import React from 'react';
import Plot from 'react-plotly.js';

function ForecastChart({ 
  data,
  showGenerationDemand = true,
  showRangeOnForecast = true,
  showForecastOverlap = false,
  heatmapData = null,
  heatmapLoading = false,
  windowWidth = 1024,
  onHeatmapClick = () => {}
}) {
  // Handle both single forecast array and multiple forecasts array
  const isMultipleForecastsFormat = Array.isArray(data) && Array.isArray(data[0]);
  const forecastsData = isMultipleForecastsFormat ? data : [data];

  if (!forecastsData || forecastsData.length === 0 || !forecastsData[0] || forecastsData[0].length === 0) {
    return <div className="alert alert-warning">No forecast data available</div>;
  }

  // Color palette for multiple forecasts
  const colors = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22'];

  // Use first forecast for generation/demand data
  const firstForecast = forecastsData[0];
  const timestamps = firstForecast.map(d => d.timestamp || d.date_time);
  const actualPrices = showForecastOverlap ? firstForecast.map(d => d.agile_actual || null) : [];

  // Calculate data ranges to lock axes
  const timeMin = new Date(Math.min(...timestamps.map(t => new Date(t).getTime())));
  const timeMax = new Date(Math.max(...timestamps.map(t => new Date(t).getTime())));
  
  // Calculate price range with 5% padding - include all forecasts
  const allPrices = [];
  forecastsData.forEach(forecast => {
    forecast.forEach(d => {
      if (d.agile_pred !== null && d.agile_pred !== undefined) allPrices.push(d.agile_pred);
      if (showRangeOnForecast && d.agile_high !== null && d.agile_high !== undefined) allPrices.push(d.agile_high);
      if (showRangeOnForecast && d.agile_low !== null && d.agile_low !== undefined) allPrices.push(d.agile_low);
    });
  });
  if (showForecastOverlap) {
    actualPrices.forEach(p => {
      if (p !== null && p !== undefined) allPrices.push(p);
    });
  }
  
  const priceMin = Math.min(...allPrices);
  const priceMax = Math.max(...allPrices);
  const pricePadding = (priceMax - priceMin) * 0.05;
  
  // Calculate power range with 5% padding
  const bmWinds = firstForecast.map(d => d.bm_wind ? d.bm_wind / 1000 : 0);
  const embWinds = firstForecast.map(d => d.emb_wind ? d.emb_wind / 1000 : 0);
  const solars = firstForecast.map(d => d.solar ? d.solar / 1000 : 0);
  
  // Forecast National Demand = (demand + solar + emb_wind) / 1000
  const forecastDemands = firstForecast.map((d) => {
    const demand = d.demand || 0;
    const solar = d.solar || 0;
    const embWind = d.emb_wind || 0;
    return (demand + solar + embWind) / 1000;
  });
  
  const allPowerValues = [...bmWinds, ...embWinds, ...solars, ...forecastDemands].filter(v => v !== null && !isNaN(v));
  const powerMin = Math.min(...allPowerValues);
  const powerMax = Math.max(...allPowerValues);
  const powerPadding = (powerMax - powerMin) * 0.05;

  // PRICE FORECAST TRACES (Top Graph) - Include all selected forecasts
  const priceTraces = [];
  
  forecastsData.forEach((forecast, forecastIdx) => {
    const pricePreds = forecast.map(d => d.agile_pred);
    const priceHighs = showRangeOnForecast ? forecast.map(d => d.agile_high || null) : [];
    const priceLows = showRangeOnForecast ? forecast.map(d => d.agile_low || null) : [];
    
    const forecastName = forecast[0]?.forecast_name || `Forecast ${forecastIdx + 1}`;
    const color = colors[forecastIdx % colors.length];
    
    // Add main forecast line
    priceTraces.push({
      x: timestamps,
      y: pricePreds,
      type: 'scatter',
      mode: 'lines',
      name: forecastName,
      line: { color: color, width: 3 },
    });

    // Add price range for this forecast (only for first forecast to avoid clutter)
    if (showRangeOnForecast && forecastIdx === 0 && priceHighs.some(h => h !== null)) {
      priceTraces.push({
        x: timestamps,
        y: priceHighs,
        type: 'scatter',
        mode: 'lines',
        name: 'Price High (90%)',
        line: { color: 'rgba(220, 53, 69, 0)', width: 0 },
        showlegend: true,
      });
      priceTraces.push({
        x: timestamps,
        y: priceLows,
        type: 'scatter',
        mode: 'lines',
        name: 'Price Low (10%)',
        fill: 'tonexty',
        fillcolor: 'rgba(220, 53, 69, 0.3)',
        line: { color: 'rgba(220, 53, 69, 0)', width: 0 },
        showlegend: true,
      });
    }
  });

  // Add actual prices if showing overlap (only once)
  if (showForecastOverlap && actualPrices.some(p => p !== null)) {
    priceTraces.push({
      x: timestamps,
      y: actualPrices,
      type: 'scatter',
      mode: 'lines',
      name: 'Actual',
      line: { color: 'yellow', width: 3 },
    });
  }

  // GENERATION AND DEMAND TRACES (Bottom Graph)
  const genTraces = [];

  // Metered wind (bm_wind) - green stacked area, fill to zero
  genTraces.push({
    x: timestamps,
    y: bmWinds,
    fill: 'tozeroy',
    line: { color: 'rgba(63,127,63)', width: 1 },
    fillcolor: 'rgba(127,255,127,0.8)',
    name: 'Forecast Metered Wind',
  });

  // Embedded wind stacked on top of metered
  const stackedEmbed = embWinds.map((e, i) => bmWinds[i] + e);
  genTraces.push({
    x: timestamps,
    y: stackedEmbed,
    fill: 'tonexty',
    line: { color: 'blue', width: 1 },
    fillcolor: 'rgba(127,127,255,0.8)',
    name: 'Forecast Embedded Wind',
  });

  // Solar stacked on top
  const stackedSolar = solars.map((s, i) => bmWinds[i] + embWinds[i] + s);
  genTraces.push({
    x: timestamps,
    y: stackedSolar,
    fill: 'tonexty',
    line: { color: 'lightgray', width: 1 },
    fillcolor: 'rgba(255,255,127,0.8)',
    name: 'Forecast Solar',
  });

  // National demand (cyan line) - drawn last so it's on top
  genTraces.push({
    x: timestamps,
    y: forecastDemands,
    line: { color: 'cyan', width: 3 },
    name: 'Forecast National Demand',
  });

  const priceLayout = {
    title: {
      text: 'Agile Price',
      font: { size: 16, color: '#fff' }
    },
    dragmode: 'pan',
    xaxis: { 
      title: { text: 'Time', font: { color: '#ccc' } },
      tickfont: { color: '#ccc', size: 11 },
      gridcolor: '#495057',
      fixedrange: true
    },
    yaxis: { 
      title: { text: 'Price [£/MWh]', font: { color: '#ccc' } },
      tickfont: { color: '#ccc', size: 11 },
      gridcolor: '#495057',
      fixedrange: true
    },
    hovermode: 'x unified',
    margin: { l: 60, r: 40, t: 50, b: 50 },
    legend: { 
      orientation: 'h', 
      y: -0.35, 
      x: 0.5, 
      xanchor: 'center', 
      yanchor: 'top',
      font: { color: '#ccc', size: 10 },
      bgcolor: 'rgba(33, 37, 41, 0.8)',
      bordercolor: '#495057',
      borderwidth: 1
    },
    template: 'plotly_dark',
    plot_bgcolor: '#212529',
    paper_bgcolor: '#343a40',
    font: { color: '#ccc' },
    autosize: true,
  };

  const genLayout = {
    title: {
      text: 'Generation and Demand',
      font: { size: 16, color: '#fff' }
    },
    dragmode: 'pan',
    xaxis: { 
      title: { text: 'Time', font: { color: '#ccc' } },
      tickfont: { color: '#ccc', size: 11 },
      gridcolor: '#495057',
      fixedrange: true
    },
    yaxis: { 
      title: { text: 'Power [GW]', font: { color: '#ccc' } },
      tickfont: { color: '#ccc', size: 11 },
      gridcolor: '#495057',
      fixedrange: true
    },
    hovermode: 'x unified',
    margin: { l: 60, r: 40, t: 50, b: 50 },
    legend: { 
      orientation: 'h', 
      y: -0.35, 
      x: 0.5, 
      xanchor: 'center', 
      yanchor: 'top',
      font: { color: '#ccc', size: 10 },
      bgcolor: 'rgba(33, 37, 41, 0.8)',
      bordercolor: '#495057',
      borderwidth: 1
    },
    template: 'plotly_dark',
    plot_bgcolor: '#212529',
    paper_bgcolor: '#343a40',
    font: { color: '#ccc' },
    autosize: true,
  };

  // Render based on showGenerationDemand flag
  if (showGenerationDemand) {
    return (
      <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '0.5rem 0' }}>
        <div style={{ flex: 1, minHeight: '280px', width: '100%', minWidth: 0 }}>
          <Plot
            data={priceTraces}
            layout={priceLayout}
            config={{ scrollZoom: true, responsive: true, doubleClick: false, displayModeBar: false }}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        </div>
        <div style={{ flex: 1, minHeight: '280px', width: '100%', minWidth: 0 }}>
          <Plot
            data={genTraces}
            layout={genLayout}
            config={{ scrollZoom: true, responsive: true, doubleClick: false, displayModeBar: false }}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        </div>
        {/* 365-Day Price Heatmap Section */}
        {heatmapData?.heatmap && (
        <div style={{ height: windowWidth < 768 ? '280px' : '320px', width: '100%', marginBottom: '0.5rem' }}>
        <Plot
          data={heatmapData.heatmap.data}
          layout={{ 
            ...heatmapData.heatmap.layout, 
            autosize: true,
            margin: { l: 60, r: 40, t: 40, b: 50 },
            modeBarButtonsToRemove: ['zoom2d', 'select2d', 'pan2d', 'lasso2d'],
            dragmode: 'pan'
          }}
          config={{ scrollZoom: true, responsive: true, doubleClick: false, displayModeBar: false }}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler
          onClick={onHeatmapClick}
        />
        </div>
        )}
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '0.5rem 0' }}>
      <div style={{ flex: 1, minHeight: '350px', minWidth: 0 }}>
        <Plot
          data={priceTraces}
          layout={priceLayout}
          config={{ scrollZoom: true, responsive: true }}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler
        />
      </div>
      {/* 365-Day Price Heatmap Section */}
      <div className="heatmap-section" style={{ padding: '0.5rem', margin: '0', paddingBottom: '1rem' }}>
        {heatmapLoading && <div className="alert alert-info">Loading heatmap...</div>}
        {heatmapData?.heatmap && (
          <>
            <h5 style={{ color: '#e0e0e0', margin: '0 0 1rem 0', padding: '0', wordWrap: 'break-word', overflow: 'hidden' }}>Historical Price Pattern (Last 365 Days)</h5>
            <div style={{ height: windowWidth < 768 ? '280px' : '320px', width: '100%', marginBottom: '0.5rem' }}>
              <Plot
                data={heatmapData.heatmap.data}
                layout={{ 
                  ...heatmapData.heatmap.layout, 
                  autosize: true,
                  margin: { l: 60, r: 40, t: 40, b: 50 }
                }}
                config={{ scrollZoom: true, responsive: true, staticPlot: true }}
                style={{ width: '100%', height: '100%' }}
                useResizeHandler
                onClick={onHeatmapClick}
              />
            </div>
            <div style={{ marginTop: '0.25rem', marginBottom: '0', textAlign: 'center', color: '#adb5bd', fontSize: '0.85rem' }}>
              <p style={{ margin: '0' }}>Click on a day to see hourly price breakdown</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default ForecastChart;
