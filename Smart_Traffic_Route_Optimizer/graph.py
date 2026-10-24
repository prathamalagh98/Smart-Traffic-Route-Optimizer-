"""Road-network model for the Smart Traffic Route Optimizer.

Cities are vertices, roads are undirected weighted edges.  Each road has three
costs that can be optimised:

    distance : kilometres
    time     : minutes   = distance / avg_speed * 60 * congestion
    fuel     : litres    = distance * 0.07 L/km * congestion   (stop-and-go burns more)

All routing algorithms live in shortest_path.py / multistop.py / sorting.py;
this module wires them to the dataset.
"""
import csv
import os
import time as _time

import multistop
from shortest_path import dijkstra_heap, reconstruct_path
from sorting import bubble_sort, merge_sort, quick_sort

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROADS_FILE = os.path.join(BASE_DIR, "data", "roads.csv")
CITIES_FILE = os.path.join(BASE_DIR, "data", "cities.csv")

CRITERIA = ("distance", "time", "fuel")
UNITS = {"distance": "km", "time": "min", "fuel": "L"}
FUEL_PER_KM = 0.07
MAX_BRUTE_FORCE_STOPS = 8      # 8! = 40,320 tours - still instant; 10! is not
MAX_SIMPLE_ROUTES = 50_000
SORTERS = {"merge": merge_sort, "quick": quick_sort, "bubble": bubble_sort}


class DataError(ValueError):
    """Raised when the CSV dataset is malformed."""


