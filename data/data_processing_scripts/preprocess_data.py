#!/usr/bin/env python3
"""
Preprocess and clean collected data

This script cleans raw data, removes duplicates, handles missing values,
and prepares it for frontend consumption.
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import Config, setup_logging
from loguru import logger

console = Console()


class DataPreprocessor:
    """Preprocesses and cleans collected data"""

    def __init__(self, config: Config):
        self.config = config
        self.data_path = Path(config.get('storage', 'file', 'base_path', default='./collected_data'))
        self.output_path = Path('./processed_data')
        self.output_path.mkdir(parents=True, exist_ok=True)

        self.cleanup_config = config.get('processing', 'cleanup', default={})
        self.remove_duplicates = self.cleanup_config.get('remove_duplicates', True)
        self.fill_missing = self.cleanup_config.get('fill_missing_values', True)
        self.detect_outliers = self.cleanup_config.get('outlier_detection', True)

    def load_latest_data(self, pattern: str) -> List[Dict]:
        """Load the most recent data files"""
        files = sorted(self.data_path.glob(f"{pattern}_*.json"))
        data = []

        # Load recent files (last 10)
        for file in files[-10:]:
            try:
                with open(file, 'r') as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        data.extend(content)
                    else:
                        data.append(content)
            except Exception as e:
                logger.warning(f"Error loading {file}: {e}")

        logger.info(f"Loaded {len(data)} records from {len(files[-10:])} recent files")
        return data

    def remove_duplicate_records(self, data: List[Dict], key_fields: List[str]) -> List[Dict]:
        """Remove duplicate records based on key fields"""
        if not self.remove_duplicates:
            return data

        seen = set()
        unique_data = []

        for record in data:
            try:
                # Create a key from specified fields
                key_parts = []
                for field in key_fields:
                    if '.' in field:
                        # Handle nested fields
                        parts = field.split('.')
                        value = record
                        for part in parts:
                            value = value.get(part, '')
                        key_parts.append(str(value))
                    else:
                        key_parts.append(str(record.get(field, '')))

                key = '|'.join(key_parts)

                if key not in seen:
                    seen.add(key)
                    unique_data.append(record)

            except Exception as e:
                logger.warning(f"Error processing record for duplicate detection: {e}")
                unique_data.append(record)

        removed = len(data) - len(unique_data)
        if removed > 0:
            logger.info(f"Removed {removed} duplicate records")

        return unique_data

    def fill_missing_values(self, data: List[Dict]) -> List[Dict]:
        """Fill missing values with defaults"""
        if not self.fill_missing:
            return data

        for record in data:
            try:
                # Fill missing timestamps
                if 'timestamp' not in record or not record['timestamp']:
                    record['timestamp'] = datetime.now().isoformat()

                # Fill missing numeric values with 0
                if 'pricing' in record:
                    pricing = record['pricing']
                    for key in ['daily_cost_usd', 'monthly_cost_usd', 'akt_usd_rate']:
                        if key not in pricing or pricing[key] is None:
                            pricing[key] = 0

            except Exception as e:
                logger.warning(f"Error filling missing values: {e}")

        return data

    def detect_and_flag_outliers(self, data: List[Dict]) -> List[Dict]:
        """Detect and flag statistical outliers in cost data"""
        if not self.detect_outliers or len(data) < 10:
            return data

        try:
            # Calculate statistics for daily costs
            daily_costs = []
            for record in data:
                if 'pricing' in record and 'daily_cost_usd' in record['pricing']:
                    cost = record['pricing']['daily_cost_usd']
                    if cost > 0:
                        daily_costs.append(cost)

            if not daily_costs:
                return data

            # Calculate mean and standard deviation
            mean = sum(daily_costs) / len(daily_costs)
            variance = sum((x - mean) ** 2 for x in daily_costs) / len(daily_costs)
            std_dev = variance ** 0.5

            # Flag outliers (3 standard deviations from mean)
            threshold_low = mean - (3 * std_dev)
            threshold_high = mean + (3 * std_dev)

            outlier_count = 0
            for record in data:
                if 'pricing' in record and 'daily_cost_usd' in record['pricing']:
                    cost = record['pricing']['daily_cost_usd']
                    if cost < threshold_low or cost > threshold_high:
                        record['is_outlier'] = True
                        outlier_count += 1
                    else:
                        record['is_outlier'] = False

            if outlier_count > 0:
                logger.info(f"Flagged {outlier_count} outlier records")

        except Exception as e:
            logger.warning(f"Error detecting outliers: {e}")

        return data

    def enrich_data(self, data: List[Dict]) -> List[Dict]:
        """Enrich data with calculated fields"""
        for record in data:
            try:
                # Add human-readable timestamp
                if 'timestamp' in record:
                    ts = datetime.fromisoformat(record['timestamp'])
                    record['timestamp_readable'] = ts.strftime('%Y-%m-%d %H:%M:%S')
                    record['date'] = ts.strftime('%Y-%m-%d')
                    record['hour'] = ts.hour

                # Add cost per day/week/month if not present
                if 'pricing' in record:
                    pricing = record['pricing']
                    if 'daily_cost_usd' in pricing:
                        pricing['weekly_cost_usd'] = pricing['daily_cost_usd'] * 7
                        pricing['yearly_cost_usd'] = pricing['daily_cost_usd'] * 365

            except Exception as e:
                logger.warning(f"Error enriching data: {e}")

        return data

    def create_summary_statistics(self, costs: List[Dict]) -> Dict:
        """Create summary statistics for the dashboard"""
        if not costs:
            return {}

        try:
            total_leases = len(costs)
            total_daily = sum(c.get('pricing', {}).get('daily_cost_usd', 0) for c in costs)
            total_monthly = sum(c.get('pricing', {}).get('monthly_cost_usd', 0) for c in costs)
            avg_daily = total_daily / total_leases if total_leases > 0 else 0

            # Get unique owners and providers
            unique_owners = len(set(c.get('deployment_id', {}).get('owner', '') for c in costs if c.get('deployment_id')))
            unique_providers = len(set(c.get('lease_id', {}).get('provider', '') for c in costs if c.get('lease_id')))

            # Get date range
            timestamps = [datetime.fromisoformat(c['timestamp']) for c in costs if 'timestamp' in c]
            if timestamps:
                min_date = min(timestamps).isoformat()
                max_date = max(timestamps).isoformat()
            else:
                min_date = max_date = datetime.now().isoformat()

            return {
                'generated_at': datetime.now().isoformat(),
                'data_range': {
                    'start': min_date,
                    'end': max_date,
                },
                'summary': {
                    'total_active_leases': total_leases,
                    'total_daily_cost_usd': total_daily,
                    'total_monthly_cost_usd': total_monthly,
                    'average_daily_cost_usd': avg_daily,
                    'unique_owners': unique_owners,
                    'unique_providers': unique_providers,
                },
            }

        except Exception as e:
            logger.error(f"Error creating summary statistics: {e}")
            return {}

    def save_processed_data(self, data: Any, filename: str):
        """Save processed data"""
        output_file = self.output_path / filename

        try:
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Saved processed data to {output_file}")
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def run(self):
        """Run the preprocessing process"""
        console.print("\n[bold blue]Akash Network - Data Preprocessor[/bold blue]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Load and process cost data
            task1 = progress.add_task("Loading cost data...", total=None)
            costs = self.load_latest_data('deployment_costs')
            progress.update(task1, completed=True)

            if costs:
                task2 = progress.add_task("Removing duplicates...", total=None)
                costs = self.remove_duplicate_records(
                    costs,
                    ['lease_id.owner', 'lease_id.dseq', 'lease_id.provider']
                )
                progress.update(task2, completed=True)

                task3 = progress.add_task("Filling missing values...", total=None)
                costs = self.fill_missing_values(costs)
                progress.update(task3, completed=True)

                task4 = progress.add_task("Detecting outliers...", total=None)
                costs = self.detect_and_flag_outliers(costs)
                progress.update(task4, completed=True)

                task5 = progress.add_task("Enriching data...", total=None)
                costs = self.enrich_data(costs)
                progress.update(task5, completed=True)

                task6 = progress.add_task("Creating summary...", total=None)
                summary = self.create_summary_statistics(costs)
                progress.update(task6, completed=True)

                task7 = progress.add_task("Saving processed data...", total=None)
                self.save_processed_data(costs, 'processed_costs.json')
                self.save_processed_data(summary, 'dashboard_summary.json')
                progress.update(task7, completed=True)

            # Load and process resource data
            task8 = progress.add_task("Loading resource data...", total=None)
            resources = self.load_latest_data('lease_resources')
            progress.update(task8, completed=True)

            if resources:
                task9 = progress.add_task("Processing resources...", total=None)
                resources = self.remove_duplicate_records(
                    resources,
                    ['lease_id.owner', 'lease_id.dseq', 'lease_id.provider']
                )
                resources = self.enrich_data(resources)
                self.save_processed_data(resources, 'processed_resources.json')
                progress.update(task9, completed=True)

        console.print("\n[bold green]Preprocessing Complete![/bold green]\n")
        console.print(f"Processed {len(costs)} cost records")
        console.print(f"Processed {len(resources)} resource records")
        console.print(f"Output saved to: {self.output_path}\n")


@click.command()
@click.option('--config', default='config.yaml', help='Path to configuration file')
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
def main(config, verbose):
    """Preprocess and clean collected data"""

    # Load configuration
    cfg = Config(config)

    # Setup logging
    if verbose:
        cfg.config['logging']['level'] = 'DEBUG'
    setup_logging(cfg)

    # Run preprocessor
    preprocessor = DataPreprocessor(cfg)
    preprocessor.run()


if __name__ == '__main__':
    main()
