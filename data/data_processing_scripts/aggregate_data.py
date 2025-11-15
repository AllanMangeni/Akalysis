#!/usr/bin/env python3
"""
Aggregate collected data into time-based summaries

This script aggregates raw data into hourly, daily, weekly, and monthly summaries
for easier analysis and visualization.
"""

import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
from collections import defaultdict
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import Config, setup_logging
from loguru import logger

console = Console()


class DataAggregator:
    """Aggregates collected data into time-based summaries"""

    def __init__(self, config: Config):
        self.config = config
        self.data_path = Path(config.get('storage', 'file', 'base_path', default='./collected_data'))
        self.output_path = Path('./processed_data')
        self.output_path.mkdir(parents=True, exist_ok=True)

    def load_json_files(self, pattern: str) -> List[Dict]:
        """Load all JSON files matching a pattern"""
        files = sorted(self.data_path.glob(f"{pattern}_*.json"))
        data = []

        for file in files:
            try:
                with open(file, 'r') as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        data.extend(content)
                    else:
                        data.append(content)
            except Exception as e:
                logger.warning(f"Error loading {file}: {e}")

        logger.info(f"Loaded {len(data)} records from {len(files)} files")
        return data

    def aggregate_costs_by_time(self, costs: List[Dict], interval: str = 'hourly') -> Dict:
        """Aggregate costs by time interval"""
        aggregated = defaultdict(lambda: {
            'total_daily_usd': 0,
            'total_monthly_usd': 0,
            'lease_count': 0,
            'unique_owners': set(),
            'unique_providers': set(),
        })

        for cost in costs:
            try:
                timestamp = datetime.fromisoformat(cost['timestamp'])

                # Determine time bucket based on interval
                if interval == 'hourly':
                    bucket = timestamp.replace(minute=0, second=0, microsecond=0)
                elif interval == 'daily':
                    bucket = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                elif interval == 'weekly':
                    bucket = timestamp - timedelta(days=timestamp.weekday())
                    bucket = bucket.replace(hour=0, minute=0, second=0, microsecond=0)
                elif interval == 'monthly':
                    bucket = timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    logger.error(f"Unknown interval: {interval}")
                    continue

                bucket_key = bucket.isoformat()

                # Aggregate data
                aggregated[bucket_key]['total_daily_usd'] += cost['pricing']['daily_cost_usd']
                aggregated[bucket_key]['total_monthly_usd'] += cost['pricing']['monthly_cost_usd']
                aggregated[bucket_key]['lease_count'] += 1
                aggregated[bucket_key]['unique_owners'].add(cost['deployment_id']['owner'])
                aggregated[bucket_key]['unique_providers'].add(cost['lease_id']['provider'])

            except Exception as e:
                logger.warning(f"Error aggregating cost: {e}")
                continue

        # Convert sets to counts
        result = {}
        for bucket, data in aggregated.items():
            result[bucket] = {
                'timestamp': bucket,
                'total_daily_usd': data['total_daily_usd'],
                'total_monthly_usd': data['total_monthly_usd'],
                'average_daily_usd': data['total_daily_usd'] / data['lease_count'] if data['lease_count'] > 0 else 0,
                'lease_count': data['lease_count'],
                'unique_owners': len(data['unique_owners']),
                'unique_providers': len(data['unique_providers']),
            }

        return dict(sorted(result.items()))

    def aggregate_resources_by_time(self, resources: List[Dict], interval: str = 'hourly') -> Dict:
        """Aggregate resource usage by time interval"""
        aggregated = defaultdict(lambda: {
            'total_leases': 0,
            'unique_providers': set(),
            'unique_owners': set(),
        })

        for resource in resources:
            try:
                timestamp = datetime.fromisoformat(resource['timestamp'])

                # Determine time bucket
                if interval == 'hourly':
                    bucket = timestamp.replace(minute=0, second=0, microsecond=0)
                elif interval == 'daily':
                    bucket = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                elif interval == 'weekly':
                    bucket = timestamp - timedelta(days=timestamp.weekday())
                    bucket = bucket.replace(hour=0, minute=0, second=0, microsecond=0)
                elif interval == 'monthly':
                    bucket = timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    continue

                bucket_key = bucket.isoformat()

                # Aggregate data
                aggregated[bucket_key]['total_leases'] += 1
                aggregated[bucket_key]['unique_providers'].add(resource['lease_id']['provider'])
                aggregated[bucket_key]['unique_owners'].add(resource['lease_id']['owner'])

            except Exception as e:
                logger.warning(f"Error aggregating resource: {e}")
                continue

        # Convert sets to counts
        result = {}
        for bucket, data in aggregated.items():
            result[bucket] = {
                'timestamp': bucket,
                'total_leases': data['total_leases'],
                'unique_providers': len(data['unique_providers']),
                'unique_owners': len(data['unique_owners']),
            }

        return dict(sorted(result.items()))

    def calculate_provider_statistics(self, costs: List[Dict]) -> Dict:
        """Calculate per-provider statistics"""
        provider_stats = defaultdict(lambda: {
            'total_leases': 0,
            'total_daily_usd': 0,
            'total_monthly_usd': 0,
            'unique_owners': set(),
            'first_seen': None,
            'last_seen': None,
        })

        for cost in costs:
            try:
                provider = cost['lease_id']['provider']
                timestamp = datetime.fromisoformat(cost['timestamp'])

                provider_stats[provider]['total_leases'] += 1
                provider_stats[provider]['total_daily_usd'] += cost['pricing']['daily_cost_usd']
                provider_stats[provider]['total_monthly_usd'] += cost['pricing']['monthly_cost_usd']
                provider_stats[provider]['unique_owners'].add(cost['deployment_id']['owner'])

                # Track first and last seen
                if not provider_stats[provider]['first_seen'] or timestamp < provider_stats[provider]['first_seen']:
                    provider_stats[provider]['first_seen'] = timestamp
                if not provider_stats[provider]['last_seen'] or timestamp > provider_stats[provider]['last_seen']:
                    provider_stats[provider]['last_seen'] = timestamp

            except Exception as e:
                logger.warning(f"Error calculating provider stats: {e}")
                continue

        # Convert to serializable format
        result = {}
        for provider, stats in provider_stats.items():
            result[provider] = {
                'provider_address': provider,
                'total_leases': stats['total_leases'],
                'total_daily_usd': stats['total_daily_usd'],
                'total_monthly_usd': stats['total_monthly_usd'],
                'average_daily_usd': stats['total_daily_usd'] / stats['total_leases'] if stats['total_leases'] > 0 else 0,
                'unique_owners': len(stats['unique_owners']),
                'first_seen': stats['first_seen'].isoformat() if stats['first_seen'] else None,
                'last_seen': stats['last_seen'].isoformat() if stats['last_seen'] else None,
            }

        # Sort by total revenue
        result = dict(sorted(result.items(), key=lambda x: x[1]['total_monthly_usd'], reverse=True))

        return result

    def save_aggregated_data(self, data: Dict, filename: str):
        """Save aggregated data to JSON file"""
        output_file = self.output_path / filename

        try:
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved aggregated data to {output_file}")
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def run(self):
        """Run the aggregation process"""
        console.print("\n[bold blue]Akash Network - Data Aggregator[/bold blue]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Load cost data
            task1 = progress.add_task("Loading cost data...", total=None)
            costs = self.load_json_files('deployment_costs')
            progress.update(task1, completed=True)

            if costs:
                # Aggregate costs by different time intervals
                task2 = progress.add_task("Aggregating costs...", total=None)
                for interval in ['hourly', 'daily', 'weekly', 'monthly']:
                    aggregated = self.aggregate_costs_by_time(costs, interval)
                    self.save_aggregated_data(aggregated, f'costs_{interval}.json')
                progress.update(task2, completed=True)

                # Calculate provider statistics
                task3 = progress.add_task("Calculating provider stats...", total=None)
                provider_stats = self.calculate_provider_statistics(costs)
                self.save_aggregated_data(provider_stats, 'provider_statistics.json')
                progress.update(task3, completed=True)

            # Load resource data
            task4 = progress.add_task("Loading resource data...", total=None)
            resources = self.load_json_files('lease_resources')
            progress.update(task4, completed=True)

            if resources:
                # Aggregate resources by different time intervals
                task5 = progress.add_task("Aggregating resources...", total=None)
                for interval in ['hourly', 'daily', 'weekly', 'monthly']:
                    aggregated = self.aggregate_resources_by_time(resources, interval)
                    self.save_aggregated_data(aggregated, f'resources_{interval}.json')
                progress.update(task5, completed=True)

        console.print("\n[bold green]Aggregation Complete![/bold green]\n")
        console.print(f"Processed {len(costs)} cost records")
        console.print(f"Processed {len(resources)} resource records")
        console.print(f"Output saved to: {self.output_path}\n")


@click.command()
@click.option('--config', default='config.yaml', help='Path to configuration file')
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
def main(config, verbose):
    """Aggregate collected data into time-based summaries"""

    # Load configuration
    cfg = Config(config)

    # Setup logging
    if verbose:
        cfg.config['logging']['level'] = 'DEBUG'
    setup_logging(cfg)

    # Run aggregator
    aggregator = DataAggregator(cfg)
    aggregator.run()


if __name__ == '__main__':
    main()
