# Smart Traffic Route Optimizer

**Course:** Design and Analysis of Algorithms (DAA) - Project based on Units I, II and III
**Language:** Python 3.8+ (standard library only; `matplotlib` is needed just for the benchmark charts)

A route-planning system for a road network in Punjab / Chandigarh region. It finds the best route
between two cities, ranks every alternative route, and plans multi-stop trips - and it *measures* the
algorithms it uses, so the theoretical complexities taught in the course can be checked against real data.

## Quick start

```bash
python app.py                 # desktop GUI (Tkinter)
python cli.py cities          # command-line version, no GUI needed
python cli.py route Ropar Ambala --by time --alternatives 5
python cli.py tour Ludhiana Patiala Ambala Mohali Ropar --compare
python analysis.py            # full benchmark: CSV tables + charts in results/  (about 30 s)
python tests.py               # 25 automated tests
```

Tkinter ships with Python on Windows and macOS. On Debian/Ubuntu: `sudo apt install python3-tk`.
Benchmark charts need `pip install -r requirements.txt`.

## What it does (and which syllabus topic each part covers)

| Feature | Algorithm | File | Syllabus |
|---|---|---|---|
| Best route by **distance / time / fuel** | Dijkstra with a binary heap, O((V+E) log V) | `shortest_path.py` | Unit 3, Exp 5 |
| Compare with other shortest-path methods | Array Dijkstra O(V^2), Bellman-Ford O(VE) | `shortest_path.py` | Unit 3, Exp 5 |
| List **every alternative route** | Backtracking DFS over simple paths | `graph.py` | Unit 2, Exp 4 |
| **Rank** the alternatives | Bubble, Merge and Quick sort (own implementations) | `sorting.py` | Unit 1, Exp 1 |
| **Multi-stop trip** (visit cities, return) | Brute force, Backtracking with pruning, Least-Cost Branch & Bound, Held-Karp DP | `multistop.py` | Unit 2 Exp 4, Unit 3 Exp 6 |
| **Performance analysis** | Timing, comparison counts, growth exponents, charts | `analysis.py` | Exp 1, 5, 6 + project |

## Project structure

```
app.py            Tkinter GUI: Route Finder, Multi-Stop Planner, Performance Analysis tabs
cli.py            same features from the command line
graph.py          road network, cost model, ties all algorithms to the data
shortest_path.py  Dijkstra (heap and array), Bellman-Ford
sorting.py        Bubble, Merge, Quick sort (return result + comparison count)
multistop.py      brute force, backtracking, branch & bound, Held-Karp
visualizer.py     map drawing widget used by the GUI
analysis.py       benchmark script -> results/
tests.py          unit tests
data/roads.csv    19 roads: distance_km, avg_speed_kmh, congestion
data/cities.csv   map coordinates (drawing only)
results/          benchmark tables (CSV), charts (PNG) and summary.md
PROJECT_REPORT.md full project report
```

## Cost model

For a road of length `d` km, average speed `v` km/h and congestion factor `c >= 1`:

* time = `d / v * 60 * c` minutes
* fuel = `d * 0.07 * c` litres (stop-and-go traffic burns more fuel)

Because speed and congestion differ per road, the *shortest* route is not always the *fastest*
(example: Ropar -> Ambala is 95 km / 126.6 min by distance, but 100 km / 123.2 min by time).

## Using your own data

Edit `data/roads.csv` (columns `source,destination,distance_km,avg_speed_kmh,congestion`).
The file is validated on load: distances and speeds must be positive (Dijkstra needs non-negative
weights), congestion must be >= 1, and duplicate or self-loop roads are rejected with a clear message.
A city without coordinates in `data/cities.csv` is placed automatically on a circle in the map.

**Note:** the road distances, speeds and congestion factors are approximate/illustrative values chosen for
demonstration, not survey data.
