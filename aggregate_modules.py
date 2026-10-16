#!/usr/bin/env python3
"""Aggregate folder-level #include dependencies to the Table 1 modules.

Input:  deps_edges.csv   (from module_deps.py --no-tests; columns from,to,files,paths)
Output: module_edges.csv  module-level edges (files = source files with an #include)
        decomposition.dot module diagram (render: dot -Tsvg decomposition.dot -o decomposition.svg)
        cif_mim.csv       CIF and MIM per module

Metrics (adapted from Gintoro et al.; n = number of modules):
  CIF(m) = |modules depending on m directly or transitively| / (n - 1)
  MIM(m) = 1 - |modules m depends on directly| / (n - 1)
An edge counts as a dependency if files >= --min (default 1).

Usage: python3 aggregate_modules.py [deps_edges.csv] [--min N]
"""
import argparse, csv
from collections import Counter, defaultdict

# Table 1: Decomposition view (module -> folders in app/)
MODULES = {
    "Core":              ["core", "gegl", "text", "path", "paint", "operations"],
    "Display":           ["display", "widgets", "propgui", "gui", "menus", "actions", "dialogs"],
    "Tools":             ["tools"],
    "Config":            ["config"],
    "Plug-in interface": ["plug-in", "pdb", "file", "file-data", "xcf"],
}
# Diagram-only: stereotypes for back-edges (verified manually, see report)
BACK_EDGES = {
    ("Display", "Tools"): "dispatches events",   # display -> tools/tool_manager.h
    ("Core", "Plug-in interface"): "creates",    # core/gimp.c creates plug-in manager + PDB
    ("Config", "Core"): "uses types",            # mostly core-types.h / core-enums.h
}

ap = argparse.ArgumentParser()
ap.add_argument("input", nargs="?", default="deps_edges.csv")
ap.add_argument("--min", type=int, default=1)
a = ap.parse_args()

folder2mod = {f"app/{f}": m for m, fs in MODULES.items() for f in fs}
names = list(MODULES)
n = len(names)

# 1. Aggregate: count distinct source files per module pair (a file including
#    both core/ and gegl/ counts once toward Core).
files = defaultdict(set)
for r in csv.DictReader(open(a.input)):
    s, d = folder2mod.get(r["from"]), folder2mod.get(r["to"])
    if s and d and s != d:
        files[(s, d)].update(r["paths"].split(";"))
w = Counter({e: len(fs) for e, fs in files.items()})

with open("module_edges.csv", "w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["from", "to", "files"])
    for (s, d), c in sorted(w.items(), key=lambda kv: -kv[1]):
        wr.writerow([s, d, c])

# 2. CIF / MIM
deps = defaultdict(set)                         # m -> modules m depends on
for (s, d), c in w.items():
    if c >= a.min:
        deps[s].add(d)
rdeps = defaultdict(set)                        # m -> modules depending on m
for s, ds in deps.items():
    for d in ds:
        rdeps[d].add(s)

def affected(m):                                # transitive reverse closure
    seen, stack = set(), [m]
    while stack:
        for u in rdeps[stack.pop()]:
            if u not in seen and u != m:
                seen.add(u); stack.append(u)
    return seen

with open("cif_mim.csv", "w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["module", "affected_modules", "CIF", "outgoing_dependencies", "MIM"])
    for m in names:
        af, out = affected(m), deps[m]
        wr.writerow([m, ";".join(sorted(af)), f"{len(af)/(n-1):.2f}",
                     ";".join(sorted(out)), f"{1-len(out)/(n-1):.2f}"])

# 3. DOT
ID = {"Core": "Core", "Display": "Display", "Tools": "Tools",
      "Config": "Config", "Plug-in interface": "Plugin"}
FILL = {"Core": "#BBDEFB", "Display": "#C8E6C9", "Tools": "#C8E6C9",
        "Config": "#E1BEE7", "Plug-in interface": "#FFE0B2"}
def wrap(fs):                                   # max 4 folders per line
    return ",\\n".join(", ".join(fs[i:i+4]) for i in range(0, len(fs), 4))
def pen(c):
    return 4 if c >= 300 else 2.5 if c >= 120 else 2.2 if c >= 100 else 1.6 if c >= 30 else 1.2

with open("decomposition.dot", "w", encoding="utf-8") as f:
    f.write('digraph G {\n'
            '  graph [rankdir=TB, nodesep=0.9, ranksep=0.9, fontname="Helvetica", pad=0.3, labelloc=b, fontsize=11,\n'
            '         label="GIMP decomposition view — module relationships\\n'
            '(edge label = «stereotype» (number of source files with #include))"];\n'
            '  node [shape=tab, style="filled,rounded", fontname="Helvetica-Bold", fontsize=14, penwidth=1.4, margin="0.3,0.15"];\n'
            '  edge [fontname="Helvetica", fontsize=11, arrowhead=vee, arrowsize=0.9, color="#333333"];\n')
    for m in names:
        f.write(f'  {ID[m]} [label="{m}\\n({wrap(MODULES[m])})", fillcolor="{FILL[m]}"];\n')
    f.write('  {rank=same; Display; Tools}\n')
    for (s, d), c in sorted(w.items(), key=lambda kv: -kv[1]):
        if c < a.min:
            continue
        if (s, d) in BACK_EDGES:
            attrs = (f'label="«{BACK_EDGES[(s, d)]}» ({c})", style=dashed, '
                     f'color="#C62828", fontcolor="#C62828"')
        else:
            attrs = f'label=" «uses» ({c})", penwidth={pen(c)}'
        if (s, d) in {("Tools", "Display"), ("Display", "Tools")}:
            attrs += ", constraint=false"
        f.write(f'  {ID[s]} -> {ID[d]} [{attrs}];\n')
    f.write('}\n')

print(open("cif_mim.csv").read())
