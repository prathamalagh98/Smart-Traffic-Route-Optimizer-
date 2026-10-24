"""Empirical performance analysis for the DAA project.

Run:  python analysis.py            full benchmark (about 1-2 minutes)
      python analysis.py --quick    smaller sizes (about 20-30 seconds)

Outputs go to results/:
    sorting_times.csv        + sorting_runtime.png, sorting_cases.png   (Experiment 1, Unit-1)
    shortest_path_times.csv  + shortest_path_scalability.png            (Experiment 5, Unit-3)
    tsp_comparison.csv       + tsp_comparison.png                       (Experiments 4 and 6)
    tsp_real_dataset.csv                                                (same, on roads.csv)
    summary.md               every table in Markdown, ready for the report
"""
import argparse
import csv
import math
import os
import random
import statistics
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import multistop  # noqa: E402
from graph import TrafficGraph  # noqa: E402
from shortest_path import bellman_ford, dijkstra_array, dijkstra_heap  # noqa: E402
from sorting import bubble_sort, merge_sort, quick_sort  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
FIG = (11, 4.2)
COLORS = {"bubble": "#c0392b", "merge": "#2980b9", "quick": "#27ae60", "quick_last": "#e67e22",
          "dijkstra_heap": "#2980b9", "dijkstra_array": "#8e44ad", "bellman_ford": "#c0392b",
          "bellman_ford_full": "#e67e22",
          "brute_force": "#c0392b", "backtracking": "#e67e22", "branch_and_bound": "#27ae60",
          "held_karp": "#2980b9"}


def timed(fn, repeats):
    """Median wall-clock time (ms) of `repeats` runs, plus the last return value."""
    runs, out = [], None
    for _ in range(repeats):
        t0 = time.perf_counter()
        out = fn()
        runs.append((time.perf_counter() - t0) * 1000)
    return statistics.median(runs), out


