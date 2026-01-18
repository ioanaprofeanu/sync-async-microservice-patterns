# Sync vs Async Microservices Performance Analysis

**Generated:** 2026-01-18 18:29:32

## Executive Summary

- **Overall p95 Latency Improvement:** 98.1%
- **Sync Average p95:** 346.40ms
- **Async Average p95:** 6.41ms

## Detailed Results

### Performance by Load Level

| Load | Sync p95 (mean±std) | Async p95 (mean±std) | Improvement |
|------|---------------------|----------------------|-------------|
| baseline | 16.99ms ± 1.56ms | 5.67ms ± 704.21µs | +66.6% |
| light | 25.86ms ± 211.46µs | 5.94ms ± 101.89µs | +77.0% |
| medium | 507.53ms ± 596.02µs | 6.43ms ± 373.21µs | +98.7% |
| medium_high | 509.10ms ± 161.75µs | 6.25ms ± 177.55µs | +98.8% |
| heavy | 508.31ms ± 485.68µs | 7.09ms ± 315.05µs | +98.6% |
| stress | 510.60ms ± 82.91µs | 7.07ms ± 21.57µs | +98.6% |

### Scenario Analysis

#### User Registration

- **Sync p95:** 518.27ms ± 2.71ms
- **Async p95:** 10.40ms ± 1.29ms
- **Improvement:** 98.0%

#### Payment Processing

- **Sync p95:** 2.01s ± 973.13µs
- **Async p95:** 4.55ms ± 548.65µs
- **Improvement:** 99.8%

#### Product Update

- **Sync p95:** 23.17ms ± 4.48ms
- **Async p95:** 10.57ms ± 1.68ms
- **Improvement:** 54.4%

#### Report Generation

- **Sync p95:** 10.22s ± 228.82ms
- **Async p95:** 523.23ms ± 169.04ms
- **Improvement:** 94.9%

#### Order Creation

- **Sync p95:** 34.24ms ± 4.70ms
- **Async p95:** 7.51ms ± 908.47µs
- **Improvement:** 78.1%

#### Click Tracking

- **Sync p95:** 1.67ms ± 842.14µs
- **Async p95:** 2.51ms ± 266.11µs
- **Improvement:** -49.7%

## Conclusions

1. Asynchronous architecture demonstrates significant performance advantages
2. Benefits are most pronounced in I/O-bound and long-running operations
3. Error rates remain low (<1%) for async under all tested loads
4. Recommend async for production systems with moderate to high traffic

