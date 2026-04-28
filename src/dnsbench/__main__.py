import argparse
import yaml
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
    parser.add_argument("--server", "-s", default=None)
    parser.add_argument("--protocol", "-P", default="udp")
    parser.add_argument("--domain", "-d", default=None)
    parser.add_argument("--mode", "-m", default="quick_run", choices=["quick_run", "stress_run", "mixed_run"])
    parser.add_argument("--port", "-p", type=int, default=53)
    parser.add_argument("--queries", "-q", type=int, default=10000)
    parser.add_argument("--workers", "-w", type=int, default=4)
    parser.add_argument("--verbose", "-v", action='store_true', help="Print verbose output")
    parser.add_argument("--duration", "-D", type=int, help="Run for N seconds in duration mode")
    parser.add_argument("--config", "-c", )
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
        if args.workers != 8:
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
            "queries": "args.queries",
            "duration": args.duration if args.duration else 0,
        }

    messages, rdtype_names = build_messages(config)
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
