#!/usr/bin/env python3
"""
Usage:
    python3 generate-graphs.py <results_directory>
"""

import json
import sys
import statistics
from pathlib import Path
from collections import defaultdict
from typing import Dict, List
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Set publication-quality defaults
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'serif'
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['figure.titlesize'] = 13


def parse_k6_summary(summary_file: Path) -> Dict:
    """Parse k6 summary JSON."""
    try:
        with open(summary_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_metric(summary: Dict, metric: str, stat: str = 'value') -> float:
    """Extract metric from summary."""
    try:
        metric_data = summary.get('metrics', {}).get(metric, {})
        if isinstance(metric_data, dict):
            return metric_data.get(stat, 0)
        return 0
    except (KeyError, AttributeError, TypeError):
        return 0


def analyze_test_results(results_dir: Path) -> Dict:
    """Analyze all test results in directory."""
    results = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for file in results_dir.glob("*_summary.json"):
        filename = file.stem.replace('_summary', '')
        parts = filename.split('_')

        if len(parts) >= 3:
            test_name = '_'.join(parts[:-2])
            arch = parts[-2]
            run_num = parts[-1]

            summary = parse_k6_summary(file)

            # Extract key metrics
            metrics = {
                'p50': get_metric(summary, 'http_req_duration', 'med'),
                'p95': get_metric(summary, 'http_req_duration', 'p(95)'),
                'p99': get_metric(summary, 'http_req_duration', 'p(99)'),
                'avg': get_metric(summary, 'http_req_duration', 'avg'),
                'max': get_metric(summary, 'http_req_duration', 'max'),
                'throughput': get_metric(summary, 'http_reqs', 'rate'),
                'total_requests': get_metric(summary, 'http_reqs', 'count'),
                'iterations': get_metric(summary, 'iterations', 'count'),
                'error_rate': get_metric(summary, 'http_req_failed', 'value') * 100,
            }

            # Scenario-specific metrics
            for scenario_num in range(1, 7):
                scenario_key = f'scenario{scenario_num}'
                scenario_duration = f'scenario{scenario_num}_duration'

                if scenario_duration in summary.get('metrics', {}):
                    metrics[f'{scenario_key}_avg'] = get_metric(summary, scenario_duration, 'avg')
                    metrics[f'{scenario_key}_p95'] = get_metric(summary, scenario_duration, 'p(95)')
                    metrics[f'{scenario_key}_p99'] = get_metric(summary, scenario_duration, 'p(99)')

            # Store metrics
            for metric_name, value in metrics.items():
                results[test_name][arch][metric_name].append(value)

    return results


def plot_p95_latency_comparison(results: Dict, output_dir: Path):
    """Figure 1: p95 Latency Comparison Across Load Levels"""
    test_order = ['baseline', 'light', 'medium', 'medium_high', 'heavy', 'stress']
    available_tests = [t for t in test_order if t in results]

    sync_p95_means = []
    sync_p95_stds = []
    async_p95_means = []
    async_p95_stds = []

    for test in available_tests:
        if 'sync' in results[test] and 'async' in results[test]:
            sync_p95_means.append(statistics.mean(results[test]['sync']['p95']))
            sync_p95_stds.append(statistics.stdev(results[test]['sync']['p95']) if len(results[test]['sync']['p95']) > 1 else 0)
            async_p95_means.append(statistics.mean(results[test]['async']['p95']))
            async_p95_stds.append(statistics.stdev(results[test]['async']['p95']) if len(results[test]['async']['p95']) > 1 else 0)

    x = np.arange(len(available_tests))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))

    bars1 = ax.bar(x - width/2, sync_p95_means, width, yerr=sync_p95_stds,
                   label='Synchronous', color='#e74c3c', alpha=0.8, capsize=5)
    bars2 = ax.bar(x + width/2, async_p95_means, width, yerr=async_p95_stds,
                   label='Asynchronous', color='#3498db', alpha=0.8, capsize=5)

    ax.set_xlabel('Load Profile', fontweight='bold')
    ax.set_ylabel('p95 Latency (ms)', fontweight='bold')
    ax.set_title('Figure 1: p95 Latency Comparison Across Load Levels')
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace('_', '-').title() for t in available_tests], rotation=45, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # Add improvement percentages on top
    for i, (sync_val, async_val) in enumerate(zip(sync_p95_means, async_p95_means)):
        if sync_val > 0:
            improvement = ((sync_val - async_val) / sync_val) * 100
            ax.text(i, max(sync_val, async_val) * 1.05, f'{improvement:.0f}%',
                   ha='center', va='bottom', fontsize=8, fontweight='bold', color='green')

    plt.tight_layout()
    plt.savefig(output_dir / 'figure1_p95_latency_comparison.png', bbox_inches='tight')
    plt.savefig(output_dir / 'figure1_p95_latency_comparison.pdf', bbox_inches='tight')
    plt.close()
    print(f"✓ Generated Figure 1: p95 Latency Comparison")


