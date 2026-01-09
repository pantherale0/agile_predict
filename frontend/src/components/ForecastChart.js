import React from 'react';
import Plot from 'react-plotly.js';

function ForecastChart({ 
  data,
  showGenerationDemand = true,
  showRangeOnForecast = true,
  showForecastOverlap = false
}) {
  if (!data || data.length === 0) {
    return <div className="alert alert-warning">No forecast data available</div>;
  }

  const timestamps = data.map(d => d.timestamp || d.date_time);
  const pricePreds = data.map(d => d.agile_pred);
  const priceHighs = showRangeOnForecast ? data.map(d => d.agile_high || null) : [];
  const priceLows = showRangeOnForecast ? data.map(d => d.agile_low || null) : [];
  const actualPrices = showForecastOverlap ? data.map(d => d.agile_actual || null) : [];

  // Generation data (convert to GW by dividing by 1000)
  const bmWinds = data.map(d => d.bm_wind ? d.bm_wind / 1000 : 0);
  const embWinds = data.map(d => d.emb_wind ? d.emb_wind / 1000 : 0);
  const solars = data.map(d => d.solar ? d.solar / 1000 : 0);
  
  // Forecast National Demand = (demand + solar + emb_wind) / 1000
  const forecastDemands = data.map((d) => {
    const demand = d.demand || 0;
    const solar = d.solar || 0;
    const embWind = d.emb_wind || 0;
    return (demand + solar + embWind) / 1000;
  });

  // Calculate data ranges to lock axes
  const timeMin = new Date(Math.min(...timestamps.map(t => new Date(t).getTime())));
  const timeMax = new Date(Math.max(...timestamps.map(t => new Date(t).getTime())));
  
  // Calculate price range with 5% padding
  const allPrices = [...pricePreds, ...priceHighs.filter(h => h !== null), ...priceLows.filter(l => l !== null), ...actualPrices.filter(p => p !== null)];
  const priceMin = Math.min(...allPrices);
  const priceMax = Math.max(...allPrices);
  const pricePadding = (priceMax - priceMin) * 0.05;
  
  // Calculate power range with 5% padding
  const allPowerValues = [...bmWinds, ...embWinds, ...solars, ...forecastDemands].filter(v => v !== null && !isNaN(v));
  const powerMin = Math.min(...allPowerValues);
  const powerMax = Math.max(...allPowerValues);
  const powerPadding = (powerMax - powerMin) * 0.05;

  // PRICE FORECAST TRACES (Top Graph)
  const priceTraces = [
    {
      x: timestamps,
      y: pricePreds,
      type: 'scatter',
      mode: 'lines',
      name: 'Predicted Price',
      line: { color: '#ff7f0e', width: 3 },
    }
  ];

  // Add price range (confidence interval)
  if (showRangeOnForecast && priceHighs.some(h => h !== null)) {
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

  // Add actual prices if showing overlap
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
      tickfont: { color: '#ccc' },
      gridcolor: '#495057',
      fixedrange: false
    },
    yaxis: { 
      title: { text: 'Price [£/MWh]', font: { color: '#ccc' } },
      tickfont: { color: '#ccc' },
      gridcolor: '#495057',
      fixedrange: false
    },
    hovermode: 'x unified',
    margin: { l: 80, r: 80, t: 60, b: 80 },
    legend: { 
      orientation: 'h', 
      y: -0.25, 
      x: 0.5, 
      xanchor: 'center', 
      yanchor: 'top',
      font: { color: '#ccc' },
      bgcolor: 'rgba(33, 37, 41, 0.8)',
      bordercolor: '#495057',
      borderwidth: 1
    },
    template: 'plotly_dark',
    plot_bgcolor: '#212529',
    paper_bgcolor: '#343a40',
    font: { color: '#ccc' },
    height: 400,
  };

  const genLayout = {
    title: {
      text: 'Generation and Demand',
      font: { size: 16, color: '#fff' }
    },
    dragmode: 'pan',
    xaxis: { 
      title: { text: 'Time', font: { color: '#ccc' } },
      tickfont: { color: '#ccc' },
      gridcolor: '#495057',
      fixedrange: false
    },
    yaxis: { 
      title: { text: 'Power [GW]', font: { color: '#ccc' } },
      tickfont: { color: '#ccc' },
      gridcolor: '#495057',
      fixedrange: false
    },
    hovermode: 'x unified',
    margin: { l: 80, r: 80, t: 60, b: 80 },
    legend: { 
      orientation: 'h', 
      y: -0.25, 
      x: 0.5, 
      xanchor: 'center', 
      yanchor: 'top',
      font: { color: '#ccc' },
      bgcolor: 'rgba(33, 37, 41, 0.8)',
      bordercolor: '#495057',
      borderwidth: 1
    },
    template: 'plotly_dark',
    plot_bgcolor: '#212529',
    paper_bgcolor: '#343a40',
    font: { color: '#ccc' },
    height: 400,
  };

  // Render based on showGenerationDemand flag
  if (showGenerationDemand) {
    return (
      <div>
        <div className="row">
          <Plot
            data={priceTraces}
            layout={priceLayout}
            config={{ scrollZoom: true, responsive: true }}
            style={{ width: '100%' }}
            useResizeHandler
          />
        </div>
        <div className="row">
          <Plot
            data={genTraces}
            layout={genLayout}
            config={{ scrollZoom: true, responsive: true }}
            style={{ width: '100%' }}
            useResizeHandler
          />
        </div>
      </div>
    );
  }

  return (
    <div className="row">
      <Plot
        data={priceTraces}
        layout={priceLayout}
        config={{ scrollZoom: true, responsive: true }}
        style={{ width: '100%' }}
        useResizeHandler
      />
    </div>
  );
}

export default ForecastChart;
