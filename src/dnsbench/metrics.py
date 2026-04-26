import statistics

def process_results(results: list[dict], rdtype_names: list[str]) -> dict:
    success = []
    error = []
    for r in results:
        if "error" not in r:
            success.append(r)
        else:
            error.append(r)

    # print(f"success list: {success}")

    latencies = []
    for r in success:
        latencies.append(r["latency"])

    latencies.sort()
    report = {
        "total_queries": len(results),
        "successful": len(success),
        "errors": len(error),
        "error_rate": len(error) / len(results),
    }

    if latencies:
        report["latency"] = {
            "min": latencies[0],
            "max": latencies[-1],
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "p95": latencies[int(len(latencies) * 0.95)],
            "p99": latencies[int(len(latencies) * 0.99)],
        }
    rcodes = {}
    for r in success:
        code = r["rcode"]
        rcodes[code] = rcodes.get(code, 0) + 1
    report["rcodes"] = rcodes

    per_type = {}
    for r in success:
        name = rdtype_names[r["msg_index"]]
        if name not in per_type:
            per_type[name] = []
        per_type[name].append(r["latency"])
    
    # per record stats
    type_stats = {}
    for name, lats in per_type.items():
        lats.sort()
        type_stats[name] = {
            "count": len(lats),
            "mean": statistics.mean(lats),
            "p95": lats[int(len(lats) * 0.95)],
        }
    report["per_type"] = type_stats
    
    return report
        
def print_report(report: dict, elapsed: float, protocol: str, server: str, port: int, verbose: bool = False):
    total = report["total_queries"]
    if elapsed > 0:
        qps = total / elapsed
    else:
        qps = 0.0


    ## format output
    print("\n====================================================")
    print("|               DNS Benchmark Results                |")
    print("======================================================")
    print(f"Target:         {server}: {port}")
    print(f"Protocol:       {protocol.upper()}")
    print(f"Total Quries:   {total}")
    print(f"Successful:     {report['successful']}")
    print(f"Errors:         {report['errors']}")
    print(f"Error Rate:     {report['error_rate']:.2%}")
    print(f"Duration:       {elapsed:.2f}s")
    print(f"Effective QPS:  {qps:.1f}")

    if "latency" in report:
        lat = report["latency"]
        print("=================================================")
        print("Latnecy (ms)")
        print(f"    Min:    {lat['min']*1000:.3f}")
        print(f"    Max:    {lat['max']*1000:.3f}")
        print(f"    Mean:   {lat['mean']*1000:.3f}")
        print(f"    Median: {lat['median']*1000:.3f}")
        print(f"    P95:    {lat['p95']*1000:.3f}")
        print(f"    P99:    {lat['p99']*1000:.3f}")


    rcode_names = {0: "NOERROR", 2: "SERVFAIL", 3: "NXDOMAIN", 5: "REFUSED"}
    print("====================================================")
    print("RCODE Distribution")
    for code, count in report["rcodes"].items():
        name =  rcode_names.get(code, f"RCODE_{code}")
        if total > 0:
            pct = count / total * 100
        else:
            pass
        print(f"    {name:<15}{count:>8} ({pct:.1f}%)")
        print("====================================================")
    
    if verbose and "per_type" in report:
        print("====================================================")
        print("Per Record Type")
        for name, stats in report["per_type"].items():
            print(f"    {name:<8} count: {stats['count']:>8} mean: {stats['mean']*1000:.3f}ms p95: {stats['p95']*1000:.3f}ms")
            
