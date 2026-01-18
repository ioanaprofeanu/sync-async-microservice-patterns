#!/usr/bin/env python3
"""
K6 Test Results Comparison Tool

Analyzes and compares k6 JSON output from synchronous and asynchronous tests.
Generates detailed comparison reports with metrics, charts, and recommendations.

Usage:
    python3 compare-results.py <results_directory> [load_profile]
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

# ANSI color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color


def parse_k6_json(json_file: Path) -> Dict[str, Any]:
    """Parse k6 JSON output and extract key metrics."""
    metrics = {
        'scenarios': {},
        'overall': {
            'iterations': 0,
            'http_reqs': 0,
            'http_req_duration_avg': 0,
            'http_req_duration_p95': 0,
            'http_req_duration_p99': 0,
            'error_rate': 0,
            'throughput': 0,
        }
    }

    with open(json_file, 'r') as f:
        for line in f:
            try:
                data = json.loads(line.strip())

                if data['type'] == 'Point' and data['metric'] == 'http_req_duration':
                    scenario = data.get('data', {}).get('tags', {}).get('scenario', 'unknown')
                    if scenario not in metrics['scenarios']:
                        metrics['scenarios'][scenario] = {
                            'requests': 0,
                            'durations': [],
                            'errors': 0,
                        }

                    metrics['scenarios'][scenario]['requests'] += 1
                    metrics['scenarios'][scenario]['durations'].append(data['data']['value'])

                elif data['type'] == 'Point':
                    metric_name = data['metric']
                    value = data['data']['value']

                    # Collect scenario-specific errors
                    if 'errors' in metric_name:
                        scenario = metric_name.split('_')[0].replace('scenario', 'scenario')
                        if scenario in metrics['scenarios']:
                            metrics['scenarios'][scenario]['errors'] += value

            except (json.JSONDecodeError, KeyError):
                continue

    # Calculate statistics for each scenario
    for scenario, data in metrics['scenarios'].items():
        if data['durations']:
            sorted_durations = sorted(data['durations'])
            data['avg'] = sum(sorted_durations) / len(sorted_durations)
            data['min'] = min(sorted_durations)
            data['max'] = max(sorted_durations)
            data['p50'] = sorted_durations[int(len(sorted_durations) * 0.50)]
            data['p95'] = sorted_durations[int(len(sorted_durations) * 0.95)]
            data['p99'] = sorted_durations[int(len(sorted_durations) * 0.99)]

    return metrics


def parse_summary_json(summary_file: Path) -> Dict[str, Any]:
    """Parse k6 summary JSON output."""
    try:
        with open(summary_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def calculate_improvement(sync_val: float, async_val: float) -> Tuple[float, str]:
    """Calculate percentage improvement (negative means async is slower)."""
    if sync_val == 0:
        return 0.0, "N/A"

    improvement = ((sync_val - async_val) / sync_val) * 100

    if improvement > 0:
        return improvement, f"{Colors.GREEN}↓ {improvement:.1f}% faster{Colors.NC}"
    elif improvement < 0:
        return improvement, f"{Colors.RED}↑ {abs(improvement):.1f}% slower{Colors.NC}"
    else:
        return 0.0, f"{Colors.YELLOW}~ Same{Colors.NC}"


def format_duration(ms: float) -> str:
    """Format duration in human-readable format."""
    if ms < 1:
        return f"{ms*1000:.2f}µs"
    elif ms < 1000:
        return f"{ms:.2f}ms"
    else:
        return f"{ms/1000:.2f}s"


def print_header(text: str):
    """Print a formatted header."""
    width = 80
    print(f"\n{Colors.CYAN}{'='*width}{Colors.NC}")
    print(f"{Colors.BOLD}{text.center(width)}{Colors.NC}")
    print(f"{Colors.CYAN}{'='*width}{Colors.NC}\n")


def print_comparison_table(sync_metrics: Dict, async_metrics: Dict):
    """Print detailed comparison table."""
    print_header("SCENARIO-BY-SCENARIO COMPARISON")

    scenarios = {
        'scenario1': 'User Registration (Fire-and-Forget)',
        'scenario2': 'Payment Processing (Long-Running)',
        'scenario3': 'Product Update (Fan-Out)',
        'scenario4': 'Report Generation (CPU-Intensive)',
        'scenario5': 'Order Creation (Saga Pattern)',
        'scenario6': 'Click Tracking (High-Throughput)',
    }

    for scenario_id, scenario_name in scenarios.items():
        if scenario_id not in sync_metrics['scenarios'] or scenario_id not in async_metrics['scenarios']:
            continue

        sync_data = sync_metrics['scenarios'][scenario_id]
        async_data = async_metrics['scenarios'][scenario_id]

        print(f"{Colors.BOLD}{scenario_name}{Colors.NC}")
        print("-" * 80)

        # Response time comparison
        print(f"{'Metric':<25} {'Sync':<15} {'Async':<15} {'Improvement':<25}")
        print("-" * 80)

        metrics_to_compare = [
            ('Average', 'avg'),
            ('Median (p50)', 'p50'),
            ('95th percentile', 'p95'),
            ('99th percentile', 'p99'),
            ('Min', 'min'),
            ('Max', 'max'),
        ]

        for label, key in metrics_to_compare:
            sync_val = sync_data.get(key, 0)
            async_val = async_data.get(key, 0)
            _, improvement_str = calculate_improvement(sync_val, async_val)

            print(f"{label:<25} {format_duration(sync_val):<15} {format_duration(async_val):<15} {improvement_str}")

        # Request statistics
        print(f"\n{'Requests':<25} {sync_data['requests']:<15} {async_data['requests']:<15}")
        print(f"{'Errors':<25} {sync_data.get('errors', 0):<15} {async_data.get('errors', 0):<15}")

        # Error rate
        sync_error_rate = (sync_data.get('errors', 0) / sync_data['requests'] * 100) if sync_data['requests'] > 0 else 0
        async_error_rate = (async_data.get('errors', 0) / async_data['requests'] * 100) if async_data['requests'] > 0 else 0
        print(f"{'Error Rate':<25} {sync_error_rate:.2f}%{'':<10} {async_error_rate:.2f}%")

        print("\n")


def print_overall_summary(sync_summary: Dict, async_summary: Dict):
    """Print overall test summary."""
    print_header("OVERALL PERFORMANCE SUMMARY")

    def get_metric(summary: Dict, metric: str, stat: str = 'values', substat: str = 'value') -> float:
        """Safely extract metric from summary."""
        try:
            if stat in summary.get('metrics', {}).get(metric, {}):
                return summary['metrics'][metric][stat].get(substat, 0)
            return 0
        except (KeyError, AttributeError, TypeError):
            return 0

    # HTTP request duration
    print(f"{Colors.BOLD}HTTP Request Duration{Colors.NC}")
    print("-" * 80)

    metrics = [
        ('Average', 'avg'),
        ('Median', 'med'),
        ('95th percentile', 'p(95)'),
        ('99th percentile', 'p(99)'),
        ('Max', 'max'),
    ]

    for label, stat in metrics:
        sync_val = get_metric(sync_summary, 'http_req_duration', 'values', stat)
        async_val = get_metric(async_summary, 'http_req_duration', 'values', stat)
        _, improvement = calculate_improvement(sync_val, async_val)

        print(f"{label:<25} {format_duration(sync_val):<15} {format_duration(async_val):<15} {improvement}")

    # Throughput and iterations
    print(f"\n{Colors.BOLD}Throughput Metrics{Colors.NC}")
    print("-" * 80)

    sync_reqs = get_metric(sync_summary, 'http_reqs', 'values', 'count')
    async_reqs = get_metric(async_summary, 'http_reqs', 'values', 'count')

    sync_rate = get_metric(sync_summary, 'http_reqs', 'values', 'rate')
    async_rate = get_metric(async_summary, 'http_reqs', 'values', 'rate')

    print(f"{'Total Requests':<25} {sync_reqs:<15.0f} {async_reqs:<15.0f}")
    print(f"{'Requests/sec':<25} {sync_rate:<15.2f} {async_rate:<15.2f} ", end='')
    _, improvement = calculate_improvement(sync_rate, async_rate)
    print(f"{improvement}")

    # Iterations
    sync_iters = get_metric(sync_summary, 'iterations', 'values', 'count')
    async_iters = get_metric(async_summary, 'iterations', 'values', 'count')
    print(f"{'Total Iterations':<25} {sync_iters:<15.0f} {async_iters:<15.0f}")

    # Error rates
    print(f"\n{Colors.BOLD}Error Rates{Colors.NC}")
    print("-" * 80)

    sync_checks = get_metric(sync_summary, 'checks', 'values', 'passes') + get_metric(sync_summary, 'checks', 'values', 'fails')
    async_checks = get_metric(async_summary, 'checks', 'values', 'passes') + get_metric(async_summary, 'checks', 'values', 'fails')

    sync_fails = get_metric(sync_summary, 'checks', 'values', 'fails')
    async_fails = get_metric(async_summary, 'checks', 'values', 'fails')

    sync_fail_rate = (sync_fails / sync_checks * 100) if sync_checks > 0 else 0
    async_fail_rate = (async_fails / async_checks * 100) if async_checks > 0 else 0

    print(f"{'Check Failures':<25} {sync_fails:<15.0f} {async_fails:<15.0f}")
    print(f"{'Failure Rate':<25} {sync_fail_rate:<14.2f}% {async_fail_rate:<14.2f}%")


def print_recommendations(sync_metrics: Dict, async_metrics: Dict):
    """Print recommendations based on test results."""
    print_header("RECOMMENDATIONS")

    recommendations = []

    # Analyze each scenario
    for scenario_id, scenario_name in {
        'scenario1': 'User Registration',
        'scenario2': 'Payment Processing',
        'scenario3': 'Product Update',
        'scenario4': 'Report Generation',
        'scenario5': 'Order Creation',
        'scenario6': 'Click Tracking',
    }.items():
        if scenario_id in sync_metrics['scenarios'] and scenario_id in async_metrics['scenarios']:
            sync_p95 = sync_metrics['scenarios'][scenario_id].get('p95', 0)
            async_p95 = async_metrics['scenarios'][scenario_id].get('p95', 0)

            improvement, _ = calculate_improvement(sync_p95, async_p95)

            if improvement > 50:
                recommendations.append(
                    f"{Colors.GREEN}✓{Colors.NC} {scenario_name}: "
                    f"Async is {improvement:.0f}% faster - {Colors.GREEN}Strongly recommend async{Colors.NC}"
                )
            elif improvement > 20:
                recommendations.append(
                    f"{Colors.GREEN}✓{Colors.NC} {scenario_name}: "
                    f"Async is {improvement:.0f}% faster - {Colors.GREEN}Recommend async{Colors.NC}"
                )
            elif improvement > 0:
                recommendations.append(
                    f"{Colors.YELLOW}~{Colors.NC} {scenario_name}: "
                    f"Async is {improvement:.0f}% faster - {Colors.YELLOW}Consider async{Colors.NC}"
                )
            elif improvement < -20:
                recommendations.append(
                    f"{Colors.RED}✗{Colors.NC} {scenario_name}: "
                    f"Sync is {abs(improvement):.0f}% faster - {Colors.RED}Use sync{Colors.NC}"
                )

    if recommendations:
        for rec in recommendations:
            print(f"  {rec}")
    else:
        print(f"{Colors.YELLOW}No clear recommendations - results are similar{Colors.NC}")

    print()


def generate_markdown_report(results_dir: Path, load_profile: str, sync_metrics: Dict, async_metrics: Dict, sync_summary: Dict, async_summary: Dict):
    """Generate a markdown report file."""
    report_file = results_dir / "comparison_report.md"

    with open(report_file, 'w') as f:
        f.write(f"# Performance Comparison Report\n\n")
        f.write(f"**Load Profile:** {load_profile.upper()}\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Summary\n\n")
        f.write("| Metric | Synchronous | Asynchronous | Improvement |\n")
        f.write("|--------|-------------|--------------|-------------|\n")

        # Add summary metrics
        def get_metric(summary: Dict, metric: str, stat: str = 'values', substat: str = 'value') -> float:
            try:
                return summary.get('metrics', {}).get(metric, {}).get(stat, {}).get(substat, 0)
            except (KeyError, AttributeError):
                return 0

        sync_p95 = get_metric(sync_summary, 'http_req_duration', 'values', 'p(95)')
        async_p95 = get_metric(async_summary, 'http_req_duration', 'values', 'p(95)')
        improvement, _ = calculate_improvement(sync_p95, async_p95)

        f.write(f"| p95 Latency | {format_duration(sync_p95)} | {format_duration(async_p95)} | {improvement:.1f}% |\n")

        f.write("\n## Scenario Details\n\n")

        for scenario_id, scenario_name in {
            'scenario1': 'User Registration',
            'scenario2': 'Payment Processing',
            'scenario3': 'Product Update',
            'scenario4': 'Report Generation',
            'scenario5': 'Order Creation',
            'scenario6': 'Click Tracking',
        }.items():
            if scenario_id in sync_metrics['scenarios'] and scenario_id in async_metrics['scenarios']:
                f.write(f"### {scenario_name}\n\n")
                f.write("| Metric | Synchronous | Asynchronous |\n")
                f.write("|--------|-------------|-------------|\n")

                sync_data = sync_metrics['scenarios'][scenario_id]
                async_data = async_metrics['scenarios'][scenario_id]

                f.write(f"| Average | {format_duration(sync_data.get('avg', 0))} | {format_duration(async_data.get('avg', 0))} |\n")
                f.write(f"| p95 | {format_duration(sync_data.get('p95', 0))} | {format_duration(async_data.get('p95', 0))} |\n")
                f.write(f"| p99 | {format_duration(sync_data.get('p99', 0))} | {format_duration(async_data.get('p99', 0))} |\n")
                f.write(f"| Requests | {sync_data['requests']} | {async_data['requests']} |\n")
                f.write("\n")

    print(f"{Colors.GREEN}✓ Markdown report saved to: {report_file}{Colors.NC}\n")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <results_directory> [load_profile]")
        sys.exit(1)

    results_dir = Path(sys.argv[1])
    load_profile = sys.argv[2] if len(sys.argv) > 2 else "unknown"

    sync_json = results_dir / "sync_results.json"
    async_json = results_dir / "async_results.json"
    sync_summary = results_dir / "sync_results_summary.json"
    async_summary = results_dir / "async_results_summary.json"

    if not sync_json.exists() or not async_json.exists():
        print(f"{Colors.RED}ERROR: Results files not found in {results_dir}{Colors.NC}")
        sys.exit(1)

    print(f"\n{Colors.BOLD}Analyzing test results...{Colors.NC}\n")

    # Parse results
    sync_metrics = parse_k6_json(sync_json)
    async_metrics = parse_k6_json(async_json)
    sync_sum = parse_summary_json(sync_summary)
    async_sum = parse_summary_json(async_summary)

    # Print comparisons
    print_comparison_table(sync_metrics, async_metrics)

    if sync_sum and async_sum:
        print_overall_summary(sync_sum, async_sum)

    print_recommendations(sync_metrics, async_metrics)

    # Generate markdown report
    generate_markdown_report(results_dir, load_profile, sync_metrics, async_metrics, sync_sum, async_sum)


if __name__ == "__main__":
    main()