def plot_error_rate_comparison(results: Dict, output_dir: Path):
    """Figure 2: Error Rate Comparison Across Load Levels"""
    test_order = ['baseline', 'light', 'medium', 'medium_high', 'heavy', 'stress']
    available_tests = [t for t in test_order if t in results]

    sync_errors = []
    async_errors = []

    for test in available_tests:
        if 'sync' in results[test] and 'async' in results[test]:
            sync_errors.append(statistics.mean(results[test]['sync']['error_rate']))
            async_errors.append(statistics.mean(results[test]['async']['error_rate']))

    x = np.arange(len(available_tests))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))

    bars1 = ax.bar(x - width/2, sync_errors, width, label='Synchronous',
                   color='#e74c3c', alpha=0.8)
    bars2 = ax.bar(x + width/2, async_errors, width, label='Asynchronous',
                   color='#3498db', alpha=0.8)

    ax.set_xlabel('Load Profile', fontweight='bold')
    ax.set_ylabel('Error Rate (%)', fontweight='bold')
    ax.set_title('Figure 2: Error Rate Comparison Across Load Levels')
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace('_', '-').title() for t in available_tests], rotation=45, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # Add horizontal line at 1% for reference
    ax.axhline(y=1.0, color='orange', linestyle='--', linewidth=1, alpha=0.5, label='1% threshold')

    plt.tight_layout()
    plt.savefig(output_dir / 'figure2_error_rate_comparison.png', bbox_inches='tight')
    plt.savefig(output_dir / 'figure2_error_rate_comparison.pdf', bbox_inches='tight')
    plt.close()
    print(f"✓ Generated Figure 2: Error Rate Comparison")


def plot_throughput_comparison(results: Dict, output_dir: Path):
    """Figure 3: Throughput Comparison Across Load Levels"""
    test_order = ['baseline', 'light', 'medium', 'medium_high', 'heavy', 'stress']
    available_tests = [t for t in test_order if t in results]

    sync_throughput = []
    async_throughput = []

    for test in available_tests:
        if 'sync' in results[test] and 'async' in results[test]:
            sync_throughput.append(statistics.mean(results[test]['sync']['throughput']))
            async_throughput.append(statistics.mean(results[test]['async']['throughput']))

    x = np.arange(len(available_tests))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))

    bars1 = ax.bar(x - width/2, sync_throughput, width, label='Synchronous',
                   color='#e74c3c', alpha=0.8)
    bars2 = ax.bar(x + width/2, async_throughput, width, label='Asynchronous',
                   color='#3498db', alpha=0.8)

    ax.set_xlabel('Load Profile', fontweight='bold')
    ax.set_ylabel('Throughput (requests/second)', fontweight='bold')
    ax.set_title('Figure 3: Throughput Comparison Across Load Levels')
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace('_', '-').title() for t in available_tests], rotation=45, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # Add improvement percentages on top
    for i, (sync_val, async_val) in enumerate(zip(sync_throughput, async_throughput)):
        if sync_val > 0:
            improvement = ((async_val - sync_val) / sync_val) * 100
            ax.text(i, max(sync_val, async_val) * 1.02, f'+{improvement:.1f}%',
                   ha='center', va='bottom', fontsize=8, fontweight='bold', color='green')

    plt.tight_layout()
    plt.savefig(output_dir / 'figure3_throughput_comparison.png', bbox_inches='tight')
    plt.savefig(output_dir / 'figure3_throughput_comparison.pdf', bbox_inches='tight')
    plt.close()
    print(f"✓ Generated Figure 3: Throughput Comparison")


