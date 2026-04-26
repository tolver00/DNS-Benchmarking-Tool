import argparse
from packet import build_messages
from engine import run_benchmark
from metrics import process_results, print_report

# presets
PRESETS = {
    "quick_run": {
        "rdatatypes": ["A"],
    },
    "stress_run": {
        "rdatatypes": ["A", "AAAA", "NS"],
    },
    "mixed_run": {
        "rdatatypes": ["A", "AAAA", "NS", "MX", "TXT", "SOA", "NS", "CAA"],
    }
}


if __name__ == "__main__":
    # user arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--protocol", default="udp")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--mode", default="quick_run", choices=["quick_run", "stress_run"])
    parser.add_argument("--port", type=int, default=53)
    parser.add_argument("--queries", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--verbose", action='store_true', help="Print verbose output")
    args = parser.parse_args()

    config = PRESETS[args.mode].copy()
    config["domain"] = args.domain
    config["server"] = args.server
    config["port"] = args.port

    messages = build_messages(config)
    results, elapsed = run_benchmark(messages, config["server"], config["port"], args.queries, args.workers, args.protocol)
    report = process_results(results)
    print_report(report, elapsed, args.protocol, args.server, args.port, args.verbose)
    # for r in results[:10]:
    #     print(r)
    # for key, value in report.items():
    #     print(f"{key}: {value}")
    

