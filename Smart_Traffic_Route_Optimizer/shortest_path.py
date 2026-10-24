"""Single-source shortest-path algorithms (Syllabus Unit-3, Experiment 5).

The graph is an adjacency list:  ``adj[u] = [(v, weight), ...]``  with
non-negative weights.  Three algorithms are provided so they can be compared:

* dijkstra_heap   - binary min-heap            O((V + E) log V)
* dijkstra_array  - linear scan for the minimum  O(V^2)
* bellman_ford    - repeated relaxation          O(V * E)
"""
import heapq

INF = float("inf")


def dijkstra_heap(adj, source, target=None):
    """Return (dist, prev, explored).  Stops early when `target` is settled."""
    dist = {source: 0.0}
    prev = {source: None}
    settled = set()
    pq = [(0.0, source)]
    while pq:
        d, u = heapq.heappop(pq)
        if u in settled:                 # stale queue entry
            continue
        settled.add(u)
        if u == target:
            break
        for v, w in adj.get(u, ()):
            nd = d + w
            if nd < dist.get(v, INF):    # relaxation
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    return dist, prev, len(settled)


def dijkstra_array(adj, source):
    """Dijkstra without a heap: pick the closest unsettled vertex by scanning."""
    dist = {u: INF for u in adj}
    dist[source] = 0.0
    settled = set()
    for _ in range(len(adj)):
        u, best = None, INF
        for x, dx in dist.items():
            if dx < best and x not in settled:
                u, best = x, dx
        if u is None:
            break
        settled.add(u)
        for v, w in adj[u]:
            if best + w < dist[v]:
                dist[v] = best + w
    return dist


def bellman_ford(adj, source, early_exit=True):
    """Return (dist, passes).

    With early_exit=True (default) it stops as soon as a pass changes nothing.
    With early_exit=False it always performs V-1 passes, i.e. the textbook O(V*E).
    """
    dist = {u: INF for u in adj}
    dist[source] = 0.0
    edges = [(u, v, w) for u in adj for v, w in adj[u]]
    passes = 0
    for _ in range(len(adj) - 1):
        passes += 1
        changed = False
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                changed = True
        if early_exit and not changed:
            break
    return dist, passes


def reconstruct_path(prev, target):
    """Follow predecessor links back from `target`."""
    path = []
    node = target
    while node is not None:
        path.append(node)
        node = prev.get(node)
    path.reverse()
    return path
