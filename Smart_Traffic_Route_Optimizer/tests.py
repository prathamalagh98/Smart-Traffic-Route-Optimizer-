"""Automated tests.  Run:  python tests.py   (or: python -m unittest tests -v)"""
import contextlib
import io
import itertools
import math
import os
import random
import tempfile
import unittest

import cli
import multistop
from graph import CRITERIA, DataError, TrafficGraph
from shortest_path import bellman_ford, dijkstra_array, dijkstra_heap, reconstruct_path
from sorting import bubble_sort, merge_sort, quick_sort

INF = float("inf")


def floyd_warshall(g, criterion):
    nodes = g.nodes
    d = {a: {b: (0 if a == b else INF) for b in nodes} for a in nodes}
    for u, edges in g.adjacency(criterion).items():
        for v, w in edges:
            d[u][v] = min(d[u][v], w)
    for k in nodes:
        for i in nodes:
            for j in nodes:
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return d


class SortingTests(unittest.TestCase):
    def test_all_sorts_match_python_sorted(self):
        rng = random.Random(1)
        cases = [[], [1], [2, 1], [5] * 7, list(range(50)), list(range(50, 0, -1))]
        cases += [[rng.randint(-50, 50) for _ in range(rng.randint(2, 200))] for _ in range(30)]
        for data in cases:
            for fn in (bubble_sort, merge_sort, quick_sort, lambda d: quick_sort(d, pivot="last")):
                self.assertEqual(fn(data)[0], sorted(data))

    def test_input_is_not_modified(self):
        data = [3, 1, 2]
        for fn in (bubble_sort, merge_sort, quick_sort):
            fn(data)
        self.assertEqual(data, [3, 1, 2])

    def test_key_sort_is_stable(self):
        items = [("b", 1), ("a", 1), ("c", 0), ("d", 1)]
        for fn in (bubble_sort, merge_sort):
            out, _ = fn(items, key=lambda t: t[1])
            self.assertEqual(out, [("c", 0), ("b", 1), ("a", 1), ("d", 1)])

    def test_best_and_worst_case_comparison_counts(self):
        n = 200
        self.assertEqual(bubble_sort(list(range(n)))[1], n - 1)                    # Omega(n)
        self.assertEqual(bubble_sort(list(range(n, 0, -1)))[1], n * (n - 1) // 2)  # n(n-1)/2
        self.assertEqual(quick_sort(list(range(n)), pivot="last")[1], n * (n - 1) // 2)
        self.assertLess(merge_sort(list(range(n)))[1], n * math.log2(n))


class ShortestPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = TrafficGraph()

    def test_dijkstra_matches_floyd_warshall_for_every_pair_and_criterion(self):
        for crit in CRITERIA:
            fw = floyd_warshall(self.g, crit)
            for a, b in itertools.permutations(self.g.nodes, 2):
                r = self.g.shortest_route(a, b, crit)
                self.assertAlmostEqual(r["cost"], fw[a][b], places=9, msg=(a, b, crit))

    def test_three_algorithms_agree_on_random_graphs(self):
        for seed in range(10):
            rng = random.Random(seed)
            v = rng.randint(5, 40)
            adj = {u: [] for u in range(v)}
            for u in range(1, v):
                w = rng.randint(1, 20)
                p = rng.randrange(u)
                adj[u].append((p, w))
                adj[p].append((u, w))
            for _ in range(2 * v):
                a, b, w = rng.randrange(v), rng.randrange(v), rng.randint(1, 20)
                if a != b:
                    adj[a].append((b, w))
                    adj[b].append((a, w))
            d1, _, _ = dijkstra_heap(adj, 0)
            d2 = dijkstra_array(adj, 0)
            d3, _ = bellman_ford(adj, 0)
            d4, _ = bellman_ford(adj, 0, early_exit=False)
            for u in adj:
                self.assertAlmostEqual(d1[u], d2[u])
                self.assertAlmostEqual(d1[u], d3[u])
                self.assertAlmostEqual(d1[u], d4[u])

    def test_path_is_valid_and_totals_add_up(self):
        r = self.g.shortest_route("Ludhiana", "Chandigarh", "time")
        self.assertEqual(r["path"][0], "Ludhiana")
        self.assertEqual(r["path"][-1], "Chandigarh")
        for a, b in zip(r["path"], r["path"][1:]):
            self.assertIn(frozenset((a, b)), self.g.roads)
        self.assertAlmostEqual(r["time"], r["cost"])

    def test_same_city_and_unknown_city(self):
        r = self.g.shortest_route("Patiala", "Patiala")
        self.assertEqual(r["path"], ["Patiala"])
        self.assertEqual(r["cost"], 0)
        with self.assertRaises(KeyError):
            self.g.shortest_route("Patiala", "Atlantis")

    def test_reconstruct_path(self):
        self.assertEqual(reconstruct_path({"a": None, "b": "a", "c": "b"}, "c"), ["a", "b", "c"])

    def test_alternative_routes_are_ranked_and_the_best_is_dijkstra(self):
        for crit in CRITERIA:
            for sorter in ("merge", "quick", "bubble"):
                top, total, comps = self.g.ranked_routes("Ludhiana", "Zirakpur", crit, 10, sorter)
                values = [r[crit] for r in top]
                self.assertEqual(values, sorted(values))
                self.assertGreater(total, 1)
                self.assertGreater(comps, 0)
                best = self.g.shortest_route("Ludhiana", "Zirakpur", crit)
                self.assertAlmostEqual(values[0], best["cost"])

    def test_all_routes_are_simple_paths(self):
        paths, truncated = self.g.all_routes("Ropar", "Rajpura")
        self.assertFalse(truncated)
        self.assertEqual(len({tuple(p) for p in paths}), len(paths))
        for p in paths:
            self.assertEqual(len(set(p)), len(p))
            self.assertEqual((p[0], p[-1]), ("Ropar", "Rajpura"))


def random_matrix(n, rng, symmetric=True):
    D = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                D[i][j] = rng.uniform(1, 100)
                if symmetric and j < i:
                    D[i][j] = D[j][i]
    return D


def tour_cost(D, order):
    return sum(D[a][b] for a, b in zip(order, order[1:]))


class MultiStopTests(unittest.TestCase):
    def test_all_solvers_find_the_same_optimum(self):
        rng = random.Random(5)
        for n in range(2, 9):
            for symmetric in (True, False):
                for _ in range(4):
                    D = random_matrix(n, rng, symmetric)
                    results = {m: fn(D) for m, fn in multistop.SOLVERS.items()}
                    optimum = results["brute_force"]["cost"]
                    for m, r in results.items():
                        self.assertAlmostEqual(r["cost"], optimum, places=9, msg=(m, n))
                        self.assertEqual(r["order"][0], 0)
                        self.assertEqual(r["order"][-1], 0)
                        self.assertEqual(sorted(r["order"][:-1]), list(range(n)))
                        self.assertAlmostEqual(tour_cost(D, r["order"]), r["cost"], places=9, msg=m)

    def test_single_city_tour_is_trivial(self):
        for fn in multistop.SOLVERS.values():
            self.assertEqual(fn([[0.0]]), {"cost": 0.0, "order": [0], "nodes": 1})

    def test_pruning_never_explores_more_than_brute_force(self):
        rng = random.Random(9)
        for n in range(4, 9):
            D = random_matrix(n, rng)
            brute = multistop.brute_force(D)["nodes"]
            self.assertLessEqual(multistop.backtracking(D)["nodes"], brute)
            self.assertLess(multistop.branch_and_bound(D)["nodes"], brute)

    def test_brute_force_node_count_formula(self):
        # 1 + (n-1) + (n-1)(n-2) + ... nodes in the full state-space tree
        for n in range(3, 8):
            expected, term = 1, 1
            for k in range(1, n):
                term *= n - k
                expected += term
            self.assertEqual(multistop.brute_force(random_matrix(n, random.Random(n)))["nodes"], expected)

    def test_plan_tour_on_real_data(self):
        g = TrafficGraph()
        stops = ["Patiala", "Ambala", "Mohali", "Ropar"]
        costs = {m: g.plan_tour("Ludhiana", stops, "distance", m)["cost"] for m in multistop.SOLVERS}
        self.assertEqual(len({round(c, 6) for c in costs.values()}), 1)
        r = g.plan_tour("Ludhiana", stops, "time", "held_karp")
        self.assertEqual((r["path"][0], r["path"][-1]), ("Ludhiana", "Ludhiana"))
        self.assertTrue(set(stops) <= set(r["path"]))
        self.assertAlmostEqual(r["time"], r["cost"], places=6)

    def test_brute_force_limit_is_enforced(self):
        g = TrafficGraph()
        others = [c for c in g.nodes if c != "Ludhiana"]
        with self.assertRaises(ValueError):
            g.plan_tour("Ludhiana", others, "distance", "brute_force")
        self.assertEqual(len({round(r["cost"], 6) for r in g.compare_methods("Ludhiana", others)}), 1)


class DataValidationTests(unittest.TestCase):
    HEADER = "source,destination,distance_km,avg_speed_kmh,congestion\n"

    def load(self, body, header=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "roads.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write((header or self.HEADER) + body)
            return TrafficGraph(path, None)

    def test_valid_file_loads(self):
        g = self.load("A,B,10,50,1.0\nB,C,5,50,1.2\n")
        self.assertEqual(sorted(g.nodes), ["A", "B", "C"])

    def test_rejects_bad_rows(self):
        bad = ["A,B,-5,50,1.0\n", "A,B,0,50,1.0\n", "A,B,5,0,1.0\n", "A,B,5,50,0.5\n",
               "A,A,5,50,1.0\n", "A,B,x,50,1.0\n", "A,B,5,50,1.0\nB,A,6,50,1.0\n"]
        for body in bad:
            with self.assertRaises(DataError, msg=body):
                self.load(body)

    def test_rejects_missing_columns(self):
        with self.assertRaises(DataError):
            self.load("A,B,5\n", header="source,destination,distance_km\n")

    def test_unreachable_city_returns_none(self):
        g = self.load("A,B,10,50,1.0\nC,D,5,50,1.0\n")
        self.assertIsNone(g.shortest_route("A", "D"))

    def test_works_from_any_working_directory(self):
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                self.assertGreater(len(TrafficGraph().nodes), 5)
            finally:
                os.chdir(old)


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(list(argv))
        return code, out.getvalue()

    def test_route(self):
        code, out = self.run_cli("route", "Ludhiana", "Chandigarh", "--by", "time", "--alternatives", "3")
        self.assertEqual(code, 0)
        self.assertIn("Best route by time", out)
        self.assertIn("Ludhiana -> ", out)

    def test_tour_compare(self):
        code, out = self.run_cli("tour", "Ludhiana", "Patiala", "Ambala", "Mohali", "--compare")
        self.assertEqual(code, 0)
        for m in multistop.SOLVERS:
            self.assertIn(m, out)

    def test_unknown_city_gives_error_code(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = cli.main(["route", "Ludhiana", "Atlantis"])
        self.assertEqual(code, 2)
        self.assertIn("Atlantis", err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
