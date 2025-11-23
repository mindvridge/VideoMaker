# Load Testing with Locust

This directory contains load testing configuration for the Video Generation API.

## Installation

```bash
pip install locust
```

## Running Load Tests

### Basic Usage

```bash
# Start Locust with web UI
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Open browser at http://localhost:8089
```

### Headless Mode

```bash
# Run without web UI
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --headless \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m
```

### Command Line Options

- `--users`: Total number of simulated users
- `--spawn-rate`: Users to spawn per second
- `--run-time`: Test duration (e.g., 5m, 1h)
- `--headless`: Run without web UI
- `--csv`: Export results to CSV files

## User Types

### VideoGenUser
Full simulation of video generation workflow:
- Health checks (high frequency)
- Model listing (medium frequency)
- Video generation submission (low frequency)
- Task status checking (medium frequency)

### QuickUser
Read-only operations only:
- Health checks
- Model listing
- Root endpoint

### StressTestUser
Aggressive stress testing:
- Rapid fire requests
- Minimal wait time

## Test Scenarios

### Scenario 1: Normal Load
```bash
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --headless \
    --users 50 \
    --spawn-rate 5 \
    --run-time 10m
```

### Scenario 2: Peak Load
```bash
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --headless \
    --users 200 \
    --spawn-rate 20 \
    --run-time 5m
```

### Scenario 3: Stress Test
```bash
locust -f tests/load/locustfile.py StressTestUser \
    --host=http://localhost:8000 \
    --headless \
    --users 500 \
    --spawn-rate 50 \
    --run-time 2m
```

## Interpreting Results

### Key Metrics

- **Requests per second (RPS)**: Throughput of the system
- **Response time (median, p95, p99)**: Latency distribution
- **Failure rate**: Percentage of failed requests
- **Users**: Current number of simulated users

### Target Performance

| Metric | Target |
|--------|--------|
| RPS | > 100 for read operations |
| p95 Response Time | < 500ms for health/models |
| p95 Response Time | < 2000ms for generation submit |
| Failure Rate | < 1% (excluding rate limits) |

## Distributed Testing

For larger load tests, run in distributed mode:

### Master
```bash
locust -f tests/load/locustfile.py --master
```

### Workers
```bash
locust -f tests/load/locustfile.py --worker --master-host=<master-ip>
```

## CI Integration

Add to GitHub Actions:

```yaml
- name: Run Load Tests
  run: |
    pip install locust
    locust -f tests/load/locustfile.py \
      --host=http://localhost:8000 \
      --headless \
      --users 10 \
      --spawn-rate 2 \
      --run-time 1m \
      --csv=loadtest
```

## Troubleshooting

### Rate Limiting
If you see many 429 responses, this is expected behavior from rate limiting.
For load testing, you may want to:
1. Increase rate limits temporarily
2. Use `RATE_LIMIT_ENABLED=false`

### Connection Errors
If you see connection errors:
1. Check if the API server is running
2. Verify the host URL is correct
3. Check firewall settings

### Memory Issues
For large tests:
1. Use distributed mode with multiple workers
2. Reduce logging verbosity
3. Monitor system resources