class TrafficGraph:
    def __init__(self, roads_file=ROADS_FILE, cities_file=CITIES_FILE):
        self.roads = {}          # frozenset({a, b}) -> {"distance", "speed", "congestion"}
        self.nodes = []
        self.neighbours = {}     # city -> [city, ...]
        self.positions = {}      # city -> (x, y) for drawing only
        self._adj_cache = {}
        self._load_roads(roads_file)
        if cities_file and os.path.exists(cities_file):
            self._load_positions(cities_file)

    # ------------------------------------------------------------------ loading
    def _load_roads(self, filename):
        needed = {"source", "destination", "distance_km", "avg_speed_kmh", "congestion"}
        with open(filename, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            missing = needed - set(reader.fieldnames or [])
            if missing:
                raise DataError(f"{os.path.basename(filename)}: missing columns {sorted(missing)}")
            for line, row in enumerate(reader, start=2):
                a, b = row["source"].strip(), row["destination"].strip()
                try:
                    dist = float(row["distance_km"])
                    speed = float(row["avg_speed_kmh"])
                    cong = float(row["congestion"])
                except (TypeError, ValueError):
                    raise DataError(f"line {line}: distance, speed and congestion must be numbers")
                if not a or not b or a == b:
                    raise DataError(f"line {line}: invalid road '{a}' - '{b}'")
                if dist <= 0:      # Dijkstra requires non-negative weights
                    raise DataError(f"line {line}: distance must be positive (got {dist})")
                if speed <= 0:
                    raise DataError(f"line {line}: speed must be positive (got {speed})")
                if cong < 1:
                    raise DataError(f"line {line}: congestion factor must be >= 1 (got {cong})")
                key = frozenset((a, b))
                if key in self.roads:
                    raise DataError(f"line {line}: duplicate road {a} - {b}")
                self.roads[key] = {"distance": dist, "speed": speed, "congestion": cong}
                for u, v in ((a, b), (b, a)):
                    if u not in self.neighbours:
                        self.neighbours[u] = []
                        self.nodes.append(u)
                    self.neighbours[u].append(v)

    def _load_positions(self, filename):
        with open(filename, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row["city"] in self.neighbours:
                    self.positions[row["city"]] = (float(row["x"]), float(row["y"]))

    # ------------------------------------------------------------------ costs
    def edge_metrics(self, a, b):
        """Return (km, minutes, litres) for the road a-b."""
        r = self.roads[frozenset((a, b))]
        km = r["distance"]
        minutes = km / r["speed"] * 60 * r["congestion"]
        litres = km * FUEL_PER_KM * r["congestion"]
        return km, minutes, litres

    def weight(self, a, b, criterion):
        return self.edge_metrics(a, b)[CRITERIA.index(criterion)]

    def adjacency(self, criterion):
        if criterion not in CRITERIA:
            raise ValueError(f"criterion must be one of {CRITERIA}")
        if criterion not in self._adj_cache:
            self._adj_cache[criterion] = {
                u: [(v, self.weight(u, v, criterion)) for v in vs]
                for u, vs in self.neighbours.items()
            }
        return self._adj_cache[criterion]

    def path_totals(self, path):
        km = minutes = litres = 0.0
        for a, b in zip(path, path[1:]):
            d, t, f = self.edge_metrics(a, b)
            km, minutes, litres = km + d, minutes + t, litres + f
        return {"distance": km, "time": minutes, "fuel": litres}

    def _check(self, *cities):
        for c in cities:
            if c not in self.neighbours:
                raise KeyError(f"unknown city: {c}")

    # ------------------------------------------------------------------ Unit-3: Dijkstra
    def shortest_route(self, source, destination, criterion="distance"):
        """Dijkstra from source to destination; None if unreachable."""
        self._check(source, destination)
        dist, prev, explored = dijkstra_heap(self.adjacency(criterion), source, destination)
        if destination not in dist:
            return None
        path = reconstruct_path(prev, destination)
        result = {"path": path, "cost": dist[destination], "explored": explored,
                  "criterion": criterion}
        result.update(self.path_totals(path))
        return result

    # ------------------------------------------------------------------ Unit-2 + Unit-1
    def all_routes(self, source, destination, limit=MAX_SIMPLE_ROUTES):
        """Backtracking DFS over simple paths.  Returns (routes, truncated)."""
        self._check(source, destination)
        routes, path, on_path = [], [source], {source}
        truncated = [False]

        def dfs(u):
            if truncated[0]:
                return
            if u == destination:
                routes.append(list(path))
                if len(routes) >= limit:
                    truncated[0] = True
                return
            for v in self.neighbours[u]:
                if v not in on_path:
                    path.append(v)
                    on_path.add(v)
                    dfs(v)
                    on_path.discard(v)
                    path.pop()

        dfs(source)
        return routes, truncated[0]

    def ranked_routes(self, source, destination, criterion="distance", top=5, sorter="merge"):
        """Enumerate every simple route and rank it with one of our own sorts.

        Returns (top_routes, total_routes, comparisons).
        """
        if sorter not in SORTERS:
            raise ValueError(f"sorter must be one of {tuple(SORTERS)}")
        paths, _ = self.all_routes(source, destination)
        routes = []
        for p in paths:
            r = {"path": p, "criterion": criterion}
            r.update(self.path_totals(p))
            routes.append(r)
        ordered, comparisons = SORTERS[sorter](routes, key=lambda r: r[criterion])
        return ordered[:top], len(routes), comparisons

    # ------------------------------------------------------------------ Unit-2/3: multi-stop
    def cost_matrix(self, cities, criterion="distance"):
        """Pairwise shortest-path costs (Dijkstra from each city) + the paths."""
        adj = self.adjacency(criterion)
        D = [[0.0] * len(cities) for _ in cities]
        paths = {}
        for i, a in enumerate(cities):
            dist, prev, _ = dijkstra_heap(adj, a)
            for j, b in enumerate(cities):
                if b not in dist:
                    raise ValueError(f"no road connection between {a} and {b}")
                D[i][j] = dist[b]
                paths[(a, b)] = reconstruct_path(prev, b)
        return D, paths

    def plan_tour(self, start, stops, criterion="distance", method="branch_and_bound"):
        """Visit all `stops` starting and ending at `start`."""
        stops = list(dict.fromkeys(stops))            # drop duplicates, keep order
        if start in stops:
            stops.remove(start)
        self._check(start, *stops)
        if method not in multistop.SOLVERS:
            raise ValueError(f"unknown method: {method}")
        if method == "brute_force" and len(stops) > MAX_BRUTE_FORCE_STOPS:
            raise ValueError(f"brute force is limited to {MAX_BRUTE_FORCE_STOPS} stops "
                             f"(it would try {len(stops)}! tours)")
        cities = [start] + stops
        D, paths = self.cost_matrix(cities, criterion)
        t0 = _time.perf_counter()
        sol = multistop.SOLVERS[method](D)
        elapsed_ms = (_time.perf_counter() - t0) * 1000
        order = [cities[i] for i in sol["order"]]
        full = [start]
        for a, b in zip(order, order[1:]):
            full.extend(paths[(a, b)][1:])
        result = {"method": method, "criterion": criterion, "order": order, "path": full,
                  "cost": sol["cost"], "nodes": sol["nodes"], "elapsed_ms": elapsed_ms}
        result.update(self.path_totals(full))
        return result

    def compare_methods(self, start, stops, criterion="distance"):
        """Run every applicable solver on the same problem (for the comparison table)."""
        results = []
        n_stops = len(set(stops) - {start})
        for m in multistop.SOLVERS:
            if m == "brute_force" and n_stops > MAX_BRUTE_FORCE_STOPS:
                continue
            results.append(self.plan_tour(start, stops, criterion, m))
        return results
