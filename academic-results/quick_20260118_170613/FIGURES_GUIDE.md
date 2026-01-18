# Figures Guide for Academic Paper

This document describes all generated figures and provides suggested placement and captions for your Results section.

## Generated Figures Overview

All figures are available in both **PNG (300 DPI)** and **PDF (vector)** formats in the `graphs/` directory:
- PNG files: For digital viewing and presentations
- PDF files: For publication submission (vector graphics scale perfectly)

---

## Figure Descriptions and Suggested Captions

### Figure 1: p95 Latency Comparison Across Load Levels
**File**: `figure1_p95_latency_comparison.png` | `figure1_p95_latency_comparison.pdf`

**Description**: Bar chart comparing p95 latency between synchronous and asynchronous architectures across all six load profiles. Shows dramatic improvement in tail latency for async, with percentages displayed above bars.

**Suggested Caption**:
> **Figure 1: p95 Latency Comparison Across Load Levels.** The asynchronous architecture (blue) demonstrates substantial p95 latency improvements over the synchronous architecture (red) across all load profiles, ranging from 66.6% at baseline to 98.7% under medium-to-stress loads. Error bars represent standard deviation across two experimental runs. Improvement percentages are displayed above the bars.

**Where to Use**: In section discussing overall performance comparison (Table 1 area).

---

### Figure 2: Error Rate Comparison Across Load Levels
**File**: `figure2_error_rate_comparison.png` | `figure2_error_rate_comparison.pdf`

**Description**: Bar chart showing error rates for sync (3.51-7.55%) vs async (0.00%) across all load levels. Includes a 1% threshold reference line.

**Suggested Caption**:
> **Figure 2: Error Rate Comparison Across Load Levels.** The synchronous architecture (red) exhibits error rates increasing from 3.51% at baseline to 7.55% under stress load, while the asynchronous architecture (blue) maintains 0% error rate across all test scenarios. The orange dashed line indicates a 1% error rate threshold for reference. This represents a 100% reduction in request failures.

**Where to Use**: In section discussing reliability and error rate disparity (Table 3 area).

---

### Figure 3: Throughput Comparison Across Load Levels
**File**: `figure3_throughput_comparison.png` | `figure3_throughput_comparison.pdf`

**Description**: Bar chart comparing requests per second achieved by both architectures. Shows async achieving 4-11% higher throughput.

**Suggested Caption**:
> **Figure 3: Throughput Comparison Across Load Levels.** The asynchronous architecture (blue) consistently achieves 4-11% higher throughput than the synchronous architecture (red), with the advantage increasing under heavier loads. At stress levels, async processes 420.5 req/s compared to sync's 380.0 req/s, demonstrating superior resource utilization through non-blocking I/O.

**Where to Use**: In throughput analysis section (Table 4 area).

---

### Figure 4: Per-Scenario p95 Latency Comparison
**File**: `figure4_scenario_comparison.png` | `figure4_scenario_comparison.pdf`

**Description**: Bar chart showing p95 latency for all six scenarios, aggregated across all load levels. Uses logarithmic scale due to wide range. Shows improvement percentages for each scenario.

**Suggested Caption**:
> **Figure 4: Per-Scenario p95 Latency Comparison (Aggregated Across All Load Levels).** Performance comparison across six microservice patterns. Asynchronous architecture (blue) shows strongest advantages in Payment Processing (99.8%), User Registration (98.0%), and Report Generation (94.9%), while Click Tracking favors synchronous implementation (-49.7%). Note: y-axis uses logarithmic scale due to wide latency range. Improvement percentages indicate relative performance gain.

**Where to Use**: In scenario-specific performance analysis section, as overview before detailed scenario discussions.

---

### Figure 5: Scalability Analysis - p95 Latency Growth Under Increasing Load
**File**: `figure5_scalability_analysis.png` | `figure5_scalability_analysis.pdf`

**Description**: Line plot showing how p95 latency evolves as concurrent users increase from 9 to 130. Demonstrates catastrophic degradation for sync vs graceful degradation for async.

