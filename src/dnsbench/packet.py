import dns.message
import dns.query
import dns.rdatatype
import dns.flags
import dns.edns
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import argparse

# target protocol class
class Protocol(Enum):
    UDP = "udp"
    TCP = "tcp"


@dataclass(frozen=True)
class QueryConfig:
    qname: str
    rdatatype: str
    protocol: Protocol
    rd_flag: bool
    cd_flag: bool
    do_flag: bool

# user arguments
parser = argparse.ArgumentParser()
parser.add_argument("--server", required=True)
parser.add_argument("--protocol", required=True)
parser.add_argument("--domain", required=True)
parser.add_argument("--mode", required=True)
parser.add_argument("--port", type=int, required=True)
parser.add_argument("--duration", type=int, required=True)
args = parser.parse_args()

# PRESET modes
preset = {
    "quick_run": {
        "rdatatypes": ["A"],
        "domain": f"{args.domain}",
        "server": f"{args.server}",
        "port": args.port,
    },
    "stress_run": {
        "rdatatype": ["A", "AAAA", "NS"],
    },
}

def query_crafter(config: QueryConfig):
    # build DNS queries
    ...

def query_from_args(mode: str):
    results = []
    config = preset[mode]
    print(f"mode: {mode}")
    print(f"config: {config}")
    for rdtype in config["rdatatypes"]: 
        msg = dns.message.make_query(
            qname=config["domain"],
            rdtype=dns.rdatatype.from_text(rdtype),
            use_edns=True,
            payload=1232,
        )
        msg.flags &= ~dns.flags.RD
        try:
            response = dns.query.udp(msg, config["server"], port=config["port"], timeout=5.0)
            print(response.to_text())
            results.append({
                "rdtype":rdtype,
                "rcode": response.rcode(),
                "latency": response.time,
                "answer_count": len(response.answer),
            })
        except dns.exception.Timeout:
            print(f"timeout querying {rdtype}")
        except Exception as e:
            print(f"error: {e}")
    for r in results:
        print(r)
    return results




query_from_args("quick_run")
