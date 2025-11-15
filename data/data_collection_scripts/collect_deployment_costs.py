#!/usr/bin/env python3
"""
Collect deployment costs from Akash Network

This script collects information about active deployments and their associated
costs (leases) from the Akash Network blockchain.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    Config,
    AkashAPIClient,
    DataStorage,
    setup_logging,
    get_akt_price,
    calculate_cost
)
from loguru import logger

console = Console()


class DeploymentCostCollector:
    """Collects deployment cost data from Akash Network"""

    def __init__(self, config: Config):
        self.config = config
        self.api_client = AkashAPIClient(config)
        self.storage = DataStorage(config)
        self.akt_price = get_akt_price(config)

    def collect_deployments(self) -> List[Dict]:
        """Collect all active deployments"""
        logger.info("Collecting deployments from Akash Network...")

        endpoint = self.config.get('akash', 'endpoints', 'deployments', default='/akash/deployment/v1beta3/deployments/list')
        page_size = self.config.get('collection', 'page_size', default=100)

        deployments = self.api_client.paginated_request(endpoint, page_size)

        logger.info(f"Collected {len(deployments)} deployments")
        return deployments

    def collect_leases(self) -> List[Dict]:
        """Collect all active leases (represents actual costs)"""
        logger.info("Collecting leases from Akash Network...")

        endpoint = self.config.get('akash', 'endpoints', 'leases', default='/akash/market/v1beta3/leases/list')
        page_size = self.config.get('collection', 'page_size', default=100)

        leases = self.api_client.paginated_request(endpoint, page_size)

        logger.info(f"Collected {len(leases)} leases")
        return leases

    def process_lease_costs(self, leases: List[Dict]) -> List[Dict]:
        """Process lease data to extract cost information"""
        processed_costs = []

        for lease in leases:
            try:
                lease_data = lease.get('lease', {})
                lease_id = lease_data.get('lease_id', {})

                # Extract price from lease
                price_info = lease.get('escrow_payment', {})

                # Price is typically in the format of amount per block
                amount_uakt = 0
                if 'rate' in price_info:
                    rate = price_info['rate']
                    if isinstance(rate, dict):
                        amount_uakt = int(rate.get('amount', 0))
                    elif isinstance(rate, str):
                        amount_uakt = int(rate)

                # Calculate costs
                usd_per_block = calculate_cost(amount_uakt, self.akt_price)

                # Akash blocks are ~6 seconds, so ~14,400 blocks per day
                blocks_per_day = 14400
                blocks_per_month = blocks_per_day * 30

                daily_cost_usd = usd_per_block * blocks_per_day
                monthly_cost_usd = usd_per_block * blocks_per_month

                cost_data = {
                    'timestamp': datetime.now().isoformat(),
                    'deployment_id': {
                        'owner': lease_id.get('owner', ''),
                        'dseq': lease_id.get('dseq', ''),
                    },
                    'lease_id': {
                        'owner': lease_id.get('owner', ''),
                        'dseq': lease_id.get('dseq', ''),
                        'gseq': lease_id.get('gseq', ''),
                        'oseq': lease_id.get('oseq', ''),
                        'provider': lease_id.get('provider', ''),
                    },
                    'pricing': {
                        'amount_uakt_per_block': amount_uakt,
                        'akt_per_block': amount_uakt / 1_000_000,
                        'usd_per_block': usd_per_block,
                        'daily_cost_usd': daily_cost_usd,
                        'monthly_cost_usd': monthly_cost_usd,
                        'akt_usd_rate': self.akt_price,
                    },
                    'state': lease_data.get('state', ''),
                    'created_at': lease_data.get('created_at', ''),
                }

                processed_costs.append(cost_data)

            except Exception as e:
                logger.warning(f"Error processing lease: {e}")
                continue

        logger.info(f"Processed {len(processed_costs)} lease costs")
        return processed_costs

    def calculate_aggregate_stats(self, costs: List[Dict]) -> Dict:
        """Calculate aggregate statistics for all deployments"""
        if not costs:
            return {}

        total_daily = sum(c['pricing']['daily_cost_usd'] for c in costs)
        total_monthly = sum(c['pricing']['monthly_cost_usd'] for c in costs)
        avg_daily = total_daily / len(costs) if costs else 0
        avg_monthly = total_monthly / len(costs) if costs else 0

        # Group by provider
        provider_stats = {}
        for cost in costs:
            provider = cost['lease_id']['provider']
            if provider not in provider_stats:
                provider_stats[provider] = {
                    'lease_count': 0,
                    'total_daily_usd': 0,
                    'total_monthly_usd': 0,
                }
            provider_stats[provider]['lease_count'] += 1
            provider_stats[provider]['total_daily_usd'] += cost['pricing']['daily_cost_usd']
            provider_stats[provider]['total_monthly_usd'] += cost['pricing']['monthly_cost_usd']

        return {
            'timestamp': datetime.now().isoformat(),
            'akt_usd_price': self.akt_price,
            'total_active_leases': len(costs),
            'aggregate_costs': {
                'total_daily_usd': total_daily,
                'total_monthly_usd': total_monthly,
                'average_daily_usd': avg_daily,
                'average_monthly_usd': avg_monthly,
            },
            'provider_breakdown': provider_stats,
        }

    def run(self):
        """Run the cost collection process"""
        console.print("\n[bold blue]Akash Network - Deployment Cost Collector[/bold blue]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Collect leases
            task1 = progress.add_task("Collecting leases...", total=None)
            leases = self.collect_leases()
            progress.update(task1, completed=True)

            # Process costs
            task2 = progress.add_task("Processing cost data...", total=None)
            costs = self.process_lease_costs(leases)
            progress.update(task2, completed=True)

            # Calculate statistics
            task3 = progress.add_task("Calculating statistics...", total=None)
            stats = self.calculate_aggregate_stats(costs)
            progress.update(task3, completed=True)

            # Save data
            task4 = progress.add_task("Saving data...", total=None)
            self.storage.save(costs, 'deployment_costs')
            self.storage.save(stats, 'cost_statistics')
            progress.update(task4, completed=True)

        # Display summary
        console.print("\n[bold green]Collection Complete![/bold green]\n")
        console.print(f"Total Active Leases: [cyan]{stats['total_active_leases']}[/cyan]")
        console.print(f"Total Daily Cost: [cyan]${stats['aggregate_costs']['total_daily_usd']:.2f}[/cyan]")
        console.print(f"Total Monthly Cost: [cyan]${stats['aggregate_costs']['total_monthly_usd']:.2f}[/cyan]")
        console.print(f"Average Daily Cost per Lease: [cyan]${stats['aggregate_costs']['average_daily_usd']:.2f}[/cyan]")
        console.print(f"Current AKT Price: [cyan]${self.akt_price:.2f}[/cyan]\n")

        return stats


@click.command()
@click.option('--config', default='config.yaml', help='Path to configuration file')
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
def main(config, verbose):
    """Collect deployment cost data from Akash Network"""

    # Load configuration
    cfg = Config(config)

    # Setup logging
    if verbose:
        cfg.config['logging']['level'] = 'DEBUG'
    setup_logging(cfg)

    # Run collector
    collector = DeploymentCostCollector(cfg)
    collector.run()


if __name__ == '__main__':
    main()