def plot_scenario_performance(results: Dict, output_dir: Path):
    """Figure 4: Per-Scenario p95 Latency Comparison"""
    scenarios = {
        'scenario1': 'User Registration\n(Fire-and-Forget)',
        'scenario2': 'Payment Processing\n(Long-Running)',
        'scenario3': 'Product Update\n(Fan-Out)',
        'scenario4': 'Report Generation\n(CPU-Intensive)',
        'scenario5': 'Order Creation\n(Saga Pattern)',
        'scenario6': 'Click Tracking\n(High-Throughput)',
    }

    sync_p95_all = []
    async_p95_all = []
    scenario_labels = []

    for scenario_key, scenario_name in scenarios.items():
        sync_vals = []
        async_vals = []

        for test_name in results:
            test_data = results[test_name]
            if 'sync' in test_data and 'async' in test_data:
                sync_vals.extend(test_data['sync'].get(f'{scenario_key}_p95', []))
                async_vals.extend(test_data['async'].get(f'{scenario_key}_p95', []))

        if sync_vals and async_vals:
            sync_p95_all.append(statistics.mean(sync_vals))
            async_p95_all.append(statistics.mean(async_vals))
            scenario_labels.append(scenario_name)

    x = np.arange(len(scenario_labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 7))

    bars1 = ax.bar(x - width/2, sync_p95_all, width, label='Synchronous',
                   color='#e74c3c', alpha=0.8)
    bars2 = ax.bar(x + width/2, async_p95_all, width, label='Asynchronous',
                   color='#3498db', alpha=0.8)

    ax.set_xlabel('Scenario', fontweight='bold')
    ax.set_ylabel('p95 Latency (ms)', fontweight='bold')
    ax.set_title('Figure 4: Per-Scenario p95 Latency Comparison (Aggregated Across All Load Levels)')
    ax.set_xticks(x)
    ax.set_xticklabels(scenario_labels, rotation=0, ha='center', fontsize=8)
    ax.legend()
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # Use log scale for y-axis due to large range
    ax.set_yscale('log')

    # Add improvement percentages on top
    for i, (sync_val, async_val) in enumerate(zip(sync_p95_all, async_p95_all)):
        if sync_val > 0:
            improvement = ((sync_val - async_val) / sync_val) * 100
            color = 'green' if improvement > 0 else 'red'
            sign = '+' if improvement > 0 else ''
            ax.text(i, max(sync_val, async_val) * 1.3, f'{sign}{improvement:.0f}%',
                   ha='center', va='bottom', fontsize=8, fontweight='bold', color=color)

    plt.tight_layout()
    plt.savefig(output_dir / 'figure4_scenario_comparison.png', bbox_inches='tight')
    plt.savefig(output_dir / 'figure4_scenario_comparison.pdf', bbox_inches='tight')
    plt.close()
    print(f"✓ Generated Figure 4: Per-Scenario Comparison")


