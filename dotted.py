# dotted.py

import os
import sys
import re
import math
import tkinter as tk
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from svgpathtools import Path

from svg_utils import normalize_glyph_path

# --- CONFIGURAÇÃO ---
TTF_PATH      = "Cursive-Regular.ttf"   # TTF com glifos cursivos
OUTPUT_DART   = "dotted.dart"           # Arquivo Dart a ser gerado
CANVAS_SIZE   = 600                     # Tamanho do Canvas no Tkinter (px)
MAX_SEGMENTS  = 5                       # Até 5 segmentos tracejados
MARKER_RADIUS = 12                      # Para dimensionar o tamanho da seta
TRACE_WIDTH   = 4                       # Espessura da linha tracejada

def make_arrow(p0, p1, length, angle_deg=30):
    """
    Dado o penúltimo ponto p0=(x0,y0) e o último p1=(x1,y1),
    cria dois subpaths "M … L p1" correspondentes às linhas de seta.
    length = comprimento da seta (no "glyph space").
    angle_deg = ângulo entre a reta e a seta (em graus).
    """
    x0, y0 = p0
    x1, y1 = p1
    θ = math.atan2(y1 - y0, x1 - x0)
    α = math.radians(angle_deg)

    # Pontos da base da seta, em coordenadas do “glyph”:
    lx = x1 - length * math.cos(θ - α)
    ly = y1 - length * math.sin(θ - α)
    rx = x1 - length * math.cos(θ + α)
    ry = y1 - length * math.sin(θ + α)

    sub1 = f"M {lx:.2f},{ly:.2f} L {x1:.2f},{y1:.2f}"
    sub2 = f"M {rx:.2f},{ry:.2f} L {x1:.2f},{y1:.2f}"
    return sub1, sub2

def build_trace_paths(segment, transform):
    """
    Converte um segmento (lista de pontos no Canvas) para coordenadas do "glyph space",
    gerando:
      - um caminho principal ("M … L …") que será interpretado como linha tracejada
      - dois subpaths de setas, apontando para o último ponto

    segment: [(x_canvas, y_canvas), ...]
    transform: (scale, tx, ty, offset) – mesma tupla retornada por normalize_glyph_path

    Retorna uma lista de strings, cada uma contendo um subpath SVG.
    """
    scale, tx, ty, offset = transform

    # Converte cada ponto do Canvas para “glyph coordinates normalizados”:
    pts_font = [
        ((x - offset - tx) / scale, (y - offset - ty) / scale)
        for x, y in segment
    ]

    elems = []
    if len(pts_font) >= 2:
        # 1) Path principal tracejado:
        d_main = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts_font)
        elems.append(d_main)

        # 2) Setas no final:
        p0, p1 = pts_font[-2], pts_font[-1]
        length_font = MARKER_RADIUS / scale * 0.8  # tamanho da seta no glyph space
        a1, a2 = make_arrow(p0, p1, length_font, angle_deg=25)
        elems.extend([a1, a2])

    return elems

def append_trace_to_dart(letter, all_elements):
    """
    Recebe a letra e a lista de elementos SVG (cada segmento tracejado + setas),
    monta a constante Dart:
      static const dottedLetterA = '''
      M … (linha tracejada segmento 1)
      M … (seta 1)
      M … (seta 2)
      M … (linha tracejada segmento 2)
      M … (seta 1)
      M … (seta 2)
      … 
      ''';
    Salva/atualiza no arquivo OUTPUT_DART.
    """
    const_name = f"dottedLetter{letter}"
    body = "\n".join(all_elements)
    block = f"static const {const_name} = '''\n{body}\n''';\n\n"

    header = ""
    if not os.path.exists(OUTPUT_DART):
        header = "// Gerado por dotted.py\n\n"

    existing = ""
    if os.path.exists(OUTPUT_DART):
        with open(OUTPUT_DART, "r", encoding="utf-8") as df:
            existing = df.read()
        # Remove bloco anterior, caso já exista
        existing = re.sub(
            rf"static const {const_name} = '''.*?''';\s*",
            "",
            existing,
            flags=re.S
        )

    with open(OUTPUT_DART, "w", encoding="utf-8") as df:
        df.write(header + existing + block)

    print(f"← {OUTPUT_DART} atualizado: {const_name}")


