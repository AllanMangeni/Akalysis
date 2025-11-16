import React from 'react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import './resource_usage.css';

const ResourceUsage = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="resource-usage">
        <div className="empty-state">
          <p>=Ê No resource data available yet</p>
          <p className="empty-subtitle">Run the data collection scripts to populate this dashboard</p>
        </div>
      </div>
    );
  }

  // Process data for visualizations
  const processTimeSeriesData = () => {
    const grouped = data.reduce((acc, item) => {
      const date = item.date || new Date(item.timestamp).toLocaleDateString();
      if (!acc[date]) {
        acc[date] = {
          date,
          leases: 0,
          providers: new Set(),
          owners: new Set()
        };
      }
      acc[date].leases += 1;
      if (item.lease_id?.provider) {
        acc[date].providers.add(item.lease_id.provider);
      }
      if (item.lease_id?.owner) {
        acc[date].owners.add(item.lease_id.owner);
      }
      return acc;
    }, {});

    return Object.values(grouped).map(item => ({
      ...item,
      providers: item.providers.size,
      owners: item.owners.size
    })).slice(-30); // Last 30 days
  };

  const processProviderUtilization = () => {
    const grouped = data.reduce((acc, item) => {
      const provider = item.lease_id?.provider?.substring(0, 10) + '...' || 'Unknown';
      if (!acc[provider]) {
        acc[provider] = {
          name: provider,
          leases: 0,
          owners: new Set()
        };
      }
      acc[provider].leases += 1;
      if (item.lease_id?.owner) {
        acc[provider].owners.add(item.lease_id.owner);
      }
      return acc;
    }, {});

    return Object.values(grouped)
      .map(item => ({
        ...item,
        owners: item.owners.size
      }))
      .sort((a, b) => b.leases - a.leases)
      .slice(0, 8); // Top 8 providers
  };

  const timeSeriesData = processTimeSeriesData();
  const providerUtilization = processProviderUtilization();

  const totalLeases = data.length;
  const uniqueProviders = new Set(data.map(item => item.lease_id?.provider)).size;
  const uniqueOwners = new Set(data.map(item => item.lease_id?.owner)).size;

  return (
    <div className="resource-usage">
      {/* Resource Summary */}
      <div className="resource-summary">
        <div className="summary-card">
          <h4>Total Leases</h4>
          <p className="summary-value">{totalLeases}</p>
        </div>
        <div className="summary-card">
          <h4>Active Providers</h4>
          <p className="summary-value">{uniqueProviders}</p>
        </div>
        <div className="summary-card">
          <h4>Unique Deployers</h4>
          <p className="summary-value">{uniqueOwners}</p>
        </div>
        <div className="summary-card">
          <h4>Avg Leases/Provider</h4>
          <p className="summary-value">
            {(totalLeases / uniqueProviders).toFixed(1)}
          </p>
        </div>
      </div>

      {/* Charts */}
      <div className="chart-grid">
        {/* Time Series - Lease Activity */}
        <div className="chart-section">
          <h3>Lease Activity (Last 30 Days)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={timeSeriesData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={70}
              />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  background: 'white',
                  border: '1px solid #e0e0e0',
                  borderRadius: '8px',
                  padding: '10px'
                }}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="leases"
                stroke="#4CAF50"
                fill="#4CAF50"
                fillOpacity={0.6}
                name="Active Leases"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Provider Utilization */}
        <div className="chart-section">
          <h3>Provider Utilization</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={providerUtilization}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11 }}
                angle={-45}
                textAnchor="end"
                height={100}
              />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  background: 'white',
                  border: '1px solid #e0e0e0',
                  borderRadius: '8px',
                  padding: '10px'
                }}
              />
              <Legend />
              <Bar dataKey="leases" fill="#2196F3" name="Active Leases" />
              <Bar dataKey="owners" fill="#FF9800" name="Unique Deployers" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Network Activity */}
        <div className="chart-section full-width">
          <h3>Network Activity Trend</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={timeSeriesData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={70}
              />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  background: 'white',
                  border: '1px solid #e0e0e0',
                  borderRadius: '8px',
                  padding: '10px'
                }}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="providers"
                stackId="1"
                stroke="#00BCD4"
                fill="#00BCD4"
                fillOpacity={0.8}
                name="Active Providers"
              />
              <Area
                type="monotone"
                dataKey="owners"
                stackId="2"
                stroke="#9C27B0"
                fill="#9C27B0"
                fillOpacity={0.8}
                name="Active Deployers"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default ResourceUsage;