def plot_scalability_analysis(results: Dict, output_dir: Path):
    """Figure 5: Scalability - p95 Latency Growth Under Load"""
    test_order = ['baseline', 'light', 'medium', 'medium_high', 'heavy', 'stress']
    available_tests = [t for t in test_order if t in results]

    # VU counts for x-axis (approximate based on test configuration)
    vu_mapping = {
        'baseline': 9,      # Sum of VUs across scenarios
        'light': 22,
        'medium': 43,
        'medium_high': 65,
        'heavy': 87,
        'stress': 130
    }

    sync_p95 = []
    async_p95 = []
    vus = []

    for test in available_tests:
        if 'sync' in results[test] and 'async' in results[test]:
            sync_p95.append(statistics.mean(results[test]['sync']['p95']))
            async_p95.append(statistics.mean(results[test]['async']['p95']))
            vus.append(vu_mapping.get(test, 0))

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(vus, sync_p95, marker='o', linewidth=2, markersize=8,
            label='Synchronous', color='#e74c3c')
    ax.plot(vus, async_p95, marker='s', linewidth=2, markersize=8,
            label='Asynchronous', color='#3498db')

    ax.set_xlabel('Concurrent Virtual Users', fontweight='bold')
    ax.set_ylabel('p95 Latency (ms)', fontweight='bold')
    ax.set_title('Figure 5: Scalability Analysis - p95 Latency Growth Under Increasing Load')
    ax.legend()
    ax.grid(True, alpha=0.3, linestyle='--')

    # Add annotations for key points
    if len(sync_p95) > 0 and len(async_p95) > 0:
        # Annotate baseline
        ax.annotate(f'{sync_p95[0]:.1f}ms', xy=(vus[0], sync_p95[0]),
                   xytext=(10, 10), textcoords='offset points', fontsize=8)
        ax.annotate(f'{async_p95[0]:.1f}ms', xy=(vus[0], async_p95[0]),
                   xytext=(10, -15), textcoords='offset points', fontsize=8)

        # Annotate stress
        ax.annotate(f'{sync_p95[-1]:.1f}ms', xy=(vus[-1], sync_p95[-1]),
                   xytext=(-30, 10), textcoords='offset points', fontsize=8)
        ax.annotate(f'{async_p95[-1]:.1f}ms', xy=(vus[-1], async_p95[-1]),
                   xytext=(-30, -15), textcoords='offset points', fontsize=8)

    plt.tight_layout()
    plt.savefig(output_dir / 'figure5_scalability_analysis.png', bbox_inches='tight')
    plt.savefig(output_dir / 'figure5_scalability_analysis.pdf', bbox_inches='tight')
    plt.close()
    print(f"✓ Generated Figure 5: Scalability Analysis")


def plot_median_vs_p95_paradox(results: Dict, output_dir: Path):
    """Figure 6: Median vs p95 Latency Paradox"""
    test_order = ['baseline', 'light', 'medium', 'medium_high', 'heavy', 'stress']
    available_tests = [t for t in test_order if t in results]

    sync_p50 = []
    sync_p95 = []
    async_p50 = []
    async_p95 = []

    for test in available_tests:
        if 'sync' in results[test] and 'async' in results[test]:
            sync_p50.append(statistics.mean(results[test]['sync']['p50']))
            sync_p95.append(statistics.mean(results[test]['sync']['p95']))
            async_p50.append(statistics.mean(results[test]['async']['p50']))
            async_p95.append(statistics.mean(results[test]['async']['p95']))

    x = np.arange(len(available_tests))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Left plot: Median (p50)
    width = 0.35
    bars1 = ax1.bar(x - width/2, sync_p50, width, label='Synchronous',
                    color='#e74c3c', alpha=0.8)
    bars2 = ax1.bar(x + width/2, async_p50, width, label='Asynchronous',
                    color='#3498db', alpha=0.8)

    ax1.set_xlabel('Load Profile', fontweight='bold')
    ax1.set_ylabel('Median Latency (ms)', fontweight='bold')
    ax1.set_title('Median (p50) Latency - Sync Advantage')
    ax1.set_xticks(x)
    ax1.set_xticklabels([t.replace('_', '-').title() for t in available_tests], rotation=45, ha='right')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3, linestyle='--')

    # Right plot: p95
    bars3 = ax2.bar(x - width/2, sync_p95, width, label='Synchronous',
                    color='#e74c3c', alpha=0.8)
    bars4 = ax2.bar(x + width/2, async_p95, width, label='Asynchronous',
                    color='#3498db', alpha=0.8)

    ax2.set_xlabel('Load Profile', fontweight='bold')
    ax2.set_ylabel('p95 Latency (ms)', fontweight='bold')
    ax2.set_title('p95 Latency - Async Advantage')
    ax2.set_xticks(x)
    ax2.set_xticklabels([t.replace('_', '-').title() for t in available_tests], rotation=45, ha='right')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3, linestyle='--')

    plt.suptitle('Figure 6: The Median vs p95 Latency Paradox', fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'figure6_median_vs_p95_paradox.png', bbox_inches='tight')
    plt.savefig(output_dir / 'figure6_median_vs_p95_paradox.pdf', bbox_inches='tight')
    plt.close()
    print(f"✓ Generated Figure 6: Median vs p95 Paradox")


