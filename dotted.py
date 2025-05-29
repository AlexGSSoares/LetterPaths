#!/usr/bin/env python3
"""
Ferramenta interativa para marcar até 5 segmentos de traçado em letras cursivas e
exportar para "dotted.dart" constantes traceLetterX contendo apenas paths:

static const traceLetterA = '''
M x1,y1 L x2,y2 …        (linha tracejada)
M xA1,yA1 L x_end,y_end  (seta #1)
M xA2,yA2 L x_end,y_end  (seta #2)
…                        (até 5 segmentos)
''';
"""
import os
import sys
import re
import math
import tkinter as tk
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from svgpathtools import parse_path

# --- CONFIGURAÇÃO ---
TTF_PATH      = "Cursive-Regular.ttf"
OUTPUT_DART   = "dotted.dart"
CANVAS_SIZE   = 600      # px
MAX_SEGMENTS  = 5
DASH_PATTERN  = (8, 4)   # preview: traço, espaço (px)
ARROW_SHAPE   = (16,20,6)# preview: comprimento, largura, base da seta (px)
MARKER_RADIUS = 12       # px (para escalar a seta)
TRACE_WIDTH   = 4        # px de grossura do tracejado

# --- AUXILIARES ---
def get_svg_path_for_char(char):
    font     = TTFont(TTF_PATH)
    glyphset = font.getGlyphSet()
    cmap     = font.getBestCmap()
    name     = cmap.get(ord(char))
    if not name:
        raise ValueError(f"Glifo não encontrado para '{char}'")
    pen = SVGPathPen(glyphset)
    glyphset[name].draw(pen)
    return parse_path(pen.getCommands())

def make_arrow(p0, p1, length=5, angle_deg=30):
    x0, y0 = p0; x1, y1 = p1
    θ = math.atan2(y1 - y0, x1 - x0)
    α = math.radians(angle_deg)
    lx = x1 - length * math.cos(θ - α)
    ly = y1 - length * math.sin(θ - α)
    rx = x1 - length * math.cos(θ + α)
    ry = y1 - length * math.sin(θ + α)
    sub1 = f"M {lx:.2f},{ly:.2f} L {x1:.2f},{y1:.2f}"
    sub2 = f"M {rx:.2f},{ry:.2f} L {x1:.2f},{y1:.2f}"
    return sub1, sub2

def build_trace_paths(segment, transform):
    scale, offx, offy = transform
    # converte coords do canvas (Y p/ baixo) → coords da fonte (Y p/ cima)
    pts = [((x - offx) / scale, (y - offy) / scale) for x,y in segment]
    # 1) path principal
    d_main = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x,y in pts)
    elems = [d_main]
    # 2) setas no fim
    if len(pts) >= 2:
        p0, p1 = pts[-2], pts[-1]
        length = MARKER_RADIUS / scale * 0.8
        a1, a2 = make_arrow(p0, p1, length=length, angle_deg=25)
        elems.extend([a1, a2])
    return elems

def append_trace_to_dart(letter, all_elements):
    const_name = f"traceLetter{letter}"
    body = "\n".join(all_elements)
    block = f"static const {const_name} = '''\n{body}\n''';\n\n"

    header = "// Gerado por trace_marker.py\n\n" if not os.path.exists(OUTPUT_DART) else ""
    existing = ""
    if os.path.exists(OUTPUT_DART):
        with open(OUTPUT_DART, "r", encoding="utf-8") as df:
            existing = df.read()
        existing = re.sub(
            rf"static const {const_name} = '''.*?''';\s*", "",
            existing, flags=re.S
        )
    with open(OUTPUT_DART, "w", encoding="utf-8") as df:
        df.write(header + existing + block)
    print(f"← {OUTPUT_DART} atualizado: {const_name}")

# --- MAIN ---
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <letra>")
        sys.exit(1)
    letter = sys.argv[1]

    try:
        path = get_svg_path_for_char(letter)
    except ValueError as e:
        print(e)
        sys.exit(1)

    # amostragem e normalização para o canvas
    pts = []
    for sub in path.continuous_subpaths():
        for i in range(301):
            p = sub.point(i/300)
            pts.append((p.real, p.imag))
    xs, ys = zip(*pts)
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w, h = maxx-minx, maxy-miny
    scale = min((CANVAS_SIZE-40)/w, (CANVAS_SIZE-40)/h)
    offx  = (CANVAS_SIZE - w*scale)/2  - minx*scale
    offy  = (CANVAS_SIZE - h*scale)/2 + maxy*scale
    pts_norm = [(x*scale+offx, -y*scale+offy) for x,y in pts]

    # UI Tkinter
    root = tk.Tk()
    root.title(f"Traçado livre: '{letter}'")
    canvas = tk.Canvas(root, width=CANVAS_SIZE, height=CANVAS_SIZE, bg="white")
    canvas.pack()

    # desenha contorno da letra
    for (x1,y1),(x2,y2) in zip(pts_norm, pts_norm[1:]):
        canvas.create_line(x1, y1, x2, y2, fill="black", width=2)

    segments = []   # lista de segmentos completos
    current = []    # segmento em edição

    def redraw():
        canvas.delete("mark", "path")
        # desenha segmentos finalizados
        for seg in segments:
            coords = [c for pt in seg for c in pt]
            canvas.create_line(
                *coords,
                dash=DASH_PATTERN,
                arrow=tk.LAST,
                arrowshape=ARROW_SHAPE,
                width=TRACE_WIDTH,
                tags="path"
            )
        # desenha segmento em edição
        if len(current) > 1:
            coords = [c for pt in current for c in pt]
            canvas.create_line(
                *coords,
                dash=DASH_PATTERN,
                arrow=tk.LAST,
                arrowshape=ARROW_SHAPE,
                width=TRACE_WIDTH,
                tags="path"
            )
        # marcadores do segmento em edição
        for idx,(x,y) in enumerate(current, start=1):
            canvas.create_oval(
                x-MARKER_RADIUS, y-MARKER_RADIUS,
                x+MARKER_RADIUS, y+MARKER_RADIUS,
                outline="blue", width=2, tags="mark"
            )
            canvas.create_text(
                x, y, text=str(idx),
                fill="blue", font=("Arial", int(MARKER_RADIUS*1.2)),
                tags="mark"
            )

    def on_click(evt):
        if len(segments) < MAX_SEGMENTS:
            current.append((evt.x, evt.y))
            redraw()

    def on_key(evt):
        global current
        if evt.char == "u":
            if current:
                current.pop()
            elif segments:
                segments.pop()
            redraw()
        elif evt.char == "t":
            if len(current) >= 2 and len(segments) < MAX_SEGMENTS:
                segments.append(current.copy())
                current = []
                redraw()
        elif evt.char == "s":
            all_elems = []
            for seg in segments:
                all_elems.extend(build_trace_paths(seg, (scale, offx, offy)))
            append_trace_to_dart(letter, all_elems)
            root.destroy()

    canvas.bind("<Button-1>", on_click)
    root.bind("<Key>", on_key)

    print("Clique para adicionar pontos; 't' finaliza um segmento; 'u' desfaz; 's' salva em dotted.dart")
    root.mainloop()