**Suggested Caption**:
> **Figure 5: Scalability Analysis - p95 Latency Growth Under Increasing Load.** As concurrent virtual users increase from 9 (baseline) to 130 (stress), the synchronous architecture (red) exhibits catastrophic non-linear degradation (16.99ms → 510.60ms, +2,904%), while the asynchronous architecture (blue) shows graceful linear degradation (5.67ms → 7.07ms, +25%). Key data points are annotated. This divergent scaling behavior indicates a saturation point in synchronous architecture around 43 concurrent users (medium load).

**Where to Use**: In scalability analysis section, demonstrating the fundamental difference in scaling characteristics.

---

### Figure 6: The Median vs p95 Latency Paradox
**File**: `figure6_median_vs_p95_paradox.png` | `figure6_median_vs_p95_paradox.pdf`

**Description**: Dual bar chart showing median (left) and p95 (right) latencies side by side. Illustrates the paradox where sync has better median but much worse p95.

**Suggested Caption**:
> **Figure 6: The Median vs p95 Latency Paradox.** Left panel shows synchronous architecture (red) achieving superior median latency (0.67-0.78ms) compared to asynchronous (blue, 1.10-1.50ms). Right panel reveals the paradox: at p95, asynchronous dramatically outperforms synchronous (6-7ms vs 500+ms). This demonstrates bimodal distribution in synchronous systems (fast successes vs slow timeouts) versus unimodal consistent performance in asynchronous systems.

**Where to Use**: In the "Median vs p95 Latency Paradox" section to visually demonstrate this counterintuitive finding.

---

### Figure 7: Performance Improvement Heatmap
**File**: `figure7_improvement_heatmap.png` | `figure7_improvement_heatmap.pdf`

**Description**: Heatmap showing improvement percentages across five metrics (p50, p95, avg, throughput, error rate) and six load levels. Green indicates async advantage, red indicates sync advantage.

**Suggested Caption**:
> **Figure 7: Performance Improvement Heatmap (Async vs Sync).** Comprehensive visualization of asynchronous performance advantage across multiple metrics and load levels. Green cells indicate asynchronous superiority, red cells indicate synchronous advantage. The heatmap reveals that p95, average latency, and error rate show strongest async advantages (dark green), while median (p50) favors sync at lower loads (red). Throughput consistently favors async (light green). Percentages indicate relative improvement.

**Where to Use**: As a comprehensive summary visualization, possibly at the end of the overall performance comparison section or in the discussion.

---

### Figure 8: Latency Distribution Comparison - Medium Load
**File**: `figure8_distribution_comparison.png` | `figure8_distribution_comparison.pdf`

**Description**: Box plot representation showing the distribution spread for sync (bimodal) vs async (unimodal). Includes annotations with p50 and p95 values.

**Suggested Caption**:
> **Figure 8: Latency Distribution Comparison - Medium Load (Bimodal vs Unimodal Distribution).** Box plot representation illustrating fundamentally different latency distributions. Synchronous architecture exhibits wide spread between p50 (0.67ms) and p95 (507ms), indicating bimodal distribution with fast-path successes and slow-path failures. Asynchronous architecture shows tight clustering (p50=1.14ms, p95=6.43ms), indicating consistent unimodal performance. The synchronous p50/p95 ratio of 0.13% compared to async's 17.7% demonstrates extreme tail latency in synchronous systems.

**Where to Use**: In the "Median vs p95 Latency Paradox" section to complement the explanation of distribution differences.

---

## Suggested Figure Placement in Results Section

Based on the structure of your Results section, here's the recommended placement order:

1. **After Table 1** (Overall Performance): Insert **Figure 1** (p95 latency comparison)

2. **After Table 3** (Error Rates): Insert **Figure 2** (error rate comparison)

3. **After Table 4** (Throughput): Insert **Figure 3** (throughput comparison)

4. **Before Scenario-Specific Sections**: Insert **Figure 4** (per-scenario overview)

5. **In Scalability Analysis Section**: Insert **Figure 5** (scalability analysis)