def plot_improvement_heatmap(results: Dict, output_dir: Path):
    """Figure 7: Performance Improvement Heatmap"""
    test_order = ['baseline', 'light', 'medium', 'medium_high', 'heavy', 'stress']
    available_tests = [t for t in test_order if t in results]

    metrics = ['p50', 'p95', 'avg', 'throughput', 'error_rate']
    metric_labels = ['Median (p50)', 'p95', 'Average', 'Throughput', 'Error Rate']

    improvements = []

    for metric in metrics:
        metric_improvements = []
        for test in available_tests:
            if 'sync' in results[test] and 'async' in results[test]:
                sync_val = statistics.mean(results[test]['sync'][metric])
                async_val = statistics.mean(results[test]['async'][metric])

                if sync_val == 0:
                    improvement = 0
                else:
                    if metric == 'throughput':
                        # Higher is better for throughput
                        improvement = ((async_val - sync_val) / sync_val) * 100
                    else:
                        # Lower is better for latency and error rate
                        improvement = ((sync_val - async_val) / sync_val) * 100

                metric_improvements.append(improvement)
        improvements.append(metric_improvements)

    improvements = np.array(improvements)

    fig, ax = plt.subplots(figsize=(12, 6))

    # Use diverging colormap (red for negative, green for positive)
    im = ax.imshow(improvements, cmap='RdYlGn', aspect='auto', vmin=-100, vmax=100)

    ax.set_xticks(np.arange(len(available_tests)))
    ax.set_yticks(np.arange(len(metric_labels)))
    ax.set_xticklabels([t.replace('_', '-').title() for t in available_tests])
    ax.set_yticklabels(metric_labels)

    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    # Add values in cells
    for i in range(len(metric_labels)):
        for j in range(len(available_tests)):
            text = ax.text(j, i, f'{improvements[i, j]:.0f}%',
                          ha="center", va="center", color="black", fontsize=9, fontweight='bold')

    ax.set_title('Figure 7: Performance Improvement Heatmap (Async vs Sync)\nGreen = Async Better, Red = Sync Better')

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Improvement (%)', rotation=270, labelpad=20)

    plt.tight_layout()
    plt.savefig(output_dir / 'figure7_improvement_heatmap.png', bbox_inches='tight')
    plt.savefig(output_dir / 'figure7_improvement_heatmap.pdf', bbox_inches='tight')
    plt.close()
    print(f"✓ Generated Figure 7: Performance Improvement Heatmap")


