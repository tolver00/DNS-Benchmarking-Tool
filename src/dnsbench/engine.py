import multiprocessing
import time
import dns.query
import os
import socket

def worker(msg_wire: bytes, server: str, port: str, query_count: int, result_queue: multiprocessing.Queue):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5.0)
    print(f"Worker {os.getpid()} starting {query_count} queries")
    local_results = []
    for _ in range(query_count):
        try:
            start = time.perf_counter()
            sock.sendto(msg_wire, (server, port))
            data, _ = sock_recvfrom(4096)
            elapsed = time.perf_counter() - start

            local_results.append({
                "latency": elapsed,
                "rcode": data[3] & 0x0F,
            })
        except socket.timeout:
            local.results.append({"error": "timeout"})
        except Exception as e:
            local_results.append({"error": str(e)})

    sock.close()
    result_queue.put(local_results)
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
