#!/usr/bin/env python3
"""
Script para gerar SVG paths de letras (shape, index e dotted) e JSON de pontos normalizados
para uso em Flutter/Dart.

INDEX: marcadores numerados (círculos com dígitos) no início de cada traço,
indicando a ordem de levantamento/baixa de caneta.
DOTTED: flechas ao longo de cada traço, mostrando direção do traçado.
"""
import os
import json
import uuid
import math
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from svgpathtools import parse_path, Path

# --- CONFIGURAÇÃO ---
TTF_PATH            = "Cursive-Regular.ttf"
OUTPUT_DART         = "shapes_svg.dart"
OUTPUT_JSON_DIR     = "assets"
SCALE               = 100.0
EXCLUDE             = set("KYWkyw")
POINTS_PER_STROKE   = 12
DIGIT_MARKER_RADIUS = 8.0
DIGIT_MARKER_SCALE  = 0.15
LETTERS             = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
                       if c not in EXCLUDE]

# --- AUXILIARES ---
def get_global_bbox(path: Path):
    xs, ys = [], []
    for seg in path:
        for pt in seg.bpoints():
            xs.append(pt.real); ys.append(pt.imag)
    return min(xs), max(xs), min(ys), max(ys)

def arrow_at(p: complex, angle: float, size=6) -> str:
    base = [complex(0, 0), complex(-size, size/2), complex(-size, -size/2)]
    rot = lambda z: complex(
        z.real * math.cos(angle) - z.imag * math.sin(angle),
        z.real * math.sin(angle) + z.imag * math.cos(angle)
    )
    pts = [rot(pt) + p for pt in base]
    return f"M {pts[0].real:.2f},{pts[0].imag:.2f} L {pts[1].real:.2f},{pts[1].imag:.2f} L {pts[2].real:.2f},{pts[2].imag:.2f} Z"

# --- DIGIT PATH ---
def digit_path(digit: str, font, glyphset, scale: float) -> Path:
    cmap = font.getBestCmap()
    glyph_name = cmap.get(ord(digit))
    if not glyph_name:
        raise ValueError(f"Glifo não encontrado para dígito '{digit}'")
    pen = SVGPathPen(glyphset)
    glyphset[glyph_name].draw(pen)
    raw = pen.getCommands()
    p = parse_path(raw)
    xs = [pt.real for seg in p for pt in seg.bpoints()]
    ys = [pt.imag for seg in p for pt in seg.bpoints()]
    cx, cy = (max(xs)+min(xs))/2, (max(ys)+min(ys))/2
    p0 = p.translated(complex(-cx, -cy))
    scaled = [seg.scaled(scale) for seg in p0]
    return Path(*scaled)



# --- MAIN ---
if __name__ == "__main__":
    os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)
    dart_f = open(OUTPUT_DART, "w", encoding="utf-8")
    dart_f.write("class CursiveSvgs {\n")

    font     = TTFont(TTF_PATH)
    glyphset = font.getGlyphSet()

    for char in LETTERS:
        cmap = font.getBestCmap()
        glyph_name = cmap.get(ord(char))
        if not glyph_name:
            print(f"[WARN] glifo não encontrado para '{char}', pulando.")
            continue
        # extrai e parseia shape SVG
        pen = SVGPathPen(glyphset)
        glyphset[glyph_name].draw(pen)
        raw = pen.getCommands()
        original = parse_path(raw)
        # inverter vertical e ajustar base
        x_min, x_max, y_min, y_max = get_global_bbox(original)
        path = original.scaled(1, -1).translated(complex(0, y_min + y_max))

        # gerar SVGs e JSONs
        shape_svg  = path.d()


        dart_f.write(f"  static const shapeLetter{char}       = '''{shape_svg}''';\n")


        strokes = []
        for sub in path.continuous_subpaths():
            pts = [f"{sub.point(k/(POINTS_PER_STROKE-1)).real/SCALE:.4f},{sub.point(k/(POINTS_PER_STROKE-1)).imag/SCALE:.4f}"
                   for k in range(POINTS_PER_STROKE)]
            strokes.append({"points": pts})

        info = {"id": str(uuid.uuid4()), "style": "default", "char": char, "strokes": strokes}
        with open(os.path.join(OUTPUT_JSON_DIR, f"{char}_PointsInfo.json"),
                  "w", encoding="utf-8") as jf:
            json.dump(info, jf, indent=2, ensure_ascii=False)

    dart_f.write("}\n")
    dart_f.close()
    print(f"✅ Gerado {OUTPUT_DART} e JSONs em {OUTPUT_JSON_DIR}/")
