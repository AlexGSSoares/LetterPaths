#!/usr/bin/env python3
"""
Ferramenta interativa para marcar até 5 índices de traçamento em letras cursivas e
atualizar um arquivo Dart com constantes indexLetterX contendo apenas paths:
"""
import os
import sys
import re
import tkinter as tk
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from svgpathtools import parse_path, Path

# --- CONFIGURAÇÃO ---
TTF_PATH           = "Cursive-Regular.ttf"
OUTPUT_DART        = "index_svg.dart"
CANVAS_SIZE        = 600   # px
MAX_MARKERS        = 5
MARKER_RADIUS      = 12    # px no canvas
DIGIT_INSIDE_SCALE = 0.6   # escala do número dentro do círculo (0.0–1.0)

# --- AUXILIARES ---
def get_svg_path_for_char(char):
    font = TTFont(TTF_PATH)
    glyphset = font.getGlyphSet()
    cmap = font.getBestCmap()
    name = cmap.get(ord(char))
    if not name:
        raise ValueError(f"Glifo não encontrado para '{char}'")
    pen = SVGPathPen(glyphset)
    glyphset[name].draw(pen)
    path = parse_path(pen.getCommands())
    return path, font, glyphset

def build_marker_paths(markers, transform, font, glyphset):
    """
    Gera os d-strings de cada marcador + dígito,
    corrigindo orientação do número para SVG (Y positivo para baixo).
    """
    scale, offx, offy = transform
    elems = []

    for idx, (x_c, y_c) in enumerate(markers, start=1):
        # Converte da coordenada do canvas (Y para baixo) para coordenada da fonte:
        cx = (x_c - offx) / scale
        cy = (y_c - offy) / scale
        r  = MARKER_RADIUS / scale

        # 1) desenha o círculo como duas arcs
        circle_d = (
            f"M {cx + r:.2f},{cy:.2f} "
            f"A {r:.2f},{r:.2f} 0 1,0 {cx - r:.2f},{cy:.2f} "
            f"A {r:.2f},{r:.2f} 0 1,0 {cx + r:.2f},{cy:.2f} Z"
        )
        elems.append(circle_d)

        # 2) desenha o dígito dentro do círculo
        digit = str(idx)
        pen = SVGPathPen(glyphset)
        cmap = font.getBestCmap()
        glyph_name = cmap.get(ord(digit))
        glyphset[glyph_name].draw(pen)
        glyph_path = parse_path(pen.getCommands())

        # escala uniforme e espelha no eixo Y (para corrigir orientação)
        ys = [pt.imag for seg in glyph_path for pt in seg.bpoints()]
        h_glyph = max(ys) - min(ys)
        desired_h = 2 * r * DIGIT_INSIDE_SCALE
        s = desired_h / h_glyph
        # aqui: seg.scaled(s, -s) -> x * s, y * -s
        glyph_scaled = Path(*(seg.scaled(s, -s) for seg in glyph_path))

        # centraliza em (0,0)
        xs = [pt.real for seg in glyph_scaled for pt in seg.bpoints()]
        ys = [pt.imag for seg in glyph_scaled for pt in seg.bpoints()]
        cx_g = (max(xs) + min(xs)) / 2
        cy_g = (max(ys) + min(ys)) / 2
        glyph_centered = glyph_scaled.translated(complex(-cx_g, -cy_g))

        # move para (cx, cy)
        glyph_at_pos = glyph_centered.translated(complex(cx, cy))
        elems.append(glyph_at_pos.d())

    return elems

def append_to_dart(letter, elements):
    const_name = f"indexLetter{letter}"
    body = "\n".join(elements)
    block = (
        f"static const {const_name} = '''\n"
        f"{body}\n"
        f"''';\n\n"
    )

    header = ""
    if not os.path.exists(OUTPUT_DART):
        header = "// Gerado por index_marker.py\n\n"

    existing = ""
    if os.path.exists(OUTPUT_DART):
        with open(OUTPUT_DART, "r", encoding="utf-8") as df:
            existing = df.read()
        pat = re.compile(rf"static const {const_name} = '''.*?''';\s*", re.S)
        existing = re.sub(pat, "", existing)

    with open(OUTPUT_DART, "w", encoding="utf-8") as df:
        df.write(header + existing + block)
    print(f"← index.dart atualizado: {const_name}")

# --- MAIN ---
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <letra>")
        sys.exit(1)
    letter = sys.argv[1]

    try:
        path, font, glyphset = get_svg_path_for_char(letter)
    except ValueError as e:
        print(e)
        sys.exit(1)

    # amostragem e normalização para desenho no canvas
    pts = []
    for sub in path.continuous_subpaths():
        for i in range(301):
            p = sub.point(i / 300)
            pts.append((p.real, p.imag))
    xs, ys = zip(*pts)
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w, h = maxx - minx, maxy - miny
    scale = min((CANVAS_SIZE - 40) / w, (CANVAS_SIZE - 40) / h)
    offx  = (CANVAS_SIZE - w * scale) / 2  - minx * scale
    offy  = (CANVAS_SIZE - h * scale) / 2 + maxy * scale
    pts_norm = [(x * scale + offx, -y * scale + offy) for x, y in pts]

    # UI Tkinter
    root = tk.Tk()
    root.title(f"Marcar índices: '{letter}'")
    canvas = tk.Canvas(root, width=CANVAS_SIZE, height=CANVAS_SIZE, bg="white")
    canvas.pack()
    for (x1, y1), (x2, y2) in zip(pts_norm, pts_norm[1:]):
        canvas.create_line(x1, y1, x2, y2, fill="black", width=2)

    markers = []
    def redraw():
        canvas.delete("mark")
        for idx, (x, y) in enumerate(markers, start=1):
            canvas.create_oval(
                x - MARKER_RADIUS, y - MARKER_RADIUS,
                x + MARKER_RADIUS, y + MARKER_RADIUS,
                outline="blue", width=2, tags="mark"
            )
            canvas.create_text(
                x, y, text=str(idx),
                fill="blue", font=("Arial", int(MARKER_RADIUS * 1.2)),
                tags="mark"
            )

    def on_click(evt):
        if len(markers) < MAX_MARKERS:
            markers.append((evt.x, evt.y))
            redraw()

    def on_key(evt):
        if evt.char == "u" and markers:
            markers.pop()
            redraw()
        elif evt.char == "s":
            elems = build_marker_paths(markers, (scale, offx, offy), font, glyphset)
            append_to_dart(letter, elems)
            root.destroy()

    canvas.bind("<Button-1>", on_click)
    root.bind("<Key>", on_key)

    print(f"Clique até {MAX_MARKERS} pontos. 'u' desfaz, 's' salva e atualiza Dart.")
    root.mainloop()
