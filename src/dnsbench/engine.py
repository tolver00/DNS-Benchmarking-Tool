import multiprocessing
import time
import dns.query
import os
import socket
import ctypes

## query class for ctypes
class QueryResult(ctypes.Structure):
    _fields_ = [
        ("latency", ctypes.c_double),
        ("rcode", ctypes.c_int),
        ("success", ctypes.c_int),
        ("msg_index", ctypes.c_int),
    ]


def worker(messages, server, port, query_count, mode, protocol, result_queue, deadline):
    if protocol == "udp":
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    elif protocol == "tcp":
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    sock.settimeout(5.0)

    if protocol == "tcp":
        sock.connect((server, port))

    num_messages = len(messages)
    local_results = []
    i = 0
    try:
        while True:
            if mode == "count" and i >= query_count:
                break
            if mode == "duration" and time.time() >= deadline:
                break
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
            i += 1
    finally:
        sock.close()
    result_queue.put(local_results)
    # print(f"Worker {os.getpid()} done") 
    
            
def run_benchmark(messages, server, port, total_queries, num_workers, protocol, mode, duration):
    result_queue = multiprocessing.Queue()
    if mode == "duration":
        deadline = time.time() + duration
    else:
        deadline = 0
    
    queries_per_worker = total_queries // num_workers if mode == "count" else 0

    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(
            target=worker,
            args=(messages, server, port, queries_per_worker, mode, protocol, result_queue, deadline),
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
        
    return results, elapsed

def worker_native(lib_path, messages, server, port, query_count, protocol, result_queue):
    lib = ctypes.CDLL(lib_path)

    # args types
    lib.run_queries.argtypes = [
        ctypes.POINTER(ctypes.c_char_p), # messages
        ctypes.POINTER(ctypes.c_int), # message length
        ctypes.c_int, # number messages
        ctypes.c_char_p, # server ip
        ctypes.c_int, # port
        ctypes.c_int, # query_count
        ctypes.c_double, # timeout
        ctypes.POINTER(QueryResult), # results
    ]
    lib.run_queries.restype = ctypes.c_int

    num_msgs = len(messages)
    msg_array = (ctypes.c_char_p * num_msgs)(*messages)
    lengths = []
    for m in messages:
        lengths.append(len(m))
    len_array = (ctypes.c_int * num_msgs)(*lengths)

    # alocate resulrs
    results = (QueryResult * query_count)()
    
    completed = lib.run_queries(
        msg_array, len_array, num_msgs,
        server.encode(), port, query_count, 5.0, results
    )

    # convert to dicts same as normal worker
    local_results = []
    for i in range(completed):
        r = results[i]
        if r.success:
            local_results.append({
                "latency": r.latency,
                "rcode": r.rcode,
                "msg_index": r.msg_index,
            })
        else:
            local_results.append({
                "error": "timeout",
                "msg_index": r.msg_index,
            })
    result_queue.put(local_results)


def run_benchmark_native(messages, server, port, total_queries, num_workers):
    result_queue = multiprocessing.Queue()
    queries_per_worker = total_queries // num_workers

    lib_path = os.path.join(os.path.dirname(__file__), "worker.so")

    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(
            target=worker_native,
            args=(lib_path, messages, server, port, queries_per_worker, "udp", result_queue),
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

    return results, elapsed
