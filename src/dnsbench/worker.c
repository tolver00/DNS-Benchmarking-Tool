#include <asm-generic/socket.h>
#include <bits/time.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

typedef struct {
  double latency;
  int rcode;
  int success;
  int msg_index;
}
QueryResult;

int run_queries(const char **messages, const int *msg_lengths, int num_messages,
                const char *server_ip, int port, int query_count,
                double timeout, QueryResult *results) {


  // server address
  struct sockaddr_in addr;
  memset(&addr, 0, sizeof(addr));
  addr.sin_family = AF_INET;
  addr.sin_port = htons(port);
  inet_pton(AF_INET, server_ip, &addr.sin_addr);

  int sock = socket(AF_INET, SOCK_DGRAM, 0);
  struct timeval tv;
  tv.tv_sec = (int)timeout;
  tv.tv_usec = 0;
  setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
  char buf[4096];

  // query loop
  for (int i = 0; i < query_count; i++) {
    int msg_idx = i % num_messages;
    struct timespec start, end;

    clock_gettime(CLOCK_MONOTONIC, &start);
    sendto(sock, messages[msg_idx], msg_lengths[msg_idx], 0,
           (struct sockaddr *)&addr, sizeof(addr));
    int n = recvfrom(sock, buf, sizeof(buf), 0, NULL, NULL);
    clock_gettime(CLOCK_MONOTONIC, &end);
    results[i].latency = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9; 

    results[i].msg_index = msg_idx;
    results[i].success = (n > 3) ? 1 : 0;
    results[i].rcode = (n > 3) ? (buf[3] & 0x0F) : -1;
  }
  close(sock);
  return query_count;
}
