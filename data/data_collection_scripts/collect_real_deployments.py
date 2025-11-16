#!/usr/bin/env python3
"""
Akash Network - Real Deployment Data Collector with Pricing Estimation

This script collects real deployment data from the Akash Network and estimates
costs based on resource specifications and market pricing benchmarks.

Since the public API doesn't provide lease pricing data, we estimate costs using:
- Resource specifications from deployments
- Market rate benchmarks for Akash pricing
- Provider-specific pricing when available
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import click
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import Config, AkashAPIClient, DataStorage, setup_logging

console = Console()


class PricingEstimator:
    """Estimates deployment costs based on resource specifications"""

    # Market rate benchmarks (USD per month)
    # Based on Akash documentation and community pricing data
    PRICING_BENCHMARKS = {
        'cpu_per_core': 1.00,  # $1.00 per core/month (1000 millicores)
        'memory_per_gb': 0.20,  # $0.20 per GB/month
        'storage_per_gb': 0.03,  # $0.03 per GB/month (ephemeral)
        'storage_persistent_per_gb': 0.10,  # $0.10 per GB/month (persistent)
        'gpu_per_unit': 100.00,  # $100 per GPU/month (varies by model)

        # GPU model multipliers (relative to base price)
        'gpu_models': {
            'nvidia-tesla-v100': 2.0,
            'nvidia-tesla-p100': 1.5,
            'nvidia-tesla-t4': 1.2,
            'nvidia-rtx-3090': 1.8,
            'nvidia-rtx-4090': 2.5,
            'nvidia-a100': 3.5,
            'default': 1.0
        }
    }

    @classmethod
    def estimate_deployment_cost(cls, deployment: Dict) -> Dict:
        """
        Estimate monthly cost for a deployment based on resource specs

        Args:
            deployment: Deployment data from Akash API

        Returns:
            Dict with pricing estimates and breakdown
        """
        try:
            resources = cls._extract_resources(deployment)

            # Calculate component costs
            cpu_cost = cls._calculate_cpu_cost(resources.get('cpu', 0))
            memory_cost = cls._calculate_memory_cost(resources.get('memory', 0))
            storage_cost = cls._calculate_storage_cost(resources.get('storage', 0))
            gpu_cost = cls._calculate_gpu_cost(
                resources.get('gpu', 0),
                resources.get('gpu_model', 'default')
            )

            # Total monthly cost
            total_monthly = cpu_cost + memory_cost + storage_cost + gpu_cost
            total_daily = total_monthly / 30
            total_hourly = total_monthly / 730  # ~730 hours per month

            return {
                'total_monthly_usd': round(total_monthly, 2),
                'total_daily_usd': round(total_daily, 2),
                'total_hourly_usd': round(total_hourly, 4),
                'breakdown': {
                    'cpu_monthly_usd': round(cpu_cost, 2),
                    'memory_monthly_usd': round(memory_cost, 2),
                    'storage_monthly_usd': round(storage_cost, 2),
                    'gpu_monthly_usd': round(gpu_cost, 2),
                },
                'resources': resources,
                'estimation_method': 'resource_based_benchmark'
            }
        except Exception as e:
            logger.warning(f"Error estimating cost: {e}")
            return {
                'total_monthly_usd': 0,
                'total_daily_usd': 0,
                'total_hourly_usd': 0,
                'breakdown': {},
                'resources': {},
                'estimation_method': 'error',
                'error': str(e)
            }

    @classmethod
    def _extract_resources(cls, deployment: Dict) -> Dict:
        """Extract resource specifications from deployment data"""
        resources = {
            'cpu': 0,
            'memory': 0,
            'storage': 0,
            'gpu': 0,
            'gpu_model': 'default'
        }

        try:
            groups = deployment.get('groups', [])
            for group in groups:
                group_spec = group.get('group_spec', {})
                resource_list = group_spec.get('resources', [])

                for resource_item in resource_list:
                    resource = resource_item.get('resource', {})
                    count = int(resource_item.get('count', 1))

                    # CPU (in millicores)
                    cpu = resource.get('cpu', {})
                    cpu_units = cpu.get('units', {})
                    cpu_val = int(cpu_units.get('val', 0))
                    resources['cpu'] += cpu_val * count

                    # Memory (in bytes)
                    memory = resource.get('memory', {})
                    memory_quantity = memory.get('quantity', {})
                    memory_val = int(memory_quantity.get('val', 0))
                    resources['memory'] += memory_val * count

                    # Storage (in bytes)
                    storage_items = resource.get('storage', [])
                    for storage in storage_items:
                        storage_quantity = storage.get('quantity', {})
                        storage_val = int(storage_quantity.get('val', 0))
                        resources['storage'] += storage_val * count

                    # GPU
                    gpu = resource.get('gpu', {})
                    gpu_units = gpu.get('units', {})
                    gpu_val = int(gpu_units.get('val', 0))
                    resources['gpu'] += gpu_val * count

                    # GPU model from attributes
                    gpu_attrs = gpu.get('attributes', [])
                    for attr in gpu_attrs:
                        if attr.get('key') == 'vendor/nvidia/model':
                            resources['gpu_model'] = attr.get('value', 'default').lower()

            return resources

        except Exception as e:
            logger.error(f"Error extracting resources: {e}")
            return resources

    @classmethod
    def _calculate_cpu_cost(cls, cpu_millicores: int) -> float:
        """Calculate CPU cost from millicores"""
        cores = cpu_millicores / 1000
        return cores * cls.PRICING_BENCHMARKS['cpu_per_core']

    @classmethod
    def _calculate_memory_cost(cls, memory_bytes: int) -> float:
        """Calculate memory cost from bytes"""
        memory_gb = memory_bytes / (1024 ** 3)
        return memory_gb * cls.PRICING_BENCHMARKS['memory_per_gb']

    @classmethod
    def _calculate_storage_cost(cls, storage_bytes: int) -> float:
        """Calculate storage cost from bytes"""
        storage_gb = storage_bytes / (1024 ** 3)
        # Assuming ephemeral storage (most common)
        return storage_gb * cls.PRICING_BENCHMARKS['storage_per_gb']

    @classmethod
    def _calculate_gpu_cost(cls, gpu_count: int, gpu_model: str = 'default') -> float:
        """Calculate GPU cost based on count and model"""
        if gpu_count == 0:
            return 0

        base_cost = cls.PRICING_BENCHMARKS['gpu_per_unit']
        model_multiplier = cls.PRICING_BENCHMARKS['gpu_models'].get(
            gpu_model.lower(),
            cls.PRICING_BENCHMARKS['gpu_models']['default']
        )

        return gpu_count * base_cost * model_multiplier


class RealDeploymentCollector:
    """Collects real deployment data from Akash Network"""

    def __init__(self, config: Config):
        self.config = config
        self.api_client = AkashAPIClient(config)
        self.storage = DataStorage(config)
        self.estimator = PricingEstimator()

    def collect_deployments(self) -> List[Dict]:
        """Collect active deployments from Akash Network"""
        logger.info("Collecting deployments from Akash Network...")

        endpoint = self.config.get('akash', 'endpoints', 'deployments',
                                   default='/akash/deployment/v1beta4/deployments/list')
        page_size = self.config.get('collection', 'page_size', default=100)

        deployments = self.api_client.paginated_request(endpoint, page_size)

        logger.info(f"Collected {len(deployments)} deployments")
        return deployments

    def process_deployments(self, deployments: List[Dict]) -> List[Dict]:
        """Process deployments and add cost estimations"""
        processed = []

        for deployment in deployments:
            try:
                deployment_data = deployment.get('deployment', {})
                deployment_id = deployment_data.get('id', {})

                # Skip if not active
                if deployment_data.get('state') != 'active':
                    continue

                # Estimate costs
                pricing = self.estimator.estimate_deployment_cost(deployment)

                # Extract provider info from groups
                providers = set()
                groups = deployment.get('groups', [])
                for group in groups:
                    group_id = group.get('id', {})
                    if 'provider' in group_id:
                        providers.add(group_id.get('provider'))

                processed_deployment = {
                    'timestamp': datetime.now().isoformat(),
                    'deployment_id': {
                        'owner': deployment_id.get('owner', ''),
                        'dseq': str(deployment_id.get('dseq', '')),
                    },
                    'state': deployment_data.get('state', ''),
                    'created_at': deployment_data.get('created_at', ''),
                    'providers': list(providers),
                    'pricing_estimate': pricing,
                    'metadata': {
                        'data_source': 'akash_public_api',
                        'collection_timestamp': datetime.now().isoformat(),
                        'is_estimate': True,
                        'estimation_disclaimer': 'Costs are estimated based on resource specifications and market benchmarks. Actual costs may vary.'
                    }
                }

                processed.append(processed_deployment)

            except Exception as e:
                logger.warning(f"Error processing deployment: {e}")
                continue

        logger.info(f"Processed {len(processed)} active deployments with cost estimates")
        return processed

    def calculate_aggregate_stats(self, deployments: List[Dict]) -> Dict:
        """Calculate aggregate statistics"""
        if not deployments:
            return {
                'total_active_deployments': 0,
                'total_estimated_monthly_cost_usd': 0,
                'total_estimated_daily_cost_usd': 0,
                'average_deployment_cost_monthly_usd': 0,
                'unique_owners': 0,
                'unique_providers': 0,
                'resource_totals': {},
                'cost_distribution': {}
            }

        total_monthly = sum(d['pricing_estimate']['total_monthly_usd'] for d in deployments)
        total_daily = sum(d['pricing_estimate']['total_daily_usd'] for d in deployments)
        unique_owners = len(set(d['deployment_id']['owner'] for d in deployments))

        # Collect all providers
        all_providers = set()
        for d in deployments:
            all_providers.update(d.get('providers', []))

        # Resource totals
        total_cpu = sum(d['pricing_estimate']['resources'].get('cpu', 0) for d in deployments)
        total_memory = sum(d['pricing_estimate']['resources'].get('memory', 0) for d in deployments)
        total_storage = sum(d['pricing_estimate']['resources'].get('storage', 0) for d in deployments)
        total_gpu = sum(d['pricing_estimate']['resources'].get('gpu', 0) for d in deployments)

        return {
            'timestamp': datetime.now().isoformat(),
            'total_active_deployments': len(deployments),
            'total_estimated_monthly_cost_usd': round(total_monthly, 2),
            'total_estimated_daily_cost_usd': round(total_daily, 2),
            'average_deployment_cost_monthly_usd': round(total_monthly / len(deployments), 2) if deployments else 0,
            'unique_owners': unique_owners,
            'unique_providers': len(all_providers),
            'resource_totals': {
                'total_cpu_millicores': total_cpu,
                'total_cpu_cores': round(total_cpu / 1000, 2),
                'total_memory_bytes': total_memory,
                'total_memory_gb': round(total_memory / (1024 ** 3), 2),
                'total_storage_bytes': total_storage,
                'total_storage_gb': round(total_storage / (1024 ** 3), 2),
                'total_gpu_units': total_gpu
            },
            'cost_distribution': {
                'deployments_under_10_usd': len([d for d in deployments if d['pricing_estimate']['total_monthly_usd'] < 10]),
                'deployments_10_to_50_usd': len([d for d in deployments if 10 <= d['pricing_estimate']['total_monthly_usd'] < 50]),
                'deployments_50_to_100_usd': len([d for d in deployments if 50 <= d['pricing_estimate']['total_monthly_usd'] < 100]),
                'deployments_over_100_usd': len([d for d in deployments if d['pricing_estimate']['total_monthly_usd'] >= 100]),
            },
            'disclaimer': 'All costs are estimates based on resource specifications and market pricing benchmarks. Actual costs may vary based on provider pricing and market conditions.'
        }

    def run(self):
        """Run the collection process"""
        console.print("\n[bold blue]Akash Network - Real Deployment Collector (with Cost Estimation)[/bold blue]\n")
        console.print("[yellow]Note: Costs are estimated based on resource specs and market benchmarks[/yellow]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Collect deployments
            task1 = progress.add_task("Collecting deployments from blockchain...", total=None)
            deployments = self.collect_deployments()
            progress.update(task1, completed=True)

            # Process and estimate costs
            task2 = progress.add_task("Estimating costs based on resources...", total=None)
            processed = self.process_deployments(deployments)
            progress.update(task2, completed=True)

            # Calculate statistics
            task3 = progress.add_task("Calculating network statistics...", total=None)
            stats = self.calculate_aggregate_stats(processed)
            progress.update(task3, completed=True)

            # Save data
            task4 = progress.add_task("Saving data...", total=None)
            self.storage.save(processed, 'real_deployments')
            self.storage.save(stats, 'network_statistics')
            progress.update(task4, completed=True)

        # Display summary table
        console.print("\n[bold green]Collection Complete![/bold green]\n")

        table = Table(title="Network Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Total Active Deployments", str(stats['total_active_deployments']))
        table.add_row("Unique Owners", str(stats['unique_owners']))
        table.add_row("Unique Providers", str(stats['unique_providers']))
        table.add_row("Est. Total Daily Cost", f"${stats['total_estimated_daily_cost_usd']:,.2f}")
        table.add_row("Est. Total Monthly Cost", f"${stats['total_estimated_monthly_cost_usd']:,.2f}")
        table.add_row("Avg. Cost per Deployment", f"${stats['average_deployment_cost_monthly_usd']:.2f}/mo")
        table.add_row("Total CPU Cores", f"{stats['resource_totals']['total_cpu_cores']:.1f}")
        table.add_row("Total Memory (GB)", f"{stats['resource_totals']['total_memory_gb']:.1f}")
        table.add_row("Total Storage (GB)", f"{stats['resource_totals']['total_storage_gb']:.1f}")
        table.add_row("Total GPUs", str(stats['resource_totals']['total_gpu_units']))

        console.print(table)
        console.print(f"\n[dim]Data saved to: {self.storage.config.get('storage', 'directory', default='collected_data')}[/dim]")
        console.print("[dim yellow]⚠️  Costs are estimates only - actual provider pricing may vary[/dim yellow]\n")

        return stats


@click.command()
@click.option('--config', default='config.yaml', help='Path to configuration file')
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
def main(config, verbose):
    """Collect real deployment data from Akash Network with cost estimation"""

    # Load configuration
    cfg = Config(config)

    # Setup logging
    if verbose:
        cfg.config['logging']['level'] = 'DEBUG'
    setup_logging(cfg)

    # Run collector
    collector = RealDeploymentCollector(cfg)
    collector.run()


if __name__ == '__main__':
    main()