6. **In Median vs p95 Paradox Section**: Insert **Figure 6** (paradox visualization) and **Figure 8** (distribution comparison)

7. **In Discussion or Summary**: Insert **Figure 7** (comprehensive heatmap)

---

## Figure Sizing Recommendations

For publication in academic journals:

- **Single-column figures**: Figures 1, 2, 3, 5, 8 (can fit in single column)
- **Double-column figures**: Figures 4, 6, 7 (require full page width)

For your thesis or conference paper:
- All figures are designed at 300 DPI and will print clearly at sizes up to 10-12 inches wide
- PDF versions are vector graphics and scale infinitely without quality loss

---

## Color Scheme

All figures use a consistent color scheme:
- **Synchronous**: Red (#e74c3c) - indicates "danger" or issues
- **Asynchronous**: Blue (#3498db) - indicates "stable" or positive
- **Improvement indicators**: Green (positive) or Red (negative)
- **Grid lines**: Light gray with dashed lines for readability

This color scheme is:
- Colorblind-friendly (red-blue contrast)
- Print-friendly (differentiable in grayscale)
- Professionally styled for academic publications

---

## LaTeX Integration Example

If you're using LaTeX for your paper, here's how to include these figures:

```latex
\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.9\textwidth]{graphs/figure1_p95_latency_comparison.pdf}
    \caption{p95 Latency Comparison Across Load Levels. The asynchronous architecture (blue) demonstrates substantial p95 latency improvements over the synchronous architecture (red) across all load profiles, ranging from 66.6\% at baseline to 98.7\% under medium-to-stress loads.}
    \label{fig:p95_comparison}
\end{figure}
```

For referencing in text:
```latex
As shown in Figure~\ref{fig:p95_comparison}, the asynchronous architecture...
```

---

## Microsoft Word Integration

For Word documents:
1. Insert PNG versions for best compatibility
2. Right-click → "Wrap Text" → "In line with text"
3. Add caption using "Insert Caption" feature
4. Enable "Update field" for automatic figure numbering

---

## High-Resolution Export

All figures are generated at 300 DPI, which meets publication standards for:
- IEEE journals and conferences
- ACM publications
- Springer journals
- Elsevier journals
- Most other academic venues

If you need different DPI or sizes, you can modify the script's settings at the top:
```python
plt.rcParams['figure.dpi'] = 300  # Change this value
plt.rcParams['savefig.dpi'] = 300  # Change this value
```

---

## Regenerating Figures

To regenerate all figures with different settings:

```bash
python3 generate-graphs.py academic-results/quick_20260118_170613
```

The script will:
- Parse all test result files
- Calculate statistics across runs
- Generate all 8 figures
- Save in both PNG and PDF formats

---

## Figure Quality Checklist

All generated figures include:
- ✅ Clear, readable axis labels
- ✅ Descriptive titles
- ✅ Legends explaining color coding
- ✅ Grid lines for easier value reading
- ✅ Annotations for key data points
- ✅ Error bars where applicable
- ✅ Consistent color scheme
- ✅ Professional academic styling
- ✅ High resolution (300 DPI)
- ✅ Vector format available (PDF)

---

## Notes for Paper Submission

1. **Always submit PDF versions** for final publication - they're vector graphics and will scale perfectly
2. **Check journal requirements** - some journals require TIFF or EPS formats, which can be exported from the PDFs
3. **Figure numbering** - Update figure numbers if you add/remove figures from your paper
4. **Color printing costs** - If submitting to a journal with color printing fees, all figures work well in grayscale
5. **Accessibility** - Add alt-text descriptions when publishing online

---

## Summary

You now have **8 publication-ready figures** covering:
1. ✅ Overall p95 latency comparison
2. ✅ Error rate reliability comparison
3. ✅ Throughput comparison
4. ✅ Per-scenario performance breakdown
5. ✅ Scalability and degradation analysis
6. ✅ Median vs p95 paradox visualization
7. ✅ Comprehensive improvement heatmap
8. ✅ Distribution comparison (bimodal vs unimodal)

All figures are professionally styled, publication-ready, and directly support the findings in your Results section.
