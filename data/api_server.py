#!/usr/bin/env python3
"""
Simple API server to serve processed Akash Network data to the dashboard

This Flask-based API serves the collected and processed data as JSON
endpoints for the frontend dashboard to consume.
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
import json
from datetime import datetime
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Configure paths
DATA_DIR = Path('./collected_data')
PROCESSED_DIR = Path('./processed_data')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_latest_file(directory: Path, pattern: str):
    """Load the most recent file matching the pattern"""
    try:
        files = sorted(directory.glob(f"{pattern}_*.json"))
        if not files:
            logger.warning(f"No files found matching {pattern}")
            return None

        latest_file = files[-1]
        logger.info(f"Loading {latest_file}")

        with open(latest_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading file {pattern}: {e}")
        return None


def load_processed_file(filename: str):
    """Load a processed data file"""
    try:
        file_path = PROCESSED_DIR / filename
        if not file_path.exists():
            logger.warning(f"Processed file not found: {filename}")
            return None

        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading processed file {filename}: {e}")
        return None


@app.route('/')
def index():
    """API index with available endpoints"""
    return jsonify({
        'name': 'Akalysis API',
        'version': '1.0.0',
        'description': 'Akash Network Monitoring API',
        'endpoints': {
            '/api/dashboard': 'Complete dashboard data',
            '/api/costs': 'Cost data',
            '/api/resources': 'Resource usage data',
            '/api/providers': 'Provider statistics',
            '/api/summary': 'Summary statistics',
            '/api/health': 'Health check'
        }
    })


@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'data_available': {
            'costs': DATA_DIR.glob('deployment_costs_*.json').__next__() is not None,
            'resources': DATA_DIR.glob('lease_resources_*.json').__next__() is not None,
            'summary': (PROCESSED_DIR / 'dashboard_summary.json').exists()
        }
    })


@app.route('/api/dashboard')
def get_dashboard_data():
    """Get complete dashboard data"""
    try:
        # Load all data
        costs = load_latest_file(DATA_DIR, 'deployment_costs') or []
        resources = load_latest_file(DATA_DIR, 'lease_resources') or []
        summary = load_processed_file('dashboard_summary.json') or {}
        providers = load_processed_file('provider_statistics.json') or {}

        # Ensure costs and resources are lists
        if isinstance(costs, dict):
            costs = [costs]
        if isinstance(resources, dict):
            resources = [resources]

        # Convert provider dict to list
        provider_list = []
        if isinstance(providers, dict):
            provider_list = list(providers.values())

        response = {
            'timestamp': datetime.now().isoformat(),
            'summary': summary.get('summary', {
                'total_active_leases': len(costs),
                'total_daily_cost_usd': sum(c.get('pricing', {}).get('daily_cost_usd', 0) for c in costs),
                'total_monthly_cost_usd': sum(c.get('pricing', {}).get('monthly_cost_usd', 0) for c in costs),
                'average_daily_cost_usd': sum(c.get('pricing', {}).get('daily_cost_usd', 0) for c in costs) / len(costs) if costs else 0,
                'unique_owners': len(set(c.get('deployment_id', {}).get('owner', '') for c in costs if c.get('deployment_id'))),
                'unique_providers': len(set(c.get('lease_id', {}).get('provider', '') for c in costs if c.get('lease_id')))
            }),
            'costs': costs,
            'resources': resources,
            'providers': provider_list[:20]  # Limit to top 20 providers
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error generating dashboard data: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/costs')
def get_costs():
    """Get deployment cost data"""
    try:
        costs = load_latest_file(DATA_DIR, 'deployment_costs') or []
        if isinstance(costs, dict):
            costs = [costs]

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'data': costs,
            'count': len(costs)
        })
    except Exception as e:
        logger.error(f"Error getting costs: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/resources')
def get_resources():
    """Get resource usage data"""
    try:
        resources = load_latest_file(DATA_DIR, 'lease_resources') or []
        if isinstance(resources, dict):
            resources = [resources]

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'data': resources,
            'count': len(resources)
        })
    except Exception as e:
        logger.error(f"Error getting resources: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/providers')
def get_providers():
    """Get provider statistics"""
    try:
        providers = load_processed_file('provider_statistics.json') or {}

        # Convert to list
        provider_list = []
        if isinstance(providers, dict):
            provider_list = list(providers.values())

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'data': provider_list,
            'count': len(provider_list)
        })
    except Exception as e:
        logger.error(f"Error getting providers: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/summary')
def get_summary():
    """Get summary statistics"""
    try:
        summary = load_processed_file('dashboard_summary.json') or {}

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'data': summary
        })
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/<interval>')
def get_stats(interval):
    """Get aggregated statistics by interval (hourly, daily, weekly, monthly)"""
    try:
        if interval not in ['hourly', 'daily', 'weekly', 'monthly']:
            return jsonify({'error': 'Invalid interval. Use: hourly, daily, weekly, or monthly'}), 400

        costs_file = f'costs_{interval}.json'
        resources_file = f'resources_{interval}.json'

        costs = load_processed_file(costs_file) or {}
        resources = load_processed_file(resources_file) or {}

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'interval': interval,
            'costs': costs,
            'resources': resources
        })
    except Exception as e:
        logger.error(f"Error getting stats for {interval}: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Create directories if they don't exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("""
╔═══════════════════════════════════════════════════════════╗
║              Akalysis API Server Starting                 ║
║                                                            ║
║  API will be available at: http://localhost:5000          ║
║  Documentation: http://localhost:5000/                    ║
║                                                            ║
║  Data directories:                                        ║
║    - Raw data: ./collected_data                          ║
║    - Processed: ./processed_data                         ║
╚═══════════════════════════════════════════════════════════╝
    """)

    app.run(debug=True, host='0.0.0.0', port=5000)
