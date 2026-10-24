"""Multi-stop route planning = Travelling-Salesman-style problem.

Visit every stop exactly once starting and ending at city 0.  Input is a
square cost matrix ``D`` (shortest-path costs between the chosen cities).

Syllabus mapping
* brute_force       - full state-space tree, no pruning        (baseline)
* backtracking      - state-space tree + bounding function     (Unit-2, Exp 4)
* branch_and_bound  - Least-Cost B&B with a priority queue     (Unit-3, Exp 6)
* held_karp         - dynamic-programming reference            (Unit-3, Exp 6)

Each solver returns a dict: cost, order (starts and ends with 0), nodes.
`nodes` = state-space nodes expanded (Held-Karp: DP states computed).
"""
import heapq

INF = float("inf")


def _trivial(D):
    n = len(D)
    if n == 1:
        return {"cost": 0.0, "order": [0], "nodes": 1}
    if n == 2:
        return {"cost": D[0][1] + D[1][0], "order": [0, 1, 0], "nodes": 2}
    return None


def brute_force(D):
    """Enumerate every permutation of the stops."""
    t = _trivial(D)
    if t:
        return t
    n = len(D)
    best = [INF, None]
    nodes = [0]

    def rec(path, cost, used):
        nodes[0] += 1
        if len(path) == n:
            total = cost + D[path[-1]][0]
            if total < best[0]:
                best[0], best[1] = total, path + [0]
            return
        last = path[-1]
        for c in range(1, n):
            if not used >> c & 1:
                path.append(c)
                rec(path, cost + D[last][c], used | 1 << c)
                path.pop()

    rec([0], 0.0, 1)
    return {"cost": best[0], "order": best[1], "nodes": nodes[0]}


def backtracking(D):
    """State-space tree with the *promising* test: cost so far < best known tour."""
    t = _trivial(D)
    if t:
        return t
    n = len(D)
    best = [INF, None]
    nodes = [0]

    def rec(path, cost, used):
        nodes[0] += 1
        if len(path) == n:
            total = cost + D[path[-1]][0]
            if total < best[0]:
                best[0], best[1] = total, path + [0]
            return
        last = path[-1]
        for c in range(1, n):
            if not used >> c & 1:
                new_cost = cost + D[last][c]
                if new_cost >= best[0]:          # not promising -> prune
                    continue
                path.append(c)
                rec(path, new_cost, used | 1 << c)
                path.pop()

    rec([0], 0.0, 1)
    return {"cost": best[0], "order": best[1], "nodes": nodes[0]}


def _lower_bound(D, cost, last, used, n):
    """Admissible lower bound on the cost of any completion of a partial tour.

    The remaining tour needs one outgoing edge from `last` (to an unvisited
    city) and one from every unvisited city (to another unvisited city or back
    to the start).  Taking the cheapest such edge for each is a lower bound.
    """
    rest = [c for c in range(1, n) if not used >> c & 1]
    if not rest:
        return cost + D[last][0]
    bound = cost + min(D[last][c] for c in rest)
    for c in rest:
        bound += min([D[c][d] for d in rest if d != c] + [D[c][0]])
    return bound


def _nearest_neighbour(D):
    """Greedy tour used only to obtain an initial upper bound."""
    n = len(D)
    path, used, cost = [0], 1, 0.0
    while len(path) < n:
        last = path[-1]
        c = min((c for c in range(1, n) if not used >> c & 1), key=lambda c: D[last][c])
        cost += D[last][c]
        path.append(c)
        used |= 1 << c
    return cost + D[path[-1]][0], path + [0]


def branch_and_bound(D):
    """Least-Cost B&B: always expand the live node with the smallest lower bound."""
    t = _trivial(D)
    if t:
        return t
    n = len(D)
    best_cost, best_order = _nearest_neighbour(D)      # initial upper bound
    counter = 0                                        # tie-breaker for the heap
    pq = [(_lower_bound(D, 0.0, 0, 1, n), counter, 0.0, [0], 1)]
    nodes = 0
    while pq:
        bound, _, cost, path, used = heapq.heappop(pq)
        if bound >= best_cost:                         # every remaining node is worse
            break
        nodes += 1
        last = path[-1]
        if len(path) == n:
            total = cost + D[last][0]
            if total < best_cost:
                best_cost, best_order = total, path + [0]
            continue
        for c in range(1, n):
            if used >> c & 1:
                continue
            new_cost = cost + D[last][c]
            new_used = used | 1 << c
            lb = _lower_bound(D, new_cost, c, new_used, n)
            if lb < best_cost:
                counter += 1
                heapq.heappush(pq, (lb, counter, new_cost, path + [c], new_used))
    return {"cost": best_cost, "order": best_order, "nodes": nodes}


def held_karp(D):
    """Bitmask DP: O(n^2 * 2^n) time, O(n * 2^n) space."""
    t = _trivial(D)
    if t:
        return t
    m = len(D) - 1                                     # cities 1..m
    full = (1 << m) - 1
    dp = [[INF] * m for _ in range(1 << m)]
    parent = [[-1] * m for _ in range(1 << m)]
    for j in range(m):
        dp[1 << j][j] = D[0][j + 1]
    states = 0
    for mask in range(1, 1 << m):
        for j in range(m):
            if not mask >> j & 1 or dp[mask][j] == INF:
                continue
            states += 1
            cur = dp[mask][j]
            for k in range(m):
                if mask >> k & 1:
                    continue
                nm = mask | 1 << k
                nc = cur + D[j + 1][k + 1]
                if nc < dp[nm][k]:
                    dp[nm][k] = nc
                    parent[nm][k] = j
    cost, last = min((dp[full][j] + D[j + 1][0], j) for j in range(m))
    order, mask = [0], full
    while last != -1:
        order.append(last + 1)
        prev = parent[mask][last]
        mask ^= 1 << last
        last = prev
    order.append(0)
    # order was rebuilt backwards from the end: [0, last..first, 0] -> fix direction
    order = [0] + order[1:-1][::-1] + [0]
    return {"cost": cost, "order": order, "nodes": states}


SOLVERS = {
    "brute_force": brute_force,
    "backtracking": backtracking,
    "branch_and_bound": branch_and_bound,
    "held_karp": held_karp,
}