def write_csv(name, header, rows):
    with open(os.path.join(RESULTS, name), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def md_table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def exponent(xs, ys):
    """Slope of the least-squares line through (log x, log y) = empirical power-law exponent."""
    lx, ly = [math.log(x) for x in xs], [math.log(y) for y in ys]
    mx, my = sum(lx) / len(lx), sum(ly) / len(ly)
    return sum((a - mx) * (b - my) for a, b in zip(lx, ly)) / sum((a - mx) ** 2 for a in lx)


# ====================================================================== Experiment 1
def make_input(kind, n, rng):
    data = [rng.randint(0, 10 * n) for _ in range(n)]
    if kind == "sorted":
        data.sort()
    elif kind == "reversed":
        data.sort(reverse=True)
    return data


def run_sorting(sizes, repeats):
    print("[1/4] sorting ...")
    algos = {"bubble": bubble_sort, "merge": merge_sort, "quick": quick_sort,
             "quick_last": lambda d: quick_sort(d, pivot="last")}
    rows = []
    for n in sizes:
        for kind in ("random", "sorted", "reversed"):
            data = make_input(kind, n, random.Random(n))
            for name, fn in algos.items():
                ms, (out, comps) = timed(lambda: fn(data), repeats)
                assert out == sorted(data), f"{name} failed on {kind} n={n}"
                rows.append((name, kind, n, round(ms, 3), comps))
        print(f"   n={n} done")
    write_csv("sorting_times.csv", ["algorithm", "input", "n", "time_ms", "comparisons"], rows)

    def pick(alg, kind):
        return [(r[2], r[3], r[4]) for r in rows if r[0] == alg and r[1] == kind]

    # chart 1: runtime + normalised cost on random input
    fig, ax = plt.subplots(1, 2, figsize=FIG)
    shapes = {"bubble": lambda n: n * n, "merge": lambda n: n * math.log2(n),
              "quick": lambda n: n * math.log2(n)}
    for name in ("bubble", "merge", "quick"):
        pts = pick(name, "random")
        ns, ts = [p[0] for p in pts], [p[1] for p in pts]
        ax[0].plot(ns, ts, "o-", color=COLORS[name], label=name)
        ratio = [t / shapes[name](n) for n, t in zip(ns, ts)]
        ax[1].plot(ns, [r / ratio[0] for r in ratio], "o-", color=COLORS[name],
                   label={"bubble": "bubble / n\u00b2", "merge": "merge / n log n",
                          "quick": "quick / n log n"}[name])
    pts = pick("merge", "random")                      # a deliberately WRONG model for contrast
    wrong = [t / (n * n) for n, t, _ in pts]
    ax[1].plot([p[0] for p in pts], [w / wrong[0] for w in wrong], "s--", color="grey",
               label="merge / n\u00b2 (wrong model)")
    ax[0].set(xscale="log", yscale="log", xlabel="input size n", ylabel="time (ms)",
              title="Running time, random input (log-log)")
    ax[1].axhline(1, color="grey", lw=0.8, ls=":")
    ax[1].set(xscale="log", yscale="log", xlabel="input size n",
              ylabel="T(n)/f(n), relative to smallest n",
              title="Right model stays flat, wrong model collapses")
    for a in ax:
        a.grid(alpha=0.3, which="both")
        a.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "sorting_runtime.png"), dpi=100)
    plt.close(fig)

    # chart 2: best / average / worst cases (comparison counts are deterministic)
    fig, ax = plt.subplots(1, 2, figsize=FIG)
    for kind, style in (("sorted", "best  (sorted)"), ("random", "average (random)"),
                        ("reversed", "worst (reversed)")):
        pts = pick("bubble", kind)
        ax[0].plot([p[0] for p in pts], [p[2] for p in pts], "o-", label=style)
    ax[0].set(xscale="log", yscale="log", xlabel="input size n", ylabel="comparisons",
              title="Bubble sort: \u03a9(n) best, O(n\u00b2) worst")
    for name, kind, label in (("quick_last", "sorted", "quick, last pivot, sorted input"),
                              ("quick", "sorted", "quick, random pivot, sorted input"),
                              ("merge", "sorted", "merge sort, sorted input")):
        pts = pick(name, kind)
        ax[1].plot([p[0] for p in pts], [p[2] for p in pts], "o-", color=COLORS[name], label=label)
    ax[1].set(xscale="log", yscale="log", xlabel="input size n", ylabel="comparisons",
              title="Quick sort worst case depends on the pivot rule")
    for a in ax:
        a.grid(alpha=0.3, which="both")
        a.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "sorting_cases.png"), dpi=100)
    plt.close(fig)

    table = []
    for n in sizes:
        row = [n]
        for name in ("bubble", "merge", "quick"):
            row.append(next(f"{t:.1f}" for nn, t, _ in pick(name, "random") if nn == n))
        table.append(row)
    expo = [[name, f"{exponent([p[0] for p in pick(name, 'random')], [p[1] for p in pick(name, 'random')]):.2f}",
             {"bubble": "2 (n\u00b2)", "merge": "~1.1 (n log n)", "quick": "~1.1 (n log n)"}[name]]
            for name in ("bubble", "merge", "quick")]
    cases = []
    for n in sizes[-1:]:
        for name, kind in (("bubble", "sorted"), ("bubble", "random"), ("bubble", "reversed"),
                           ("quick_last", "sorted"), ("quick", "sorted"), ("merge", "sorted")):
            comps = next(c for nn, _, c in pick(name, kind) if nn == n)
            cases.append([name, kind, n, comps])
    return {"times": (["n", "bubble (ms)", "merge (ms)", "quick (ms)"], table),
            "expo": (["algorithm", "measured exponent", "theory"], expo),
            "cases": (["algorithm", "input", "n", "comparisons"], cases)}


