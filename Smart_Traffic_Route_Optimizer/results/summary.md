# Benchmark summary (full run)

## Experiment 1 - Sorting: running time on random input

| n | bubble (ms) | merge (ms) | quick (ms) |
|---|---|---|---|
| 250 | 4.1 | 0.6 | 0.5 |
| 500 | 11.0 | 0.7 | 0.6 |
| 1000 | 42.3 | 1.5 | 1.2 |
| 2000 | 172.6 | 3.3 | 3.5 |
| 4000 | 713.7 | 9.6 | 6.0 |

## Experiment 1 - Sorting: measured growth exponent

| algorithm | measured exponent | theory |
|---|---|---|
| bubble | 1.89 | 2 (n²) |
| merge | 1.00 | ~1.1 (n log n) |
| quick | 0.99 | ~1.1 (n log n) |

## Experiment 1 - Sorting: comparisons in best / average / worst cases (largest n)

| algorithm | input | n | comparisons |
|---|---|---|---|
| bubble | sorted | 4000 | 3999 |
| bubble | random | 4000 | 7991784 |
| bubble | reversed | 4000 | 7998000 |
| quick_last | sorted | 4000 | 7568437 |
| quick | sorted | 4000 | 54747 |
| merge | sorted | 4000 | 23728 |

## Experiment 5 - Shortest paths: running time

| V | E | heap Dijkstra (ms) | array Dijkstra (ms) | Bellman-Ford early-exit (ms) | Bellman-Ford V-1 passes (ms) |
|---|---|---|---|---|---|
| 200 | 800 | 0.3 | 1.7 | 0.7 | 17.6 |
| 400 | 1600 | 0.6 | 6.7 | 2.3 | 88.9 |
| 800 | 3200 | 1.4 | 25.0 | 7.2 | 382.7 |
| 1600 | 6400 | 3.4 | 104.1 | 11.1 | - |
| 3200 | 12800 | 7.4 | 405.7 | 28.2 | - |
| 6400 | 25600 | 21.2 | - | 74.5 | - |

## Experiment 5 - Shortest paths: measured growth exponent

| algorithm | measured exponent in V (E = 4V) |
|---|---|
| dijkstra_heap | 1.25 |
| dijkstra_array | 1.98 |
| bellman_ford | 1.30 |
| bellman_ford_full | 2.22 |

## Experiments 4 and 6 - Multi-stop: mean nodes explored (random Euclidean instances)

| cities | brute_force | backtracking | branch_and_bound | held_karp |
|---|---|---|---|---|
| 4 | 16 | 15 | 4 | 12 |
| 5 | 65 | 55 | 14 | 32 |
| 6 | 326 | 233 | 32 | 80 |
| 7 | 1,957 | 909 | 89 | 192 |
| 8 | 13,700 | 3,525 | 98 | 448 |
| 9 | 109,601 | 18,153 | 481 | 1,024 |
| 10 | 986,410 | 81,689 | 823 | 2,304 |
| 11 | - | 399,551 | 3,309 | 5,120 |
| 12 | - | 965,242 | 6,125 | 11,264 |
| 13 | - | - | 23,677 | 24,576 |

## Experiments 4 and 6 - Multi-stop: mean running time

| cities | brute_force (ms) | backtracking (ms) | branch_and_bound (ms) | held_karp (ms) |
|---|---|---|---|---|
| 4 | 0.01 | 0.01 | 0.03 | 0.02 |
| 5 | 0.03 | 0.03 | 0.07 | 0.03 |
| 6 | 0.13 | 0.11 | 0.18 | 0.07 |
| 7 | 0.82 | 0.56 | 0.58 | 0.18 |
| 8 | 7.30 | 2.60 | 1.26 | 0.58 |
| 9 | 58.28 | 15.61 | 6.47 | 1.35 |
| 10 | 541.32 | 65.18 | 15.32 | 2.76 |
| 11 | - | 349.40 | 56.80 | 6.25 |
| 12 | - | 948.05 | 181.65 | 19.47 |
| 13 | - | - | 718.39 | 37.73 |

## Experiments 4 and 6 - Multi-stop: search space saved versus brute force

| cities | brute-force nodes | backtracking saves | branch & bound saves |
|---|---|---|---|
| 4 | 16 | 1.2% | 70.0% |
| 5 | 65 | 14.8% | 78.2% |
| 6 | 326 | 28.5% | 90.0% |
| 7 | 1,957 | 53.5% | 95.4% |
| 8 | 13,700 | 74.3% | 99.3% |
| 9 | 109,601 | 83.4% | 99.6% |
| 10 | 986,410 | 91.7% | 99.9% |

## Real dataset (roads.csv, start = Ludhiana): mean nodes explored

| stops | brute_force | backtracking | branch_and_bound | held_karp |
|---|---|---|---|---|
| 2 | 5 | 5 | 1 | 4 |
| 3 | 16 | 16 | 3 | 12 |
| 4 | 65 | 60 | 13 | 32 |
| 5 | 326 | 216 | 18 | 80 |
| 6 | 1,957 | 1,165 | 115 | 192 |
| 7 | 13,700 | 4,197 | 169 | 448 |
| 8 | 109,601 | 15,046 | 160 | 1,024 |

