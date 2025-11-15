#!/usr/bin/env python3
"""
Collect resource usage data from Akash Network

This script collects information about resource utilization across the network,
including CPU, GPU, memory, and storage usage from active leases and provider capacity.
"""

import sys
import os
from datetime import datetime
from typing import List, Dict, Tuple
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    Config,
    AkashAPIClient,
    DataStorage,
    setup_logging
)
from loguru import logger

console = Console()


class ResourceUsageCollector:
    """Collects resource usage data from Akash Network"""

    def __init__(self, config: Config):
        self.config = config
        self.api_client = AkashAPIClient(config)
        self.storage = DataStorage(config)

    def collect_providers(self) -> List[Dict]:
        """Collect all active providers"""
        logger.info("Collecting providers from Akash Network...")

        endpoint = self.config.get('akash', 'endpoints', 'providers', default='/akash/provider/v1beta3/providers')
        page_size = self.config.get('collection', 'page_size', default=100)

        providers = self.api_client.paginated_request(endpoint, page_size)

        logger.info(f"Collected {len(providers)} providers")
        return providers

    def collect_leases(self) -> List[Dict]:
        """Collect all active leases to determine resource usage"""
        logger.info("Collecting leases for resource analysis...")

        endpoint = self.config.get('akash', 'endpoints', 'leases', default='/akash/market/v1beta3/leases/list')
        page_size = self.config.get('collection', 'page_size', default=100)

        leases = self.api_client.paginated_request(endpoint, page_size)

        logger.info(f"Collected {len(leases)} leases")
        return leases

    def parse_resource_spec(self, resources: Dict) -> Dict:
        """Parse resource specifications from deployment/lease"""
        resource_data = {
            'cpu': 0,
            'gpu': 0,
            'memory': 0,
            'storage': 0,
        }

        try:
            if isinstance(resources, list):
                for resource_group in resources:
                    resources_obj = resource_group.get('resources', {})

                    # CPU (in millicores, 1000 = 1 CPU)
                    cpu = resources_obj.get('cpu', {})
                    if cpu:
                        units = cpu.get('units', {})
                        if units:
                            val = units.get('val', '0')
                            resource_data['cpu'] += int(val) / 1000

                    # GPU
                    gpu = resources_obj.get('gpu', {})
                    if gpu:
                        units = gpu.get('units', {})
                        if units:
                            val = units.get('val', '0')
                            resource_data['gpu'] += int(val)

                    # Memory (in bytes)
                    memory = resources_obj.get('memory', {})
                    if memory:
                        quantity = memory.get('quantity', {})
                        if quantity:
                            val = quantity.get('val', '0')
                            # Convert to GB
                            resource_data['memory'] += int(val) / (1024 ** 3)

                    # Storage (in bytes)
                    storage = resources_obj.get('storage', [])
                    for storage_item in storage:
                        quantity = storage_item.get('quantity', {})
                        if quantity:
                            val = quantity.get('val', '0')
                            # Convert to GB
                            resource_data['storage'] += int(val) / (1024 ** 3)

        except Exception as e:
            logger.warning(f"Error parsing resource spec: {e}")

        return resource_data

    def analyze_lease_resources(self, leases: List[Dict]) -> Tuple[List[Dict], Dict]:
        """Analyze resource usage from leases"""
        lease_resources = []
        total_resources = {
            'cpu': 0,
            'gpu': 0,
            'memory': 0,
            'storage': 0,
        }

        for lease in leases:
            try:
                lease_data = lease.get('lease', {})
                lease_id = lease_data.get('lease_id', {})

                # Note: Actual resource specs would need to be fetched from the deployment
                # For now, we're collecting lease IDs and provider associations
                lease_info = {
                    'timestamp': datetime.now().isoformat(),
                    'lease_id': {
                        'owner': lease_id.get('owner', ''),
                        'dseq': lease_id.get('dseq', ''),
                        'gseq': lease_id.get('gseq', ''),
                        'oseq': lease_id.get('oseq', ''),
                        'provider': lease_id.get('provider', ''),
                    },
                    'state': lease_data.get('state', ''),
                    'created_at': lease_data.get('created_at', ''),
                }

                lease_resources.append(lease_info)

            except Exception as e:
                logger.warning(f"Error analyzing lease resources: {e}")
                continue

        logger.info(f"Analyzed {len(lease_resources)} lease resources")
        return lease_resources, total_resources

    def analyze_provider_capacity(self, providers: List[Dict]) -> List[Dict]:
        """Analyze provider capacity and attributes"""
        provider_data = []

        for provider in providers:
            try:
                provider_info = provider.get('provider', {})
                attributes = provider.get('attributes', [])

                # Parse provider attributes
                attr_dict = {}
                for attr in attributes:
                    key = attr.get('key', '')
                    value = attr.get('value', '')
                    attr_dict[key] = value

                provider_record = {
                    'timestamp': datetime.now().isoformat(),
                    'address': provider_info.get('owner', ''),
                    'host_uri': provider_info.get('host_uri', ''),
                    'attributes': attr_dict,
                    'info': provider_info.get('info', {}),
                }

                provider_data.append(provider_record)

            except Exception as e:
                logger.warning(f"Error analyzing provider: {e}")
                continue

        logger.info(f"Analyzed {len(provider_data)} providers")
        return provider_data

    def calculate_network_statistics(self, leases: List[Dict], providers: List[Dict]) -> Dict:
        """Calculate network-wide resource statistics"""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'active_leases': len(leases),
            'active_providers': len(providers),
            'resources': {
                'total_cpu_cores': 0,
                'total_gpu_units': 0,
                'total_memory_gb': 0,
                'total_storage_gb': 0,
            },
            'provider_distribution': {
                'total_providers': len(providers),
                'providers_with_active_leases': 0,
            },
        }

        # Count providers with active leases
        providers_with_leases = set()
        for lease in leases:
            try:
                lease_data = lease.get('lease', {})
                lease_id = lease_data.get('lease_id', {})
                provider = lease_id.get('provider', '')
                if provider:
                    providers_with_leases.add(provider)
            except:
                continue

        stats['provider_distribution']['providers_with_active_leases'] = len(providers_with_leases)

        # Calculate utilization rate
        if stats['active_providers'] > 0:
            stats['provider_distribution']['utilization_rate'] = (
                len(providers_with_leases) / stats['active_providers']
            ) * 100

        return stats

    def run(self):
        """Run the resource collection process"""
        console.print("\n[bold blue]Akash Network - Resource Usage Collector[/bold blue]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Collect providers
            task1 = progress.add_task("Collecting providers...", total=None)
            providers = self.collect_providers()
            progress.update(task1, completed=True)

            # Collect leases
            task2 = progress.add_task("Collecting leases...", total=None)
            leases = self.collect_leases()
            progress.update(task2, completed=True)

            # Analyze resources
            task3 = progress.add_task("Analyzing lease resources...", total=None)
            lease_resources, total_resources = self.analyze_lease_resources(leases)
            progress.update(task3, completed=True)

            # Analyze provider capacity
            task4 = progress.add_task("Analyzing provider capacity...", total=None)
            provider_data = self.analyze_provider_capacity(providers)
            progress.update(task4, completed=True)

            # Calculate statistics
            task5 = progress.add_task("Calculating network statistics...", total=None)
            stats = self.calculate_network_statistics(leases, providers)
            progress.update(task5, completed=True)

            # Save data
            task6 = progress.add_task("Saving data...", total=None)
            self.storage.save(lease_resources, 'lease_resources')
            self.storage.save(provider_data, 'provider_capacity')
            self.storage.save(stats, 'network_statistics')
            progress.update(task6, completed=True)

        # Display summary
        console.print("\n[bold green]Collection Complete![/bold green]\n")

        table = Table(title="Network Resource Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Active Leases", str(stats['active_leases']))
        table.add_row("Active Providers", str(stats['active_providers']))
        table.add_row(
            "Providers with Leases",
            str(stats['provider_distribution']['providers_with_active_leases'])
        )
        if 'utilization_rate' in stats['provider_distribution']:
            table.add_row(
                "Provider Utilization",
                f"{stats['provider_distribution']['utilization_rate']:.2f}%"
            )

        console.print(table)
        console.print()

        return stats


@click.command()
@click.option('--config', default='config.yaml', help='Path to configuration file')
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
def main(config, verbose):
    """Collect resource usage data from Akash Network"""

    # Load configuration
    cfg = Config(config)

    # Setup logging
    if verbose:
        cfg.config['logging']['level'] = 'DEBUG'
    setup_logging(cfg)

    # Run collector
    collector = ResourceUsageCollector(cfg)
    collector.run()


if __name__ == '__main__':
    main()
