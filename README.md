# Akalysis

**Resource Monitoring & Deployment Cost Analytics for Akash Network**

Akalysis is a comprehensive analytics platform for the Akash Network, providing real-time monitoring, cost analysis, and predictive insights for deployments on the decentralized cloud marketplace.

## Features

### Data Collection & Processing
- **Automated Data Collection** - Fetch deployment costs, resource usage, and provider statistics from Akash Network API
- **Time-Series Aggregation** - Hourly, daily, weekly, and monthly data aggregations
- **Data Cleaning & Enrichment** - Automatic duplicate removal, outlier detection, and data enrichment
- **Provider Analytics** - Per-provider statistics, revenue tracking, and performance metrics

### Interactive Dashboard
- **Real-Time Metrics** - Active leases, daily/monthly costs, unique deployers, and providers
- **Cost Visualization** - Interactive charts showing cost trends, provider distribution, and breakdowns
- **Resource Monitoring** - Lease activity, provider utilization, and network health metrics
- **Provider Comparison** - Sortable table with performance scores and detailed statistics
- **Auto-Refresh** - Dashboard updates every 5 minutes automatically

### Unique Advantages Over Existing Tools
Unlike Akash Console and Akash Stats, Akalysis offers:
- **Historical Trend Analysis** - Long-term cost and usage pattern analysis
- **Cost Forecasting** - Predictive models for budget planning (coming soon)
- **Provider Intelligence** - Performance scoring and recommendations (coming soon)
- **Cost Optimization** - Automated suggestions for cost savings (coming soon)
- **Developer API** - Programmatic access to all analytics data
- **Customizable Dashboards** - Build your own views and reports

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Installation

```bash
# Clone the repository
git clone https://github.com/AllanMangeni/Akalysis.git
cd Akalysis

# Install Python dependencies
cd data
pip install -r requirements.txt

# Install frontend dependencies
cd ../dashboard/akalysis
npm install
```

### Running the System

**1. Start the Data Collection (Terminal 1)**
```bash
cd data

# Run data collection scripts
python data_collection_scripts/collect_deployment_costs.py
python data_collection_scripts/collect_resource_usage.py

# Process the collected data
python data_processing_scripts/preprocess_data.py
python data_processing_scripts/aggregate_data.py
```

**2. Start the API Server (Terminal 2)**
```bash
cd data
python api_server.py
```
API will be available at `http://localhost:5000`

**3. Start the Dashboard (Terminal 3)**
```bash
cd dashboard/akalysis
npm start
```
Dashboard will open at `http://localhost:3000`

## Project Structure

```
Akalysis/
├── data/                           # Backend data collection & processing
│   ├── data_collection_scripts/    # Scripts to fetch data from Akash API
│   │   ├── collect_deployment_costs.py
│   │   └── collect_resource_usage.py
│   ├── data_processing_scripts/    # Data cleaning and aggregation
│   │   ├── preprocess_data.py
│   │   └── aggregate_data.py
│   ├── api_server.py              # Flask API server
│   ├── utils.py                   # Shared utilities
│   ├── config.yaml                # Configuration
│   ├── requirements.txt           # Python dependencies
│   └── README.md                  # Detailed data docs
│
├── dashboard/akalysis/            # React frontend dashboard
│   ├── src/
│   │   ├── components/           # React components
│   │   │   ├── MetricsOverview.js
│   │   │   ├── cost_breakdown.js
│   │   │   ├── resource_usage.js
│   │   │   └── ProviderComparison.js
│   │   ├── App.js                # Main app component
│   │   └── App.css               # Styling
│   └── package.json              # Node dependencies
│
└── README.md                      # This file
```

## API Endpoints

The API server provides the following endpoints:

- `GET /` - API documentation
- `GET /api/health` - Health check
- `GET /api/dashboard` - Complete dashboard data
- `GET /api/costs` - Deployment cost data
- `GET /api/resources` - Resource usage data
- `GET /api/providers` - Provider statistics
- `GET /api/summary` - Summary statistics
- `GET /api/stats/<interval>` - Aggregated stats (hourly/daily/weekly/monthly)

## Configuration

Edit `data/config.yaml` to customize:
- API endpoints and RPC nodes
- Data collection intervals
- Storage backend (JSON, CSV, MongoDB, PostgreSQL)
- Rate limiting settings
- Processing options

Copy `data/.env.example` to `data/.env` and configure:
- Database credentials
- Alert webhooks
- Custom API settings

## Development

### Data Collection Scripts
Create new collectors in `data/data_collection_scripts/`:
1. Import utilities from `utils.py`
2. Use `AkashAPIClient` for API calls
3. Use `DataStorage` for saving data
4. Add comprehensive logging

### Frontend Components
Add new dashboard components in `dashboard/akalysis/src/components/`:
1. Import Recharts for visualizations
2. Use consistent styling patterns
3. Handle empty states
4. Add responsive design

## Roadmap

### Phase 3: Advanced Features (Upcoming)
- [ ] Cost forecasting with ML models
- [ ] Budget alerts and notifications
- [ ] Provider reputation scoring
- [ ] What-if analysis tool
- [ ] Cost optimization recommendations
- [ ] Anomaly detection

### Phase 4: Developer Tools
- [ ] REST API documentation (Swagger)
- [ ] CLI tool for quick queries
- [ ] Webhooks for cost alerts
- [ ] SDK for popular languages
- [ ] CI/CD integration

### Phase 5: Deployment
- [ ] Deploy on Akash Network (dogfooding!)
- [ ] Docker containers
- [ ] Kubernetes manifests
- [ ] Monitoring and logging setup

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Contact: [Your contact info]

## Acknowledgments

Built for the Akash Network community. Powered by:
- React & Recharts for the frontend
- Flask for the API
- Python for data processing
- Akash Network REST API