# ====================================================================== Experiment 5
def random_graph(v, seed, factor=4):
    """Connected random undirected graph with ~factor*v edges and weights 1..100."""
    rng = random.Random(seed)
    adj = {u: [] for u in range(v)}
    seen = set()

    def add(a, b):
        key = (min(a, b), max(a, b))
        if a == b or key in seen:
            return False
        seen.add(key)
        w = float(rng.randint(1, 100))
        adj[a].append((b, w))
        adj[b].append((a, w))
        return True

    for u in range(1, v):
        add(u, rng.randrange(u))               # random spanning tree => connected
    target = min(factor * v, v * (v - 1) // 2)
    while len(seen) < target:
        add(rng.randrange(v), rng.randrange(v))
    return adj, len(seen)


def run_shortest_paths(sizes, repeats, array_max, bf_full_max):
    print("[2/4] shortest paths ...")
    rows = []
    for v in sizes:
        adj, e = random_graph(v, seed=v)
        ref, _, _ = dijkstra_heap(adj, 0)
        ms, _ = timed(lambda: dijkstra_heap(adj, 0), repeats)
        rows.append(("dijkstra_heap", v, e, round(ms, 3), ""))
        if v <= array_max:
            ms, dist = timed(lambda: dijkstra_array(adj, 0), repeats)
            assert all(abs(dist[u] - ref[u]) < 1e-9 for u in ref)
            rows.append(("dijkstra_array", v, e, round(ms, 3), ""))
        ms, (dist, passes) = timed(lambda: bellman_ford(adj, 0), repeats)
        assert all(abs(dist[u] - ref[u]) < 1e-9 for u in ref)
        rows.append(("bellman_ford", v, e, round(ms, 3), f"{passes} passes"))
        if v <= bf_full_max:
            ms, (dist, passes) = timed(lambda: bellman_ford(adj, 0, early_exit=False), 1)
            rows.append(("bellman_ford_full", v, e, round(ms, 3), f"{passes} passes"))
        print(f"   V={v} done")
    write_csv("shortest_path_times.csv", ["algorithm", "V", "E", "time_ms", "note"], rows)

    def pick(alg):
        return [(r[1], r[2], r[3]) for r in rows if r[0] == alg]

    fig, ax = plt.subplots(1, 2, figsize=FIG)
    for name in ("dijkstra_heap", "dijkstra_array", "bellman_ford", "bellman_ford_full"):
        pts = pick(name)
        if pts:
            ax[0].plot([p[0] for p in pts], [p[2] for p in pts], "o-", color=COLORS[name], label=name)
    ax[0].set(xscale="log", yscale="log", xlabel="vertices V (E = 4V)", ylabel="time (ms)",
              title="Single-source shortest paths (log-log)")
    pts = pick("dijkstra_heap")
    ratio = [t / ((v + e) * math.log2(v)) for v, e, t in pts]
    ax[1].plot([p[0] for p in pts], [r / ratio[0] for r in ratio], "o-", color=COLORS["dijkstra_heap"],
               label="heap Dijkstra / ((V+E) log V)")
    wrong = [t / (v * v) for v, e, t in pts]           # deliberately WRONG model for contrast
    ax[1].plot([p[0] for p in pts], [w / wrong[0] for w in wrong], "s--", color="grey",
               label="heap Dijkstra / V\u00b2 (wrong model)")
    ax[1].axhline(1, color="grey", lw=0.8, ls=":")
    ax[1].set(xscale="log", yscale="log", xlabel="vertices V", ylabel="T/f, relative to smallest V",
              title="Right model stays near-flat, wrong model collapses")
    for a in ax:
        a.grid(alpha=0.3, which="both")
        a.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "shortest_path_scalability.png"), dpi=100)
    plt.close(fig)

    names = ("dijkstra_heap", "dijkstra_array", "bellman_ford", "bellman_ford_full")
    table = []
    for v in sizes:
        e = next(p[1] for p in pick("dijkstra_heap") if p[0] == v)
        row = [v, e]
        for name in names:
            row.append(next((f"{t:.1f}" for vv, _, t in pick(name) if vv == v), "-"))
        table.append(row)
    expo = []
    for name in names:
        pts = pick(name)
        if len(pts) >= 3:
            expo.append([name, f"{exponent([p[0] for p in pts], [p[2] for p in pts]):.2f}"])
    return {"times": (["V", "E", "heap Dijkstra (ms)", "array Dijkstra (ms)",
                       "Bellman-Ford early-exit (ms)", "Bellman-Ford V-1 passes (ms)"], table),
            "expo": (["algorithm", "measured exponent in V (E = 4V)"], expo)}