if __name__ == "__main__":
    # -------------------------- Checagem de argumentos ----------------------------
    if len(sys.argv) != 2:
        print(f"Uso: python {sys.argv[0]} <letra>")
        sys.exit(1)
    letter = sys.argv[1]
    if len(letter) != 1:
        print("Informe apenas uma letra, ex: python dotted.py A")
        sys.exit(1)

    # -------------------------- Carrega o glifo da letra --------------------------
    font = TTFont(TTF_PATH)
    glyphset = font.getGlyphSet()
    cmap = font.getBestCmap()
    glyph_name = cmap.get(ord(letter))
    if not glyph_name:
        print(f"Glifo não encontrado para '{letter}'.")
        sys.exit(1)

    # ---------------- Extrai SVG bruto do glifo e normaliza (flip + escala + centralização) -------------
    pen = SVGPathPen(glyphset)
    glyphset[glyph_name].draw(pen)
    raw_commands = pen.getCommands()

    normalized_path, scale, tx, ty = normalize_glyph_path(raw_commands, CANVAS_SIZE - 40)
    offset = 20  # Pequeno deslocamento para não colar no canto do Canvas
    transform = (scale, tx + offset, ty + offset, offset)

    # ------------------------- Gera pontos de contorno (preview) -----------------------------
    pts = []
    for sub in normalized_path.continuous_subpaths():
        for i in range(301):
            p = sub.point(i / 300)
            pts.append((p.real + offset, p.imag + offset))

    # ----------------------------- Interface Tkinter --------------------------------
    root = tk.Tk()
    root.title(f"Traçado livre: '{letter}'")
    canvas = tk.Canvas(root, width=CANVAS_SIZE, height=CANVAS_SIZE, bg="white")
    canvas.pack()

    # Desenha o contorno da letra (em preto) para referência do tracing
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        canvas.create_line(x1, y1, x2, y2, fill="black", width=2)

    # Cada segmento e o segmento em edição são armazenados nestas variáveis:
    segments = []  # lista de segmentos finalizados
    current = []   # segmento em edição (lista de pontos)

    def redraw():
        """
        Refaz tudo no Canvas:
          - segmentos finalizados (tracejado + seta)
          - segmento em edição (tracejado + seta)
          - marcadores (círculos azuis com número) para cada ponto do segmento em edição
        """
        canvas.delete("mark", "path")

        # 1) Desenha todos os segmentos completados
        for seg in segments:
            coords = [c for pt in seg for c in pt]
            canvas.create_line(
                *coords,
                dash=(8, 4),             # traço tracejado (8px on, 4px off)
                arrow=tk.LAST,           # seta no fim do segmento
                arrowshape=(16, 20, 6),  # tamanho da seta (comprimento, largura, base)
                width=TRACE_WIDTH,
                tags="path"
            )

        # 2) Desenha o segmento em edição (se houver ≥ 2 pontos)
        if len(current) > 1:
            coords = [c for pt in current for c in pt]
            canvas.create_line(
                *coords,
                dash=(8, 4),
                arrow=tk.LAST,
                arrowshape=(16, 20, 6),
                width=TRACE_WIDTH,
                tags="path"
            )

        # 3) Desenha marcadores numerados de cada ponto no segmento atual
        for idx, (x, y) in enumerate(current, start=1):
            # Círculo outline em azul
            canvas.create_oval(
                x - MARKER_RADIUS, y - MARKER_RADIUS,
                x + MARKER_RADIUS, y + MARKER_RADIUS,
                outline="blue", width=2, tags="mark"
            )
            # Texto do índice dentro do círculo (apenas referência visual)
            canvas.create_text(
                x, y, text=str(idx),
                fill="blue",
                font=("Arial", int(MARKER_RADIUS * 1.2)),
                tags="mark"
            )

    def on_click(evt):
        """
        Ao clicar com o mouse, adiciona as coordenadas (evt.x, evt.y) ao segmento atual,
        desde que o número de segmentos finalizados seja menor que MAX_SEGMENTS.
        """
        if len(segments) < MAX_SEGMENTS:
            current.append((evt.x, evt.y))
            redraw()

    def on_key(evt):
        """
        Captura teclas:
          - 'u': desfaz o último ponto de 'current'. Se 'current' estiver vazio,
                 remove o último segmento de 'segments'.
          - 't': termina o segmento atual (adiciona 'current' a 'segments') se tiver ao menos 2 pontos,
                 então reinicia 'current' para começar novo segmento.
          - 's': gera os SVG paths chamando build_trace_paths(...) para cada segmento em 'segments',
                 chama append_trace_to_dart(...) para salvar em dotted.dart e fecha a janela.
        """
        global current, segments  # <- voilà: declara como global para poder reatribuir current = [] ou segments.pop()

        # 'u' -> desfaz ponto atual ou remove último segmento
        if evt.char == "u":
            if current:
                current.pop()
            elif segments:
                segments.pop()
            redraw()

        # 't' -> termina o segmento atual (se tiver ≥ 2 pontos) e começa um novo
        elif evt.char == "t":
            if len(current) >= 2 and len(segments) < MAX_SEGMENTS:
                segments.append(current.copy())
                current = []  # reinicia para próximo segmento
                redraw()

        # 's' -> salva em dotted.dart e fecha
        elif evt.char == "s":
            all_elems = []
            for seg in segments:
                all_elems.extend(build_trace_paths(seg, transform))
            append_trace_to_dart(letter, all_elems)
            root.destroy()

    # Liga os eventos de clique e teclas
    canvas.bind("<Button-1>", on_click)    # clique com mouse
    root.bind("<Key>", on_key)             # teclas gerais

    print("Clique para adicionar pontos; 't' finaliza um segmento; 'u' desfaz; 's' salva em dotted.dart")
    root.mainloop()
