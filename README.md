# DNS-Benchmarking-Tool
A lightweight benchmarking tool for evaluating authoritative DNS server performance.

### Features
- Parallel query execution with configurable worker count via multiprocessing
- C query engine for optimized performance (UDP only)
- UDP and TCP support
- Latency measurement
- External file output in multiple formats (.json, .db, .html, .csv)
- Configurable test scenarios via YAML configs

### Requirements
- Python 3.10+
- A C compiler (gcc/clang)

**Compiling the C engine**
```bash
cd src/dnsbench/
gcc -O2 -shared -fPIC -o worker.so worker.c
```

### YAML configs
**Example config**

```YAML
# config/example.yaml
host:
  server: 127.0.0.1
  port: 5301
  domain: bench.test
args:
  protocol: udp
  workers: 8
mode:
  count: 50000
rdatatypes:
  - A
  - AAAA
  - MX
  - NS
```