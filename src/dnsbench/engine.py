import multiprocessing
import time
import dns.query
import os

def worker(msg_wire: bytes, server: str, port: str, query_count: int, result_queue: multiprocessing.Queue):
    msg = dns.message.from_wire(msg_wire)
    for _ in range(query_count):
        try:
            response = dns.query.udp(msg, server, port=port, timeout=5.0)
            result_queue.put({
                "latency": response.time,
                "rcode": response.rcode(),
            })
        except dns.exception.Timeout:
            result_queue.put({"error": "timeout"})
        except Exception as e:
            result_queue.put({"error": str(e)})
    print(f"Worker {os.getpid()} done")

def run_benchmark(messages: list[bytes], server: str, port: int, total_queries: int, num_workers: int):
    result_queue = multiprocessing.Queue()
    queries_per_worker = total_queries // num_workers

    processes = []
    for i in range(num_workers):
        msg_wire = messages[i % len(messages)]
        p = multiprocessing.Process(
            target=worker,
            args=(msg_wire, server, port, queries_per_worker, result_queue),
        )
        processes.append(p)
    start = time.time()
    for p in processes:
        p.start()

    results = []
    expected = queries_per_worker * num_workers
    while len(results) < expected:
        try:
            results.append(result_queue.get(timeout=0.1))
        except Exception:
            if not any(p.is_alive() for p in processes):
                break

    for p in processes:
        p.join()

    elapsed = time.time() - start
    print(f"Completed {len(results)} queries in {elapsed:.2f}s")
    print(f"Effective QPS: {len(results) / elapsed:.1f}")

    return results 
