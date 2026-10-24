"""Smart Traffic Route Optimizer - desktop GUI (Tkinter).

Run:  python app.py

Tab 1  Route Finder        Dijkstra + ranking of every alternative route (Merge/Quick/Bubble sort)
Tab 2  Multi-Stop Planner  Backtracking, Branch & Bound, Held-Karp, Brute force on the same trip
Tab 3  Performance         Charts produced by analysis.py (empirical complexity analysis)
"""
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from graph import CRITERIA, DataError, MAX_BRUTE_FORCE_STOPS, TrafficGraph, UNITS
from visualizer import MapCanvas

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")

CRITERIA_LABELS = {"Shortest distance": "distance", "Fastest time": "time", "Least fuel": "fuel"}
SORT_LABELS = {"Merge Sort": "merge", "Quick Sort": "quick", "Bubble Sort": "bubble"}
METHOD_LABELS = {
    "Backtracking (pruned)": "backtracking",
    "Branch & Bound": "branch_and_bound",
    "Held-Karp (DP)": "held_karp",
    "Brute force": "brute_force",
}
METHOD_NAMES = {v: k for k, v in METHOD_LABELS.items()}


def arrow(path):
    return " \u2192 ".join(path)


def hours(minutes):
    h, m = divmod(int(round(minutes)), 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


class App(ttk.Frame):
    def __init__(self, root, graph):
        super().__init__(root, padding=8)
        self.g = graph
        self.cities = sorted(graph.nodes)
        self.pack(fill="both", expand=True)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_route = ttk.Frame(nb, padding=6)
        self.tab_tour = ttk.Frame(nb, padding=6)
        self.tab_perf = ttk.Frame(nb, padding=6)
        nb.add(self.tab_route, text="  Route Finder  ")
        nb.add(self.tab_tour, text="  Multi-Stop Planner  ")
        nb.add(self.tab_perf, text="  Performance Analysis  ")

        self._build_route_tab()
        self._build_tour_tab()
        self._build_perf_tab()

        ttk.Label(self, anchor="w", foreground="#5f6b76",
                  text=f"Dataset: {len(graph.nodes)} cities, {len(graph.roads)} roads  |  "
                       f"time = distance / speed x congestion  |  fuel = 0.07 L/km x congestion"
                  ).pack(fill="x", pady=(6, 0))

    # ================================================================== tab 1
    def _build_route_tab(self):
        left = ttk.Frame(self.tab_route, width=450)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        box = ttk.LabelFrame(left, text="Find the best route (Dijkstra)", padding=8)
        box.pack(fill="x")
        self.r_src = self._combo(box, "From", self.cities, 0, default="Ludhiana")
        self.r_dst = self._combo(box, "To", self.cities, 1, default="Chandigarh")
        self.r_crit = self._combo(box, "Optimise for", list(CRITERIA_LABELS), 2,
                                  default="Fastest time")
        self.r_sort = self._combo(box, "Rank routes with", list(SORT_LABELS), 3,
                                  default="Merge Sort")
        btns = ttk.Frame(box)
        btns.grid(row=4, column=0, columnspan=2, pady=(8, 0), sticky="ew")
        ttk.Button(btns, text="Find route", command=self.find_route).pack(side="left", expand=True, fill="x")
        ttk.Button(btns, text="Swap", width=7, command=self.swap).pack(side="left", padx=(6, 0))

        self.r_result = tk.Text(left, height=11, wrap="word", relief="flat", bg="#eef3f8",
                                font=("Segoe UI", 10), padx=8, pady=6, state="disabled")
        self.r_result.pack(fill="x", pady=8)

        ttk.Label(left, text="Alternative routes (click a row to preview)").pack(anchor="w")
        cols = ("rank", "km", "min", "litres", "route")
        self.r_tree = ttk.Treeview(left, columns=cols, show="headings", height=8)
        for c, w, t in (("rank", 34, "#"), ("km", 52, "km"), ("min", 52, "min"),
                        ("litres", 48, "L"), ("route", 480, "Route")):
            self.r_tree.heading(c, text=t)
            self.r_tree.column(c, width=w, anchor="w" if c == "route" else "e", stretch=c == "route")
        self.r_tree.pack(fill="both", expand=True)
        self.r_tree.bind("<<TreeviewSelect>>", self._preview_alternative)
        self.r_routes = []
        self.r_map = MapCanvas(self.tab_route, self.g)
        self.r_map.pack(side="left", fill="both", expand=True)

    def swap(self):
        a, b = self.r_src.get(), self.r_dst.get()
        self.r_src.set(b)
        self.r_dst.set(a)

    def find_route(self):
        src, dst = self.r_src.get(), self.r_dst.get()
        if src == dst:
            messagebox.showinfo("Pick two cities", "Source and destination are the same city.")
            return
        crit = CRITERIA_LABELS[self.r_crit.get()]
        route = self.g.shortest_route(src, dst, crit)
        if route is None:
            messagebox.showwarning("No route", f"There is no road connection from {src} to {dst}.")
            return
        sorter = SORT_LABELS[self.r_sort.get()]
        top, total, comps = self.g.ranked_routes(src, dst, crit, top=10, sorter=sorter)

        self.r_map.show_route(route["path"])
        text = (f"Best route by {crit}:\n{arrow(route['path'])}\n\n"
                f"Distance : {route['distance']:.1f} km\n"
                f"Time     : {hours(route['time'])}\n"
                f"Fuel     : {route['fuel']:.2f} L\n\n"
                f"Dijkstra settled {route['explored']} of {len(self.g.nodes)} cities.\n"
                f"{total} possible routes exist; ranked with {self.r_sort.get()} "
                f"({comps} comparisons).")
        self._set_text(self.r_result, text)

        self.r_tree.delete(*self.r_tree.get_children())
        self.r_routes = top
        for i, r in enumerate(top, 1):
            self.r_tree.insert("", "end", iid=str(i - 1),
                               values=(i, f"{r['distance']:.0f}", f"{r['time']:.0f}",
                                       f"{r['fuel']:.1f}", arrow(r["path"])))

    def _preview_alternative(self, _event):
        sel = self.r_tree.selection()
        if sel:
            self.r_map.show_route(self.r_routes[int(sel[0])]["path"], color="#8e44ad")

    # ================================================================== tab 2
    def _build_tour_tab(self):
        left = ttk.Frame(self.tab_tour, width=450)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        box = ttk.LabelFrame(left, text="Visit several cities and return", padding=8)
        box.pack(fill="x")
        self.t_start = self._combo(box, "Start / end", self.cities, 0, default="Ludhiana")
        self.t_crit = self._combo(box, "Optimise for", list(CRITERIA_LABELS), 1,
                                  default="Shortest distance")
        self.t_method = self._combo(box, "Algorithm", list(METHOD_LABELS), 2,
                                    default="Branch & Bound")
        ttk.Label(box, text="Stops (Ctrl/Shift-click)").grid(row=3, column=0, columnspan=2,
                                                            sticky="w", pady=(8, 2))
        self.t_list = tk.Listbox(box, selectmode="extended", height=11, exportselection=False)
        for c in self.cities:
            self.t_list.insert("end", c)
        for c in ("Patiala", "Ambala", "Mohali", "Ropar"):
            self.t_list.selection_set(self.cities.index(c))
        self.t_list.grid(row=4, column=0, columnspan=2, sticky="ew")
        btns = ttk.Frame(box)
        btns.grid(row=5, column=0, columnspan=2, pady=(8, 0), sticky="ew")
        ttk.Button(btns, text="Plan tour", command=self.plan_tour).pack(side="left", expand=True, fill="x")
        ttk.Button(btns, text="Compare all", command=self.compare_all).pack(side="left", expand=True,
                                                                              fill="x", padx=(6, 0))

        self.t_result = tk.Text(left, height=10, wrap="word", relief="flat", bg="#fdf3e7",
                                font=("Segoe UI", 10), padx=8, pady=6, state="disabled")
        self.t_result.pack(fill="x", pady=8)

        ttk.Label(left, text="Algorithm comparison (same trip)").pack(anchor="w")
        cols = ("method", "cost", "nodes", "ms")
        self.t_tree = ttk.Treeview(left, columns=cols, show="headings", height=5)
        for c, w, t in (("method", 190, "Algorithm"), ("cost", 70, "Cost"),
                        ("nodes", 80, "Nodes"), ("ms", 60, "ms")):
            self.t_tree.heading(c, text=t)
            self.t_tree.column(c, width=w, anchor="w" if c == "method" else "e")
        self.t_tree.pack(fill="x")
        self.t_map = MapCanvas(self.tab_tour, self.g)
        self.t_map.pack(side="left", fill="both", expand=True)

    def _tour_inputs(self):
        start = self.t_start.get()
        stops = [self.cities[i] for i in self.t_list.curselection() if self.cities[i] != start]
        if not stops:
            messagebox.showinfo("Select stops", "Select at least one stop other than the start city.")
            return None
        return start, stops, CRITERIA_LABELS[self.t_crit.get()]

    def _show_tour(self, r, crit):
        unit = UNITS[crit]
        self.t_map.show_tour(r["order"], r["path"])
        self._set_text(self.t_result,
                       f"{METHOD_NAMES[r['method']]}\nVisiting order:\n{arrow(r['order'])}\n\n"
                       f"Distance : {r['distance']:.1f} km\nTime     : {hours(r['time'])}\n"
                       f"Fuel     : {r['fuel']:.2f} L\n"
                       f"Optimised {crit}: {r['cost']:.1f} {unit}")

    def plan_tour(self):
        inp = self._tour_inputs()
        if not inp:
            return
        start, stops, crit = inp
        try:
            r = self.g.plan_tour(start, stops, crit, METHOD_LABELS[self.t_method.get()])
        except ValueError as exc:
            messagebox.showwarning("Cannot plan tour", str(exc))
            return
        self._show_tour(r, crit)
        self.t_tree.delete(*self.t_tree.get_children())
        self.t_tree.insert("", "end", values=(METHOD_NAMES[r["method"]], f"{r['cost']:.1f}",
                                              r["nodes"], f"{r['elapsed_ms']:.2f}"))

    def compare_all(self):
        inp = self._tour_inputs()
        if not inp:
            return
        start, stops, crit = inp
        results = self.g.compare_methods(start, stops, crit)
        self.t_tree.delete(*self.t_tree.get_children())
        for r in results:
            self.t_tree.insert("", "end", values=(METHOD_NAMES[r["method"]], f"{r['cost']:.1f}",
                                                  r["nodes"], f"{r['elapsed_ms']:.2f}"))
        self._show_tour(results[-1], crit)
        if len({round(r["cost"], 6) for r in results}) == 1:
            note = "All algorithms found the same optimal cost."
        else:
            note = "Warning: algorithms disagree!"
        skipped = ""
        if len(stops) > MAX_BRUTE_FORCE_STOPS:
            skipped = f" Brute force skipped (>{MAX_BRUTE_FORCE_STOPS} stops)."
        self._append_text(self.t_result, f"\n\n{note}{skipped}")

    # ================================================================== tab 3
    def _build_perf_tab(self):
        bar = ttk.Frame(self.tab_perf)
        bar.pack(fill="x")
        ttk.Label(bar, text="Chart:").pack(side="left")
        self.p_choice = ttk.Combobox(bar, state="readonly", width=40)
        self.p_choice.pack(side="left", padx=6)
        self.p_choice.bind("<<ComboboxSelected>>", lambda e: self._show_chart())
        ttk.Button(bar, text="Refresh", command=self._refresh_charts).pack(side="left")
        self.p_run = ttk.Button(bar, text="Re-run benchmark (~30 s)", command=self._run_benchmark)
        self.p_run.pack(side="left", padx=6)
        self.p_status = ttk.Label(bar, foreground="#5f6b76",
                                  text="Same as: python analysis.py")
        self.p_status.pack(side="left", padx=6)
        self.p_image = ttk.Label(self.tab_perf, anchor="center")
        self.p_image.pack(fill="both", expand=True, pady=8)
        self._photo = None
        self._refresh_charts()

    def _refresh_charts(self):
        files = sorted(f for f in os.listdir(RESULTS_DIR) if f.endswith(".png")) \
            if os.path.isdir(RESULTS_DIR) else []
        self.p_choice["values"] = files
        if files:
            if self.p_choice.get() not in files:
                self.p_choice.set(files[0])
            self._show_chart()
        else:
            self.p_choice.set("")
            self.p_image.configure(image="", text="No charts yet - run the benchmark.")

    def _show_chart(self):
        path = os.path.join(RESULTS_DIR, self.p_choice.get())
        try:
            photo = tk.PhotoImage(file=path)
        except tk.TclError:
            self.p_image.configure(image="", text="Could not open this chart.")
            return
        factor = max(1, -(-photo.width() // max(self.p_image.winfo_width(), 1100)))
        self._photo = photo.subsample(factor) if factor > 1 else photo
        self.p_image.configure(image=self._photo, text="")

    def _run_benchmark(self):
        self.p_run.state(["disabled"])
        self.p_status.configure(text="Running analysis.py ...")
        self._bench_result = None

        def work():
            try:
                self._bench_result = subprocess.run(
                    [sys.executable, os.path.join(BASE_DIR, "analysis.py")],
                    cwd=BASE_DIR, capture_output=True, text=True, timeout=600).returncode
            except Exception:
                self._bench_result = -1

        threading.Thread(target=work, daemon=True).start()
        self.after(500, self._poll_benchmark)

    def _poll_benchmark(self):
        if self._bench_result is None:
            self.after(500, self._poll_benchmark)
            return
        ok = self._bench_result == 0
        self.p_status.configure(text="Benchmark finished." if ok else "Benchmark failed.")
        self.p_run.state(["!disabled"])
        self._refresh_charts()

    # ================================================================== helpers
    @staticmethod
    def _combo(parent, label, values, row, default=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        cb = ttk.Combobox(parent, values=values, state="readonly", width=24)
        cb.grid(row=row, column=1, sticky="ew", pady=2, padx=(8, 0))
        cb.set(default if default in values else values[0])
        parent.columnconfigure(1, weight=1)
        return cb

    @staticmethod
    def _set_text(widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    @staticmethod
    def _append_text(widget, text):
        widget.configure(state="normal")
        widget.insert("end", text)
        widget.configure(state="disabled")


def main():
    root = tk.Tk()
    root.title("Smart Traffic Route Optimizer - DAA Project")
    root.geometry("1280x780")
    root.minsize(1000, 640)
    try:
        graph = TrafficGraph()
    except (DataError, OSError) as exc:
        messagebox.showerror("Cannot load road data", str(exc))
        root.destroy()
        return
    App(root, graph)
    root.mainloop()


if __name__ == "__main__":
    main()
