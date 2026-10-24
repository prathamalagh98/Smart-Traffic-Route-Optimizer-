"""Map drawing widget used by app.py.

MapCanvas draws the road network and can overlay a route or a multi-stop tour.
The overlay is drawn *before* the distance labels so the labels of highlighted
roads stay readable.  Cities without coordinates in data/cities.csv are placed
on a circle automatically, so adding a city to roads.csv never crashes the GUI.
"""
import math
import tkinter as tk

BG = "#f7f9fc"
EDGE = "#b8c2cc"
EDGE_TEXT = "#5f6b76"
NODE_FILL = "#ffffff"
NODE_LINE = "#2c3e50"
START = "#2ecc71"
END = "#e74c3c"
ROUTE = "#2980b9"
TOUR = "#e67e22"
MARGIN_X, MARGIN_Y = 70, 50


class MapCanvas(tk.Canvas):
    def __init__(self, master, graph, **kw):
        kw.setdefault("bg", BG)
        kw.setdefault("highlightthickness", 1)
        kw.setdefault("highlightbackground", "#d0d7de")
        super().__init__(master, **kw)
        self.graph = graph
        self.positions = self._layout()
        self._state = {}
        self.bind("<Configure>", lambda e: self._redraw())

    # ------------------------------------------------------------------ layout
    def _layout(self):
        pos = dict(self.graph.positions)
        missing = [c for c in self.graph.nodes if c not in pos]
        if missing:
            xs = [p[0] for p in pos.values()] or [0.0]
            ys = [p[1] for p in pos.values()] or [0.0]
            cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
            radius = max(150.0, (max(xs) - min(xs)) / 4)
            for i, c in enumerate(missing):
                ang = 2 * math.pi * i / len(missing)
                pos[c] = (cx + radius * math.cos(ang), cy + radius * math.sin(ang))
        return pos

    def _to_screen(self, city):
        xs = [p[0] for p in self.positions.values()]
        ys = [p[1] for p in self.positions.values()]
        w = max(self.winfo_width(), 400)
        h = max(self.winfo_height(), 300)
        sx = (w - 2 * MARGIN_X) / max(max(xs) - min(xs), 1)
        sy = (h - 2 * MARGIN_Y) / max(max(ys) - min(ys), 1)
        x, y = self.positions[city]
        return MARGIN_X + (x - min(xs)) * sx, MARGIN_Y + (y - min(ys)) * sy

    # ------------------------------------------------------------------ public
    def clear_overlay(self):
        self._state = {}
        self._redraw()

    def show_route(self, path, color=ROUTE):
        """Highlight a single route; first city green, last city red."""
        self._state = {"path": list(path), "color": color,
                       "start": path[0], "end": path[-1], "numbers": {}}
        self._redraw()

    def show_tour(self, order, full_path, color=TOUR):
        """Highlight a tour. `order` = visiting order (start ... start)."""
        numbers = {}                      # start city -> 0 (drawn as "S"), stops -> 1, 2, 3 ...
        for i, c in enumerate(order[:-1]):
            numbers.setdefault(c, i)
        self._state = {"path": list(full_path), "color": color,
                       "start": order[0], "end": None, "numbers": numbers}
        self._redraw()

    # ------------------------------------------------------------------ drawing
    def _redraw(self):
        self.delete("all")
        g = self.graph
        on_path = set()
        path = self._state.get("path") or []
        for a, b in zip(path, path[1:]):
            on_path.add(frozenset((a, b)))

        # 1. plain roads
        for key in g.roads:
            if key in on_path:
                continue
            a, b = tuple(key)
            (x1, y1), (x2, y2) = self._to_screen(a), self._to_screen(b)
            self.create_line(x1, y1, x2, y2, fill=EDGE, width=2)

        # 2. highlighted roads (before labels, so labels stay visible)
        color = self._state.get("color", ROUTE)
        for a, b in zip(path, path[1:]):
            (x1, y1), (x2, y2) = self._to_screen(a), self._to_screen(b)
            self.create_line(x1, y1, x2, y2, fill=color, width=6,
                             capstyle="round", arrow="last" if self._state.get("end") is None
                             else None, arrowshape=(12, 14, 5))

        # 3. distance labels on top of every road
        for key, road in g.roads.items():
            a, b = tuple(key)
            (x1, y1), (x2, y2) = self._to_screen(a), self._to_screen(b)
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            text = f"{road['distance']:g} km"
            tid = self.create_text(mx, my, text=text, font=("Segoe UI", 8),
                                   fill="#ffffff" if key in on_path else EDGE_TEXT)
            x0, y0, xe, ye = self.bbox(tid)
            rect = self.create_rectangle(x0 - 2, y0 - 1, xe + 2, ye + 1, width=0,
                                         fill=color if key in on_path else BG)
            self.tag_lower(rect, tid)

        # 4. cities
        start, end = self._state.get("start"), self._state.get("end")
        numbers = self._state.get("numbers", {})
        for city in g.nodes:
            x, y = self._to_screen(city)
            fill = START if city == start else END if city == end else NODE_FILL
            self.create_oval(x - 11, y - 11, x + 11, y + 11, fill=fill,
                             outline=NODE_LINE, width=2)
            if city in numbers:
                label = "S" if numbers[city] == 0 else str(numbers[city])
                self.create_text(x, y, text=label, font=("Segoe UI", 9, "bold"),
                                 fill="#ffffff" if city == start else NODE_LINE)
            tid = self.create_text(x, y - 22, text=city, font=("Segoe UI", 10, "bold"),
                                   fill=NODE_LINE)
            x0, y0, xe, ye = self.bbox(tid)
            self.tag_lower(self.create_rectangle(x0 - 2, y0, xe + 2, ye, width=0, fill=BG), tid)
