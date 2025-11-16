import React from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import './cost_breakdown.css';

const COLORS = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#00BCD4', '#F44336'];

const CostBreakdown = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="cost-breakdown">
        <div className="empty-state">
          <p>=Ê No cost data available yet</p>
          <p className="empty-subtitle">Run the data collection scripts to populate this dashboard</p>
        </div>
      </div>
    );
  }

  // Process data for charts
  const processTimeSeriesData = () => {
    // Group by date
    const grouped = data.reduce((acc, item) => {
      const date = item.date || new Date(item.timestamp).toLocaleDateString();
      if (!acc[date]) {
        acc[date] = {
          date,
          totalCost: 0,
          count: 0
        };
      }
      acc[date].totalCost += item.pricing?.daily_cost_usd || 0;
      acc[date].count += 1;
      return acc;
    }, {});

    return Object.values(grouped).slice(-30); // Last 30 days
  };

  const processProviderData = () => {
    // Group by provider
    const grouped = data.reduce((acc, item) => {
      const provider = item.lease_id?.provider?.substring(0, 10) + '...' || 'Unknown';
      if (!acc[provider]) {
        acc[provider] = {
          name: provider,
          cost: 0,
          leases: 0
        };
      }
      acc[provider].cost += item.pricing?.daily_cost_usd || 0;
      acc[provider].leases += 1;
      return acc;
    }, {});

    return Object.values(grouped)
      .sort((a, b) => b.cost - a.cost)
      .slice(0, 6); // Top 6 providers
  };

  const timeSeriesData = processTimeSeriesData();
  const providerData = processProviderData();

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p className="label">{label}</p>
          <p className="value" style={{ color: payload[0].color }}>
            ${payload[0].value.toFixed(2)}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="cost-breakdown">
      <div className="chart-grid">
        {/* Time Series Chart */}
        <div className="chart-section">
          <h3>Cost Trend (Last 30 Days)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={timeSeriesData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={70}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => `$${value.toFixed(0)}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line
                type="monotone"
                dataKey="totalCost"
                stroke="#2196F3"
                strokeWidth={2}
                name="Daily Cost (USD)"
                dot={{ fill: '#2196F3', r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Provider Distribution */}
        <div className="chart-section">
          <h3>Top Providers by Cost</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={providerData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                type="number"
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => `$${value.toFixed(0)}`}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 11 }}
                width={100}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="cost" fill="#4CAF50" name="Daily Cost (USD)">
                {providerData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Provider Pie Chart */}
        <div className="chart-section">
          <h3>Provider Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={providerData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="cost"
              >
                {providerData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Cost Summary Stats */}
        <div className="chart-section cost-stats">
          <h3>Cost Statistics</h3>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-label">Total Deployments</span>
              <span className="stat-value">{data.length}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Avg Cost per Deployment</span>
              <span className="stat-value">
                ${(data.reduce((sum, item) => sum + (item.pricing?.daily_cost_usd || 0), 0) / data.length).toFixed(2)}
              </span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Highest Daily Cost</span>
              <span className="stat-value">
                ${Math.max(...data.map(item => item.pricing?.daily_cost_usd || 0)).toFixed(2)}
              </span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Lowest Daily Cost</span>
              <span className="stat-value">
                ${Math.min(...data.map(item => item.pricing?.daily_cost_usd || 0)).toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CostBreakdown;