# ====================================================================== Experiments 4 + 6
def random_matrix(n, rng):
    pts = [(rng.uniform(0, 100), rng.uniform(0, 100)) for _ in range(n)]
    return [[math.dist(a, b) for b in pts] for a in pts]


def run_tsp(ns, instances, caps):
    print("[3/4] multi-stop (TSP) on random Euclidean instances ...")
    rows = []
    for n in ns:
        stats = {m: {"nodes": [], "ms": []} for m in multistop.SOLVERS}
        for k in range(instances):
            D = random_matrix(n, random.Random(1000 * n + k))
            costs = {}
            for m, fn in multistop.SOLVERS.items():
                if n > caps[m]:
                    continue
                ms, res = timed(lambda: fn(D), 1)
                costs[m] = res["cost"]
                stats[m]["nodes"].append(res["nodes"])
                stats[m]["ms"].append(ms)
            assert max(costs.values()) - min(costs.values()) < 1e-6, f"solvers disagree n={n}: {costs}"
        for m, s in stats.items():
            if s["nodes"]:
                rows.append((n, m, len(s["nodes"]), round(statistics.mean(s["nodes"]), 1),
                             round(statistics.mean(s["ms"]), 3)))
        print(f"   n={n} done")
    write_csv("tsp_comparison.csv", ["n_cities", "method", "instances", "mean_nodes", "mean_time_ms"], rows)

    def pick(m, col):
        return [(r[0], r[col]) for r in rows if r[1] == m]

    fig, ax = plt.subplots(1, 2, figsize=FIG)
    for m in multistop.SOLVERS:
        pts = pick(m, 3)
        ax[0].plot([p[0] for p in pts], [p[1] for p in pts], "o-", color=COLORS[m], label=m)
        pts = pick(m, 4)
        ax[1].plot([p[0] for p in pts], [p[1] for p in pts], "o-", color=COLORS[m], label=m)
    ax[0].set(yscale="log", xlabel="cities visited (incl. start)", ylabel="mean nodes explored",
              title="Search-space size")
    ax[1].set(yscale="log", xlabel="cities visited (incl. start)", ylabel="mean time (ms)",
              title="Running time")
    for a in ax:
        a.grid(alpha=0.3, which="both")
        a.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "tsp_comparison.png"), dpi=100)
    plt.close(fig)

    table, reduction = [], []
    for n in ns:
        row = [n]
        for m in multistop.SOLVERS:
            row.append(next((f"{int(v):,}" for nn, v in pick(m, 3) if nn == n), "-"))
        table.append(row)
        brute = next((v for nn, v in pick("brute_force", 3) if nn == n), None)
        if brute:
            red = [n, f"{int(brute):,}"]
            for m in ("backtracking", "branch_and_bound"):
                v = next(v for nn, v in pick(m, 3) if nn == n)
                red.append(f"{100 * (1 - v / brute):.1f}%")
            reduction.append(red)
    names = list(multistop.SOLVERS)
    times = []
    for n in ns:
        times.append([n] + [next((f"{v:.2f}" for nn, v in pick(m, 4) if nn == n), "-") for m in names])
    return {"nodes": (["cities"] + names, table),
            "times": (["cities"] + [m + " (ms)" for m in names], times),
            "reduction": (["cities", "brute-force nodes", "backtracking saves", "branch & bound saves"],
                          reduction)}


