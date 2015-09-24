import sys
import math
import re
from xml.dom import minidom
from multiprocessing import Process, Queue

from graph import *
import shapely.ops
from shapely.geometry import LineString
import svg.path
import kdtree

try:
    import silhouette
    units = silhouette.units
except ImportError:
    msg = "Warning: no silhouette module available"
    print(msg)

units.define("pixel = inch / 72 = px")

def to_steps(thing):
    if type(thing) in (tuple, list) and len(thing) == 2 and type(thing[0]) in (int, float):
        (x, y) = thing
        x *= units["pixel"]
        y *= units["pixel"]
        # flip x
        x = (12 * units["inch"]) - x
        x = x.to("steps").magnitude
        y = y.to("steps").magnitude
        return (x, y)
    return map(to_steps, thing)

def draw_rect(cutter, **kw):
    x = float(kw["x"])
    y = float(kw["y"])
    width = float(kw["width"])
    height = float(kw["height"])
    move = (x, y)
    draw = [(x + width, y), (x + width, y + height), (x, y + height), (x, y)]
    cutter.position = to_steps(move)
    cutter.draw(to_steps(draw))

def walk_graph(graph, node):
    stack = [node]
    reverse = []
    path = [node]
    while stack:
        node = stack[-1]
        children = [nnode for nnode in graph[node] if not graph[node][nnode]["visited"]]
        if children:
            child = children[0]
            graph[node][child]["visited"] = True
            if reverse:
                path += reverse
                reverse = []
            path.append(child)
            stack.append(child)
            continue
        # no children
        stack.pop()
        if stack:
            reverse.append(stack[-1])
    return path

def build_path_commands(tree, graph):
    cursor = (0, 0)
    next_node = tree.search_nn(cursor)
    nodes = []
    culled = set()
    while next_node:
        (next_point, distance) = next_node
        next_point = next_point.data
        distance = math.sqrt(distance)
        tree = tree.remove(next_point)
        culled.add(next_point)
        if nodes and distance > 16:
            yield nodes
            nodes = []
        nodes += walk_graph(graph, next_point)
        for node in nodes:
            if node in culled:
                continue
            tree = tree.remove(node) or tree
            culled.add(node)
        next_node = tree.search_nn(nodes[-1])
    if nodes:
        yield nodes

def graph_lines(lines):
    graph = BidirectedGraph()
    if isinstance(lines, LineString):
        lines = [lines]
    for line in lines:
        last_coord = None
        for coord in line.coords:
            if coord not in graph:
                graph.add_node(coord)
            if last_coord:
                val = {"visited": False}
                graph.connect(coord, last_coord, val)
            last_coord = coord
    return graph

def simplify_path(path):
    lines = svg.path.parse_path(path)
    coords = [lines[0].start]
    for line in lines:
        if type(line) != svg.path.Line:
            raise NameError('The SVG file contains a path with crap: {}.'.format(type(line)))
        coords.append(line.end)
    coords = [(c.real, c.imag) for c in coords]
    lines = to_steps(coords)
    lines = [list(lines)]
    result = shapely.ops.linemerge(lines)
    print("building graph")
    graph = graph_lines(result)
    print("building kdtree")
    tree = kdtree.create(list(graph.keys()))
    return build_path_commands(tree, graph)

def produce_paths(svgfn, path_queue):
    fh = open(svgfn)
    doc = minidom.parse(fh)
    paths = doc.getElementsByTagName("path")
    for path in paths:
        points = path.getAttribute('d')
        paths = simplify_path(points)
        for path in paths:
            path_queue.put(path)
    rects = doc.getElementsByTagName("rect")
    for rect in rects:
        path_queue.put(dict(rect.attributes.items()))
    path_queue.put("done")

def draw_svg(worker, path_queue):
    cutter = connect()
    try:
        while 1:
            thing = path_queue.get()
            if thing == "done":
                break
            if type(thing) == dict:
                for rpt in range(3):
                    draw_rect(cutter, **thing)
            else:
                cutter.position = thing[0]
                cutter.draw(thing)
        worker.join()
    finally:
        cutter.home()

def connect():
    cutter = silhouette.Silhouette()
    cutter.connect()
    print("speed")
    cutter.speed = 8
    print("pressure")
    cutter.pressure = 4
    print("media")
    cutter.media = 113
    print("offset")
    cutter.offset = 0
    return cutter

if __name__ == "__main__":
    path_queue = Queue()
    svgfn = sys.argv[1]
    worker = Process(target=produce_paths, args=(svgfn, path_queue))
    worker.start()
    draw_svg(worker, path_queue)
