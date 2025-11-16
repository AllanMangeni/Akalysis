import React, { useState, useEffect } from 'react';
import './App.css';
import MetricsOverview from './components/MetricsOverview';
import CostBreakdown from './components/cost_breakdown';
import ResourceUsage from './components/resource_usage';
import ProviderComparison from './components/ProviderComparison';

function App() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Fetch dashboard data
  const fetchData = async () => {
    try {
      setLoading(true);
      // For now, we'll use mock data. Later this will fetch from the backend API
      const mockData = {
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
      };

      setDashboardData(mockData);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
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
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="App">
        <div className="error-container">
          <h2>Error Loading Data</h2>
          <p>{error}</p>
          <button onClick={handleRefresh} className="refresh-button">
            Retry
          </button>
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