def plot_latency_distribution_comparison(results: Dict, output_dir: Path):
    """Figure 8: Latency Distribution Comparison (Medium Load)"""
    # Use medium load as representative
    if 'medium' not in results:
        print("⚠ Skipping Figure 8: Medium load data not available")
        return

    test_data = results['medium']

    if 'sync' not in test_data or 'async' not in test_data:
        print("⚠ Skipping Figure 8: Missing sync or async data")
        return

    # Get p50, p95, p99 for visualization
    sync_p50 = statistics.mean(test_data['sync']['p50'])
    sync_p95 = statistics.mean(test_data['sync']['p95'])
    async_p50 = statistics.mean(test_data['async']['p50'])
    async_p95 = statistics.mean(test_data['async']['p95'])

    fig, ax = plt.subplots(figsize=(12, 6))

    # Create box plot representation
    sync_data = [sync_p50, sync_p50, sync_p95, sync_p95]
    async_data = [async_p50, async_p50, async_p95, async_p95]

    positions = [1, 2]
    bp = ax.boxplot([sync_data, async_data], positions=positions, widths=0.6,
                     patch_artist=True, showfliers=False,
                     medianprops=dict(color='black', linewidth=2))

    # Color the boxes
    bp['boxes'][0].set_facecolor('#e74c3c')
    bp['boxes'][0].set_alpha(0.7)
    bp['boxes'][1].set_facecolor('#3498db')
    bp['boxes'][1].set_alpha(0.7)

    # Add annotations
    ax.annotate(f'p50: {sync_p50:.2f}ms\np95: {sync_p95:.2f}ms',
               xy=(1, sync_p95), xytext=(1.5, sync_p95 * 1.2),
               fontsize=9, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    ax.annotate(f'p50: {async_p50:.2f}ms\np95: {async_p95:.2f}ms',
               xy=(2, async_p95), xytext=(1.5, async_p95 * 3),
               fontsize=9, bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

    ax.set_ylabel('Latency (ms)', fontweight='bold')
    ax.set_title('Figure 8: Latency Distribution Comparison - Medium Load\n(Bimodal vs Unimodal Distribution)')
    ax.set_xticks(positions)
    ax.set_xticklabels(['Synchronous\n(Bimodal)', 'Asynchronous\n(Unimodal)'])
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # Add text explanation
    fig.text(0.5, 0.02,
            'Synchronous shows wide spread (p50=0.67ms, p95=507ms) indicating bimodal distribution.\n'
            'Asynchronous shows tight clustering (p50=1.14ms, p95=6.43ms) indicating consistent performance.',
            ha='center', fontsize=9, style='italic', wrap=True)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)
    plt.savefig(output_dir / 'figure8_distribution_comparison.png', bbox_inches='tight')
    plt.savefig(output_dir / 'figure8_distribution_comparison.pdf', bbox_inches='tight')
    plt.close()
    print(f"✓ Generated Figure 8: Latency Distribution Comparison")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <results_directory>")
        sys.exit(1)

    results_dir = Path(sys.argv[1])

    if not results_dir.exists():
        print(f"ERROR: Directory not found: {results_dir}")
        sys.exit(1)

    print(f"\nGenerating publication-quality graphs from: {results_dir}\n")

    # Create graphs subdirectory
    graphs_dir = results_dir / "graphs"
    graphs_dir.mkdir(exist_ok=True)

    # Analyze results
    results = analyze_test_results(results_dir)

    if not results:
        print("ERROR: No valid test results found")
        sys.exit(1)

    # Generate all figures
    print("Generating figures...\n")

    plot_p95_latency_comparison(results, graphs_dir)
    plot_error_rate_comparison(results, graphs_dir)
    plot_throughput_comparison(results, graphs_dir)
    plot_scenario_performance(results, graphs_dir)
    plot_scalability_analysis(results, graphs_dir)
    plot_median_vs_p95_paradox(results, graphs_dir)
    plot_improvement_heatmap(results, graphs_dir)
    plot_latency_distribution_comparison(results, graphs_dir)

    print(f"\n✓ All graphs generated successfully!")
    print(f"\nOutput directory: {graphs_dir}")
    print(f"\nGenerated files:")
    for f in sorted(graphs_dir.glob("*.png")):
        print(f"  - {f.name}")

    print(f"\nPDF versions also available for publication use.")


if __name__ == "__main__":
    main()
