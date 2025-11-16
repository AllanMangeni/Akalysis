import React from 'react';
import './MetricsOverview.css';

const MetricsOverview = ({ data }) => {
  if (!data) {
    return <div className="metrics-overview">Loading metrics...</div>;
  }

  const metrics = [
    {
      title: 'Active Leases',
      value: data.total_active_leases || 0,
      icon: '📊',
      color: '#4CAF50'
    },
    {
      title: 'Daily Cost',
      value: `$${(data.total_daily_cost_usd || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      subtitle: `Avg: $${(data.average_daily_cost_usd || 0).toFixed(2)}`,
      icon: '💰',
      color: '#2196F3'
    },
    {
      title: 'Monthly Cost',
      value: `$${(data.total_monthly_cost_usd || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      icon: '📈',
      color: '#FF9800'
    },
    {
      title: 'Unique Deployers',
      value: data.unique_owners || 0,
      icon: '👥',
      color: '#9C27B0'
    },
    {
      title: 'Active Providers',
      value: data.unique_providers || 0,
      icon: '🏢',
      color: '#00BCD4'
    }
  ];

  return (
    <div className="metrics-overview">
      {metrics.map((metric, index) => (
        <div key={index} className="metric-card" style={{ borderTopColor: metric.color }}>
          <div className="metric-icon" style={{ backgroundColor: `${metric.color}20` }}>
            {metric.icon}
          </div>
          <div className="metric-content">
            <h3 className="metric-title">{metric.title}</h3>
            <p className="metric-value" style={{ color: metric.color }}>
              {metric.value}
            </p>
            {metric.subtitle && (
              <p className="metric-subtitle">{metric.subtitle}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default MetricsOverview;
