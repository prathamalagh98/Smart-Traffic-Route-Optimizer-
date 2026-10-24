"""Command-line interface for the Smart Traffic Route Optimizer (no GUI needed).

Examples
    python cli.py cities
    python cli.py route Ludhiana Chandigarh --by time --alternatives 5
    python cli.py tour Ludhiana Patiala Ambala Mohali Ropar --method branch_and_bound
    python cli.py tour Ludhiana Patiala Ambala Mohali Ropar --compare
"""
import argparse
import sys

import multistop
from graph import CRITERIA, DataError, SORTERS, UNITS, TrafficGraph


def arrow(path):
    return " -> ".join(path)


def cmd_cities(g, _args):
    print(f"{len(g.nodes)} cities, {len(g.roads)} roads")
    for c in sorted(g.nodes):
        print(f"  {c:<18} connects to: {', '.join(sorted(g.neighbours[c]))}")


def cmd_route(g, a):
    r = g.shortest_route(a.source, a.destination, a.by)
    if r is None:
        print(f"No road connection between {a.source} and {a.destination}.")
        return 1
    print(f"Best route by {a.by}: {arrow(r['path'])}")
    print(f"  distance {r['distance']:.1f} km | time {r['time']:.1f} min | fuel {r['fuel']:.2f} L"
          f" | Dijkstra settled {r['explored']}/{len(g.nodes)} cities")
    if a.alternatives:
        top, total, comps = g.ranked_routes(a.source, a.destination, a.by, a.alternatives, a.sort)
        print(f"\n{total} simple routes exist; top {len(top)} ranked by {a.by} "
              f"({a.sort} sort, {comps} comparisons):")
        for i, t in enumerate(top, 1):
            print(f"  {i}. {t['distance']:6.1f} km {t['time']:6.1f} min {t['fuel']:5.2f} L  "
                  f"{arrow(t['path'])}")
    return 0


def cmd_tour(g, a):
    start, stops = a.cities[0], a.cities[1:]
    if not stops:
        print("Give a start city followed by at least one stop.")
        return 1
    if a.compare:
        results = g.compare_methods(start, stops, a.by)
        print(f"{'algorithm':<18}{'cost':>9}{'nodes':>10}{'ms':>10}")
        for r in results:
            print(f"{r['method']:<18}{r['cost']:>9.1f}{r['nodes']:>10}{r['elapsed_ms']:>10.2f}")
        r = results[-1]
    else:
        r = g.plan_tour(start, stops, a.by, a.method)
        print(f"Algorithm: {r['method']}  (explored {r['nodes']} nodes in {r['elapsed_ms']:.2f} ms)")
    print(f"\nVisiting order: {arrow(r['order'])}")
    print(f"Full road path: {arrow(r['path'])}")
    print(f"Total {r['distance']:.1f} km | {r['time']:.1f} min | {r['fuel']:.2f} L "
          f"(optimised {a.by}: {r['cost']:.1f} {UNITS[a.by]})")
    return 0


def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("cities", help="list cities and their neighbours").set_defaults(func=cmd_cities)

    r = sub.add_parser("route", help="best route between two cities (Dijkstra)")
    r.add_argument("source")
    r.add_argument("destination")
    r.add_argument("--by", choices=CRITERIA, default="distance")
    r.add_argument("--alternatives", type=int, default=0, metavar="N",
                   help="also list the N best alternative routes")
    r.add_argument("--sort", choices=tuple(SORTERS), default="merge")
    r.set_defaults(func=cmd_route)

    t = sub.add_parser("tour", help="visit several cities and return (TSP)")
    t.add_argument("cities", nargs="+", help="start city followed by the stops")
    t.add_argument("--by", choices=CRITERIA, default="distance")
    t.add_argument("--method", choices=tuple(multistop.SOLVERS), default="branch_and_bound")
    t.add_argument("--compare", action="store_true", help="run every algorithm and compare")
    t.set_defaults(func=cmd_tour)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        g = TrafficGraph()
        return args.func(g, args) or 0
    except (DataError, KeyError, ValueError, OSError) as exc:
        print(f"Error: {exc.args[0] if isinstance(exc, KeyError) else exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
