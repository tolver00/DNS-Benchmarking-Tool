import multiprocessing
import time
import dns.query
import os
import socket

def worker(messages: bytes, server: str, port: int, query_count: int, protocol: str, result_queue: multiprocessing.Queue):
    if protocol == "udp":
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    elif protocol == "tcp":
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    sock.settimeout(5.0)

    if protocol == "tcp":
        sock.connect((server, port))

    num_messages = len(messages)
    local_results = []
    try:
        for i in range(query_count):
            msg_wire = messages[i % num_messages]
            try:
                start = time.perf_counter()
                if protocol == "udp":
                   sock.sendto(msg_wire, (server, port))
                   data, _ = sock.recvfrom(4096)
                elif protocol == "tcp":
                    length = len(msg_wire).to_bytes(2, "big")
                    sock.sendall(length + msg_wire)
                    resp_len = int.from_bytes(sock.recv(2), "big")
                    data = sock.recv(resp_len)
                    
                   
                elapsed = time.perf_counter() - start
                local_results.append({
                    "latency": elapsed,
                    "rcode": data[3] & 0x0F,
                    "msg_index": i % num_messages,
                })
            except socket.timeout:
                local_results.append({"error": "timeout", "msg_index": i % num_messages})
            except Exception as e:
                local_results.append({"error": str(e), "msg_index": i % num_messages})

    finally:
        sock.close()
    result_queue.put(local_results)
    # print(f"Worker {os.getpid()} done") 
    
            
def run_benchmark(messages: list[bytes], server: str, port: int, total_queries: int, num_workers: int, protocol: str):
    result_queue = multiprocessing.Queue()
    queries_per_worker = total_queries // num_workers

    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(
            target=worker,
            args=(messages, server, port, queries_per_worker, protocol, result_queue),
        )
        processes.append(p)
    start = time.time()
    for p in processes:
        p.start()

    results = []
    for _ in range(num_workers):
        batch = result_queue.get()
        results.extend(batch)

    for p in processes:
        p.join()
    elapsed = time.time() - start
        
    # print(f"Completed {len(results)} queries in {elapsed:.2f}s")
    # print(f"Effective QPS: {len(results) / elapsed:.1f}")

    return results, elapsed
