import argparse
import yaml
from packet import build_messages
from engine import run_benchmark, run_benchmark_native
from metrics import process_results, print_report
from output import write_csv, write_json, write_sqlite, write_html

# presets
PRESETS = {
    "quick_run": {
        "rdatatypes": ["A"],
    },
    "stress_run": {
        "rdatatypes": ["A", "AAAA", "NS"],
    },
    "mixed_run": {
        "rdatatypes": ["A", "AAAA", "MX", "TXT", "SOA", "NS", "CAA"],
    }
}

def load_yaml_config(path):
    config = {}
    with open(path) as f:
        raw = yaml.safe_load(f)

    config = {
        "server": raw["host"]["server"],
        "port": raw["host"].get("port", 53),
        "domain": raw["host"]["domain"],
        "protocol": raw["args"].get("protocol", "udp"),
        "workers": raw["args"].get("workers", 8),
        "rdatatypes": raw["rdatatypes"],
    }

    if "duration" in raw["mode"]:
        config["exec_mode"] = "duration"
        config["duration"] = raw["mode"]["duration"]
    elif "count" in raw["mode"]:
        config["exec_mode"] = "count"
        config["queries"] = raw["mode"]["count"]
    return config


if __name__ == "__main__":
    # user arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", "-s", default=None, help="Target DNS server IP address")
    parser.add_argument("--protocol", "-P", default="udp", help="Network protocol to target (defaults to UDP)")
    parser.add_argument("--domain", "-d", default=None, help="Target domain to query")
    parser.add_argument("--mode", "-m", default="quick_run", help="Mode presets for test runs", choices=["quick_run", "stress_run", "mixed_run"])
    parser.add_argument("--port", "-p", type=int, default=53, help="Target port (defaults to 53)")
    parser.add_argument("--queries", "-q", type=int, default=10000, help="Amount of queries executed in run (defaults to 10000)")
    parser.add_argument("--workers", "-w", type=int, default=4, help="Amount of workers to execute queries (defaults to 4). See documentation for explanation of setting")
    parser.add_argument("--verbose", "-v", action='store_true', help="Print verbose output")
    parser.add_argument("--duration", "-D", type=int, help="Run for N seconds in duration mode")
    parser.add_argument("--output", "-o", type=str, help="Output to file in PATH (.json, .csv, .db)")
    parser.add_argument("--config", "-c", help="Point to YAML config in PATH")
    parser.add_argument("--native", "-n", action="store_true", help="Running in native will increase performance and QPS (only works with UDP)")
    args = parser.parse_args()

    # config parsing
    if args.config:
        config = load_yaml_config(args.config)
        if args.server:
            config["server"] = args.server
        if args.domain:
            config["domain"] = args.domain
        if args.port != 53:
            config["port"] = args.port
        if args.protocol != "udp":
            config["protocol"] = args.protocol
        if args.workers != 4:
            config["workers"] = args.workers
        if args.duration:
            config["exec_mode"] = "duration"
            config["duration"] = args.duration
    else:
        preset = PRESETS[args.mode]
        config = {
            "server": args.server,
            "port": args.port,
            "domain": args.domain,
            "protocol": args.protocol,
            "workers": args.workers,
            "rdatatypes": preset["rdatatypes"],
            "exec_mode": "duration" if args.duration else "count",
            "queries": args.queries,
            "duration": args.duration if args.duration else 0,
        }

    messages, rdtype_names = build_messages(config)

    # run type
    if args.native:
        results, elapsed = run_benchmark_native(
            messages,
            config["server"],
            config["port"],
            config.get("queries", 0),
            config["workers"],
            )
    else:
        results, elapsed = run_benchmark(
            messages,
            config["server"],
            config["port"],
            config.get("queries", 0),
            config["workers"],
            config["protocol"],
            mode=config["exec_mode"],
            duration=config.get("duration", 0)
        )
    report = process_results(results, rdtype_names)
    print_report(report, elapsed, config["protocol"], config["server"], config["port"], args.verbose)

    # output to file
    if args.output:
        if args.output.endswith(".json"):
            write_json(report, elapsed, config, args.output)
        elif args.output.endswith(".csv"):
            write_csv(report, elapsed, config, args.output)
        elif args.output.endswith(".db"):
            write_sqlite(report, elapsed, config, rdtype_names, results, args.output)
        elif args.output.endswith(".html"):
            write_html(report, elapsed, config, rdtype_names, results, args.output)
    

    
