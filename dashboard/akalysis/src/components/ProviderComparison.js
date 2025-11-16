import React, { useState } from 'react';
import './ProviderComparison.css';

const ProviderComparison = ({ data }) => {
  const [sortField, setSortField] = useState('cost');
  const [sortDirection, setSortDirection] = useState('desc');

  if (!data || data.length === 0) {
    return (
      <div className="provider-comparison">
        <div className="empty-state">
          <p>🏢 No provider data available yet</p>
          <p className="empty-subtitle">Run the data collection scripts to populate this dashboard</p>
        </div>
      </div>
    );
  }

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedData = [...data].sort((a, b) => {
    let aVal, bVal;

    switch (sortField) {
      case 'provider':
        aVal = a.provider_address || a.name || '';
        bVal = b.provider_address || b.name || '';
        break;
      case 'leases':
        aVal = a.lease_count || a.total_leases || 0;
        bVal = b.lease_count || b.total_leases || 0;
        break;
      case 'cost':
        aVal = a.total_monthly_usd || 0;
        bVal = b.total_monthly_usd || 0;
        break;
      case 'avgCost':
        aVal = a.average_daily_usd || 0;
        bVal = b.average_daily_usd || 0;
        break;
      case 'owners':
        aVal = a.unique_owners || 0;
        bVal = b.unique_owners || 0;
        break;
      default:
        return 0;
    }

    if (sortDirection === 'asc') {
      return aVal > bVal ? 1 : -1;
    } else {
      return aVal < bVal ? 1 : -1;
    }
  });

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <span className="sort-icon">⇅</span>;
    return sortDirection === 'asc' ? <span className="sort-icon">↑</span> : <span className="sort-icon">↓</span>;
  };

  return (
    <div className="provider-comparison">
      <div className="table-container">
        <table className="provider-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('provider')}>
                Provider <SortIcon field="provider" />
              </th>
              <th onClick={() => handleSort('leases')}>
                Active Leases <SortIcon field="leases" />
              </th>
              <th onClick={() => handleSort('cost')}>
                Monthly Revenue <SortIcon field="cost" />
              </th>
              <th onClick={() => handleSort('avgCost')}>
                Avg Daily Cost <SortIcon field="avgCost" />
              </th>
              <th onClick={() => handleSort('owners')}>
                Unique Deployers <SortIcon field="owners" />
              </th>
              <th>Performance Score</th>
            </tr>
          </thead>
          <tbody>
            {sortedData.map((provider, index) => {
              const leaseCount = provider.lease_count || provider.total_leases || 0;
              const monthlyRevenue = provider.total_monthly_usd || 0;
              const avgDaily = provider.average_daily_usd || 0;
              const uniqueOwners = provider.unique_owners || 0;
              const providerAddress = provider.provider_address || provider.name || 'Unknown';

              // Calculate a simple performance score based on metrics
              const performanceScore = Math.min(
                100,
                Math.round((leaseCount * 2 + uniqueOwners * 5 + monthlyRevenue / 100) / 3)
              );

              return (
                <tr key={index}>
                  <td className="provider-cell">
                    <div className="provider-info">
                      <span className="provider-icon">🏢</span>
                      <span className="provider-name" title={providerAddress}>
                        {providerAddress.substring(0, 12)}...
                      </span>
                    </div>
                  </td>
                  <td className="number-cell">
                    <span className="badge badge-primary">{leaseCount}</span>
                  </td>
                  <td className="number-cell">
                    <span className="revenue-value">
                      ${monthlyRevenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </td>
                  <td className="number-cell">
                    ${avgDaily.toFixed(2)}
                  </td>
                  <td className="number-cell">
                    <span className="badge badge-secondary">{uniqueOwners}</span>
                  </td>
                  <td className="score-cell">
                    <div className="score-bar-container">
                      <div
                        className="score-bar"
                        style={{
                          width: `${performanceScore}%`,
                          backgroundColor: performanceScore > 70 ? '#4CAF50' : performanceScore > 40 ? '#FF9800' : '#F44336'
                        }}
                      />
                      <span className="score-text">{performanceScore}%</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Summary Cards */}
      <div className="provider-summary">
        <div className="summary-stat">
          <h4>Total Providers</h4>
          <p className="stat-value">{data.length}</p>
        </div>
        <div className="summary-stat">
          <h4>Total Monthly Revenue</h4>
          <p className="stat-value">
            ${data.reduce((sum, p) => sum + (p.total_monthly_usd || 0), 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </p>
        </div>
        <div className="summary-stat">
          <h4>Total Active Leases</h4>
          <p className="stat-value">
            {data.reduce((sum, p) => sum + (p.lease_count || p.total_leases || 0), 0)}
          </p>
        </div>
        <div className="summary-stat">
          <h4>Avg Provider Load</h4>
          <p className="stat-value">
            {(data.reduce((sum, p) => sum + (p.lease_count || p.total_leases || 0), 0) / data.length).toFixed(1)} leases
          </p>
        </div>
      </div>
    </div>
  );
};

export default ProviderComparison;
