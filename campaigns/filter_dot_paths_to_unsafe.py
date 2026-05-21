#!/usr/bin/env python3
"""Filter a DOT digraph keeping only nodes/edges that lie on paths
that lead to an unsafe state, plus legend nodes.

Usage:
  python scripts/filter_dot_paths_to_unsafe.py input.dot [output.dot]

Detection heuristics for "unsafe": node attributes containing
`red`, `unsafe` or `fail` in `color`, `fillcolor` or `label`, or a
name containing those words. Legend nodes are preserved when their
name starts with `legend_`.
"""

import argparse
import sys
from collections import defaultdict, deque

try:
    import pydot
except Exception as e:
    print("This script requires pydot. Install with: pip install pydot", file=sys.stderr)
    raise


def strip_quotes(s: str) -> str:
    if s is None:
        return s
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s


def is_unsafe_node(node: pydot.Node) -> bool:
    name = strip_quotes(node.get_name() or '')
    attrs = {k.lower(): v for k, v in (node.get_attributes() or {}).items()}
    # Check name
    lname = name.lower()
    if 'unsafe' in lname or 'fail' in lname or 'error' in lname:
        return True
    # Check common attributes
    for key in ('color', 'fillcolor', 'style', 'penwidth'):
        v = attrs.get(key)
        if not v:
            continue
        if 'red' in v.lower() or 'unsafe' in v.lower() or 'fail' in v.lower():
            return True
    # label may be HTML; check textual content
    lab = attrs.get('label', '')
    if lab and ('unsafe' in lab.lower() or 'fail' in lab.lower()):
        return True
    return False


def is_legend_node(node: pydot.Node) -> bool:
    name = strip_quotes(node.get_name() or '')
    if name.startswith('legend_'):
        return True
    # some legends may be named tasks_info etc.; preserve any explicitly
    # labelled legend nodes (heuristic: name contains 'legend' or 'tasks_info')
    if 'legend' in name.lower() or 'tasks_info' in name.lower():
        return True
    return False


def build_adjacency(graph: pydot.Dot):
    adj = defaultdict(list)
    nodes = set()
    for edge in graph.get_edges():
        src = strip_quotes(edge.get_source())
        dst = strip_quotes(edge.get_destination())
        nodes.add(src)
        nodes.add(dst)
        adj[src].append(dst)
    return dict(adj), nodes


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('input')
    p.add_argument('output', nargs='?', help='output DOT file (default: input_unsafe_paths.dot)')
    args = p.parse_args(argv)

    graphs = pydot.graph_from_dot_file(args.input)
    if not graphs:
        print('Unable to parse DOT file', file=sys.stderr)
        sys.exit(2)
    graph = graphs[0]

    adj, seen_nodes = build_adjacency(graph)

    # map node name -> pydot.Node (original nodes)
    node_map = {}
    for n in graph.get_nodes():
        name = strip_quotes(n.get_name())
        if name in (None, ''):
            continue
        node_map[name] = n

    # Find unsafe nodes
    unsafe = set()
    for name, node in node_map.items():
        if is_unsafe_node(node):
            unsafe.add(name)

    if not unsafe:
        print('No unsafe nodes detected with default heuristics. Exiting.', file=sys.stderr)
        # Still produce an empty filtered graph with legends only

    # Build reverse adjacency
    rev = defaultdict(list)
    for u, vs in adj.items():
        for v in vs:
            rev[v].append(u)

    # BFS/DFS backwards from unsafe nodes to collect all nodes that can reach them
    reachable = set(unsafe)
    dq = deque(unsafe)
    while dq:
        v = dq.popleft()
        for u in rev.get(v, []):
            if u not in reachable:
                reachable.add(u)
                dq.append(u)

    # Always include legend nodes and any nodes without edges but present in node_map
    for name, node in node_map.items():
        if is_legend_node(node):
            reachable.add(name)

    # Also include any nodes that are explicitly present but had no edges (like tasks_info)
    for name in node_map.keys():
        if name not in reachable and name in seen_nodes and name not in adj and name not in rev:
            # ignore isolated nodes unless legend
            pass

    # Create new graph and copy attributes
    out = pydot.Dot(graph_type='digraph')
    # Copy some global attributes if present
    for k, v in (graph.get_attributes() or {}).items():
        out.set(k, v)

    # Add selected nodes preserving attributes
    for name in sorted(reachable):
        if name in node_map:
            # Add a copy of the original node
            out.add_node(node_map[name])
        else:
            out.add_node(pydot.Node(name))

    # Add edges where both endpoints are kept
    for edge in graph.get_edges():
        u = strip_quotes(edge.get_source())
        v = strip_quotes(edge.get_destination())
        if u in reachable and v in reachable:
            out.add_edge(edge)

    out_path = args.output or (args.input.rsplit('.', 1)[0] + '_unsafe_paths.dot')
    out.write_raw(out_path)
    print('Wrote filtered DOT to', out_path)


if __name__ == '__main__':
    main()