def run_real(ks, samples):
    print("[4/4] multi-stop on the real road dataset ...")
    g = TrafficGraph()
    start = "Ludhiana"
    others = sorted(set(g.nodes) - {start})
    rows = []
    for k in ks:
        agg = {m: [] for m in multistop.SOLVERS}
        for s in range(samples):
            stops = random.Random(77 * k + s).sample(others, k)
            costs = {}
            for r in g.compare_methods(start, stops, "distance"):
                agg[r["method"]].append(r["nodes"])
                costs[r["method"]] = r["cost"]
            assert max(costs.values()) - min(costs.values()) < 1e-6
        for m, v in agg.items():
            if v:
                rows.append((k, m, len(v), round(statistics.mean(v), 1)))
        print(f"   {k} stops done")
    write_csv("tsp_real_dataset.csv", ["stops", "method", "samples", "mean_nodes"], rows)
    table = []
    for k in ks:
        row = [k]
        for m in multistop.SOLVERS:
            row.append(next((f"{v:,.0f}" for kk, mm, _, v in rows if kk == k and mm == m), "-"))
        table.append(row)
    return {"nodes": (["stops"] + list(multistop.SOLVERS), table)}


# ====================================================================== main
def main():
    ap = argparse.ArgumentParser(description="Empirical performance analysis")
    ap.add_argument("--quick", action="store_true", help="smaller sizes, runs in ~30 s")
    quick = ap.parse_args().quick
    os.makedirs(RESULTS, exist_ok=True)
    t0 = time.perf_counter()

    if quick:
        s1 = run_sorting([100, 200, 400, 800, 1600], repeats=1)
        s2 = run_shortest_paths([100, 200, 400, 800, 1600], 1, array_max=1600, bf_full_max=400)
        s3 = run_tsp(range(4, 10), 3, {"brute_force": 8, "backtracking": 9,
                                       "branch_and_bound": 9, "held_karp": 9})
        s4 = run_real([2, 3, 4, 5, 6], 3)
    else:
        s1 = run_sorting([250, 500, 1000, 2000, 4000], repeats=3)
        s2 = run_shortest_paths([200, 400, 800, 1600, 3200, 6400], 3, array_max=3200, bf_full_max=800)
        s3 = run_tsp(range(4, 14), 5, {"brute_force": 10, "backtracking": 12,
                                       "branch_and_bound": 13, "held_karp": 13})
        s4 = run_real([2, 3, 4, 5, 6, 7, 8], 5)

    sections = [
        ("Experiment 1 - Sorting: running time on random input", s1["times"]),
        ("Experiment 1 - Sorting: measured growth exponent", s1["expo"]),
        ("Experiment 1 - Sorting: comparisons in best / average / worst cases (largest n)", s1["cases"]),
        ("Experiment 5 - Shortest paths: running time", s2["times"]),
        ("Experiment 5 - Shortest paths: measured growth exponent", s2["expo"]),
        ("Experiments 4 and 6 - Multi-stop: mean nodes explored (random Euclidean instances)", s3["nodes"]),
        ("Experiments 4 and 6 - Multi-stop: mean running time", s3["times"]),
        ("Experiments 4 and 6 - Multi-stop: search space saved versus brute force", s3["reduction"]),
        ("Real dataset (roads.csv, start = Ludhiana): mean nodes explored", s4["nodes"]),
    ]
    with open(os.path.join(RESULTS, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# Benchmark summary ({'quick' if quick else 'full'} run)\n\n")
        for title, (header, rows) in sections:
            fh.write(f"## {title}\n\n{md_table(header, rows)}\n\n")
    print(f"\nDone in {time.perf_counter() - t0:.0f} s.  See the results/ folder (summary.md, *.csv, *.png).")


if __name__ == "__main__":
    main()
