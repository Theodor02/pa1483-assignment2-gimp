#!/usr/bin/env python3
"""Python 3 rewrite of GIMP's tools/module-dependencies.py.

Changes vs. the 2010 original:
- Discovers app/ modules from disk instead of a hardcoded (stale) list.
- Resolves #include "x/y.h" only to headers that actually exist in a module.
- Scans .c and .h files; edge weight = number of files with such an include.
- Reports cycles (strongly connected components).
- Writes DOT; render with Graphviz:  dot -Tsvg deps.dot -o deps.svg
  For the original's reduced view:   tred deps.dot | dot -Tsvg -o deps-tred.svg

Usage (from GIMP source root):  python3 module_deps.py [--min N] [--no-tests]
"""
import argparse, os, re, sys
from collections import defaultdict

LIBS = ["libgimp", "libgimpbase", "libgimpcolor", "libgimpconfig", "libgimpmath",
        "libgimpmodule", "libgimpthumb", "libgimpwidgets"]
EXTERNAL = {"GLib": ["glib.h", "glib-object.h", "gio/gio.h"], "GTK": ["gtk/gtk.h"],
            "GEGL": ["gegl.h"], "babl": ["babl/babl.h"], "Pango": ["pango/pango.h"],
            "Cairo": ["cairo.h"]}
IGNORED = {"libgimp/libgimp-intl.h"}  # i18n macro header, ignored by the original too
INC = re.compile(r'^\s*#\s*include\s+["<]([^">]+)[">]', re.M)

ap = argparse.ArgumentParser()
ap.add_argument("--min", type=int, default=1, help="drop edges with weight < N")
ap.add_argument("--no-tests", action="store_true", help="exclude app/tests")
ap.add_argument("-o", default="deps.dot")
a = ap.parse_args()
if not (os.path.isdir("app") and os.path.isdir("libgimp")):
    sys.exit("Run from GIMP source root")

app_mods = sorted(d for d in os.listdir("app") if os.path.isdir(f"app/{d}"))
if a.no_tests:
    app_mods.remove("tests")
mods = {f"app/{m}": f"app/{m}" for m in app_mods} | {l: l for l in LIBS}

# header path (as written in #include) -> module
hdr = {}
for m, path in mods.items():
    for root, _, files in os.walk(path):
        for f in files:
            if f.endswith(".h"):
                rel = os.path.relpath(os.path.join(root, f), path).replace(os.sep, "/")
                short = path.split("/")[-1]           # "core" or "libgimpbase"
                hdr[f"{short}/{rel}"] = m
for ext, hs in EXTERNAL.items():
    for h in hs:
        hdr[h] = ext

edges = defaultdict(set)                             # (src,dst) -> files
for m, path in mods.items():
    for root, _, files in os.walk(path):
        for f in files:
            if not f.endswith((".c", ".h")):
                continue
            fp = os.path.join(root, f)
            with open(fp, errors="ignore") as fh:
                for inc in INC.findall(fh.read()):
                    d = None if inc in IGNORED else hdr.get(inc)
                    if d and d != m:
                        edges[(m, d)].add(fp)

w = {e: len(fs) for e, fs in edges.items() if len(fs) >= a.min}

# Tarjan SCC for cycle report
g = defaultdict(list)
for s, d in w:
    g[s].append(d)
idx, low, st, on, sccs, n = {}, {}, [], set(), [], [0]
def sc(v):
    idx[v] = low[v] = n[0]; n[0] += 1; st.append(v); on.add(v)
    for u in g[v]:
        if u not in idx:
            sc(u); low[v] = min(low[v], low[u])
        elif u in on:
            low[v] = min(low[v], idx[u])
    if low[v] == idx[v]:
        c = []
        while True:
            u = st.pop(); on.discard(u); c.append(u)
            if u == v: break
        if len(c) > 1: sccs.append(sorted(c))
sys.setrecursionlimit(10000)
for v in list(g):
    if v not in idx: sc(v)

col = lambda x: "lawngreen" if x.startswith("app/") else ("coral1" if x.startswith("lib") else "lightblue")
nodes = {x for e in w for x in e}
with open(a.o, "w") as o:
    o.write("digraph gimp {\n  node [style=filled];\n")
    for x in sorted(nodes):
        o.write(f'  "{x}" [fillcolor={col(x)}];\n')
    for (s, d), c in sorted(w.items()):
        o.write(f'  "{s}" -> "{d}" [label="{c}"];\n')
    o.write("}\n")

with open(a.o.rsplit(".", 1)[0] + "_edges.csv", "w") as o:
    o.write("from,to,files,paths\n")
    for (s, d), c in sorted(w.items(), key=lambda kv: -kv[1]):
        o.write(f"{s},{d},{c},{';'.join(sorted(edges[(s, d)]))}\n")

print(f"{len(nodes)} modules, {len(w)} edges -> {a.o}")
for c in sccs:
    print("Cycle group:", ", ".join(c))
