import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import MetricsOverview from './components/MetricsOverview';
import CostBreakdown from './components/cost_breakdown';
import ResourceUsage from './components/resource_usage';
import ProviderComparison from './components/ProviderComparison';

// API configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function App() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [apiStatus, setApiStatus] = useState('checking');

  // Fetch dashboard data from API
  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch data from API
      const response = await axios.get(`${API_BASE_URL}/api/dashboard`, {
        timeout: 10000 // 10 second timeout
      });

      setDashboardData(response.data);
      setLastUpdated(new Date());
      setApiStatus('connected');
    } catch (err) {
      console.error('Error fetching dashboard data:', err);

      // Provide helpful error messages
      let errorMessage = 'Failed to fetch data from API server';

      if (err.code === 'ECONNABORTED') {
        errorMessage = 'Request timeout - API server might be slow or unresponsive';
      } else if (err.code === 'ERR_NETWORK' || err.message.includes('Network Error')) {
        errorMessage = 'Cannot connect to API server. Make sure the API server is running at ' + API_BASE_URL;
      } else if (err.response) {
        // Server responded with error
        errorMessage = `API Error: ${err.response.status} - ${err.response.data?.error || err.response.statusText}`;
      }

      setError(errorMessage);
      setApiStatus('disconnected');

      // Use fallback mock data if API is unavailable
      if (!dashboardData) {
        setDashboardData({
          summary: {
            total_active_leases: 0,
            total_daily_cost_usd: 0,
            total_monthly_cost_usd: 0,
            average_daily_cost_usd: 0,
            unique_owners: 0,
            unique_providers: 0
          },
          costs: [],
          resources: [],
          providers: []
        });
      }
    } finally {
      setLoading(false);
    }
  };

  // Check API health on mount
  const checkApiHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/health`, {
        timeout: 5000
      });

      if (response.data.status === 'healthy') {
        setApiStatus('connected');
      }
    } catch (err) {
      setApiStatus('disconnected');
      console.warn('API health check failed:', err.message);
    }
  };

  useEffect(() => {
    // Check API health first
    checkApiHealth();

    // Fetch data
    fetchData();

    // Auto-refresh every 5 minutes
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    fetchData();
  };

  if (loading && !dashboardData) {
    return (
      <div className="App">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading Akash Network data...</p>
          <p className="loading-subtitle">Connecting to API at {API_BASE_URL}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <div className="header-left">
            <h1>Akalysis</h1>
            <p className="subtitle">Akash Network Resource & Cost Analytics</p>
          </div>
          <div className="header-right">
            {apiStatus === 'disconnected' && (
              <span className="api-status disconnected" title="API server is not responding">
                ⚠️ API Offline
              </span>
            )}
            {apiStatus === 'connected' && (
              <span className="api-status connected" title="Connected to API server">
                ✓ API Online
              </span>
            )}
            <button onClick={handleRefresh} className="refresh-button" disabled={loading}>
              {loading ? 'Refreshing...' : '🔄 Refresh'}
            </button>
            {lastUpdated && (
              <span className="last-updated">
                Last updated: {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <span className="error-icon">⚠️</span>
          <span className="error-message">{error}</span>
          <button onClick={handleRefresh} className="error-retry-button">
            Retry
          </button>
        </div>
      )}

      <main className="dashboard-main">
        <section className="metrics-section">
          <MetricsOverview data={dashboardData?.summary} />
        </section>

        <section className="charts-section">
          <div className="chart-container">
            <h2>Cost Breakdown</h2>
            <CostBreakdown data={dashboardData?.costs} />
          </div>

          <div className="chart-container">
            <h2>Resource Usage</h2>
            <ResourceUsage data={dashboardData?.resources} />
          </div>
        </section>

        <section className="providers-section">
          <h2>Provider Analysis</h2>
          <ProviderComparison data={dashboardData?.providers} />
        </section>
      </main>

      <footer className="App-footer">
        <p>
          Monitoring {dashboardData?.summary?.total_active_leases || 0} active leases across{' '}
          {dashboardData?.summary?.unique_providers || 0} providers
        </p>
      </footer>
    </div>
  );
}

export default App;
