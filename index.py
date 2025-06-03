# index.py

import os
import sys
import re
import tkinter as tk
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from svgpathtools import Path, parse_path

from svg_utils import normalize_glyph_path

# --- CONFIGURAÇÃO ---
TTF_PATH           = "Cursive-Regular.ttf"   # Caminho para o TTF com letra cursiva
OUTPUT_DART        = "index_svg.dart"        # Arquivo Dart que será gerado
CANVAS_SIZE        = 600                     # Tamanho do Canvas do Tkinter (pixels)
MAX_MARKERS        = 5                       # Até 5 índices por letra
MARKER_RADIUS      = 12                      # Raio, em px, dos círculos de índice no Canvas
DIGIT_INSIDE_SCALE = 0.6                     # Fração do círculo que o digit ocupa (0.0–1.0)

def build_marker_paths(markers, transform, font, glyphset):
    """
    Gera os caminhos SVG (strings 'd="..."') para cada marcador:
      - um círculo preenchido
      - o dígito recortado dentro do círculo (em “negative space”)

    markers: lista de tuplas [(x_canvas, y_canvas), ...] no espaço do Canvas Tkinter
    transform: (scale, tx, ty, offset), onde:
        - scale, tx, ty vêm diretamente de normalize_glyph_path(letra, CANVAS_SIZE-40)
        - offset é um deslocamento fixo de 20 pixels para não colar na borda
    font, glyphset: servem para extrair o glifo do dígito e gerar seu SVG path

    Retorna: lista de strings (cada string é um sub-path SVG, sem cabeçalho),
    na ordem “círculo preenchido” (com fill color) e “dígito recortado” (com
    fill da cor de fundo), para cada índice.
    """
    scale, tx, ty, offset = transform
    elems = []

    # Vamos assumir que o fundo (onde vamos “recortar” o dígito) é branco.
    # Assim, desenharemos:
    #   1) o círculo com fill="#000000" (ou outra cor a ser definida no Dart),
    #   2) o dígito no mesmo local, com fill="#FFFFFF", de modo a parecer recortado.
    #
    # No Flutter, você usará indexPathPaintStyle = PaintingStyle.fill e indexColor = ...
    # para o círculo, e precisará desenhar o dígito com mesma lógica mas invertendo a cor.

    for idx, (x_c, y_c) in enumerate(markers, start=1):
        # 1) Converte (x_canvas, y_canvas) → (x0, y0) no “glyph space” normalizado
        x0 = (x_c - offset - tx) / scale
        y0 = (y_c - offset - ty) / scale

        # 2) Raio, em coordenadas do glyph normalizado
        r_font = MARKER_RADIUS / scale

        # 3) Cria o “círculo preenchido” como dois arcos (formando um círculo)
        #    Esse círculo deve ser desenhado com fill, depois recortaremos o dígito.
        circle_d = (
            f"M {x0 + r_font:.3f},{y0:.3f} "
            f"A {r_font:.3f},{r_font:.3f} 0 1,0 {x0 - r_font:.3f},{y0:.3f} "
            f"A {r_font:.3f},{r_font:.3f} 0 1,0 {x0 + r_font:.3f},{y0:.3f} Z"
        )
        elems.append(circle_d)

        # 4) Agora desenha o dígito (ex: "1", "2", …) para recorte
        digit = str(idx)
        cmap = font.getBestCmap()
        glyph_name_digit = cmap.get(ord(digit))
        if not glyph_name_digit:
            # Se por algum motivo não existir o glifo do dígito, pula
            continue

        # 4.1) Extrai SVG bruto do glifo do dígito
        pen = SVGPathPen(glyphset)
        glyphset[glyph_name_digit].draw(pen)
        raw_digit = pen.getCommands()

        # 4.2) Normaliza o glifo do dígito para caber em um quadrado de lado
        #      (2 * r_font * DIGIT_INSIDE_SCALE)
        #      O resultado vem com centro em (target/2, target/2).
        target_size = 2 * r_font * DIGIT_INSIDE_SCALE
        dpath, dscale, dtx, dty = normalize_glyph_path(raw_digit, target_size)

        # 4.3) Para que o centro do dígito (que está em target/2,target/2) vá para (x0, y0),
        #      precisamos translá-lo por:
        #         (x0 - target/2, y0 - target/2)
        dx = x0 - (target_size / 2)
        dy = y0 - (target_size / 2)
        dpath_translated = Path(*(seg.translated(complex(dx, dy)) for seg in dpath))

        # 4.4) Adiciona o comando SVG do dígito (fill branco na hora do Dart) para “recortar”
        elems.append(dpath_translated.d())

    return elems


def append_to_dart(letter, elements):
    """
    Gera ou atualiza o bloco Dart para `indexLetter<letter>`, contendo:
      - primeiro o(s) círculo(s) preenchido(s) (em preto, por exemplo)
      - depois o(s) caminho(s) do dígito(s) (em branco), de modo a recortar

    A saída no Dart ficará assim:

      static const indexLetterA = '''
        M x1,y1 A ... Z   (círculo)
        M x2,y2 L ...     (dígito, que será pintado com cor de fundo)
        M ...             (próximo círculo)
        M ...             (próximo dígito)
      ''';

    Chamaremos indexPathPaintStyle = PaintingStyle.fill e
    indexColor = Colors.black para o círculo, e no número usaremos
    dottedColor = Colors.white (ou whatever seja a cor de fundo).
    """
    const_name = f"indexLetter{letter}"
    # Junta cada subpath em uma linha separada
    body = "\n".join(elements)
    block = (
        f"static const {const_name} = '''\n"
        f"{body}\n"
        f"''';\n\n"
    )

    header = ""
    if not os.path.exists(OUTPUT_DART):
        header = "// Gerado por index.py\n\n"

    existing = ""
    if os.path.exists(OUTPUT_DART):
        with open(OUTPUT_DART, "r", encoding="utf-8") as df:
            existing = df.read()
        # Remove bloco anterior, caso exista
        pat = re.compile(rf"static const {const_name} = '''.*?''';\s*", re.S)
        existing = re.sub(pat, "", existing)

    with open(OUTPUT_DART, "w", encoding="utf-8") as df:
        df.write(header + existing + block)

    print(f"← {OUTPUT_DART} atualizado: {const_name}")


if __name__ == "__main__":
    # --- Checagem de argumentos ---
    if len(sys.argv) != 2:
        print(f"Uso: python {sys.argv[0]} <letra>  (ex: python index.py A)")
        sys.exit(1)

    letter = sys.argv[1]
    if len(letter) != 1:
        print("Informe apenas uma única letra (ex: A).")
        sys.exit(1)

    # --- Carrega fonte e glifos ---
    font = TTFont(TTF_PATH)
    glyphset = font.getGlyphSet()
    cmap = font.getBestCmap()
    glyph_name = cmap.get(ord(letter))
    if not glyph_name:
        print(f"Glifo não encontrado para '{letter}'.")
        sys.exit(1)

    # --- Extrai SVG bruto da letra e normaliza (flip + escala + centralização) ---
    pen = SVGPathPen(glyphset)
    glyphset[glyph_name].draw(pen)
    raw_commands = pen.getCommands()

    normalized_path, scale, tx, ty = normalize_glyph_path(raw_commands, CANVAS_SIZE - 40)
    offset = 20  # Pequeno deslocamento para não colar no canto do Canvas
    transform = (scale, tx + offset, ty + offset, offset)

    # --- Gera pontos de contorno (preview) ---
    pts = []
    for sub in normalized_path.continuous_subpaths():
        for i in range(301):
            p = sub.point(i / 300)
            pts.append((p.real + offset, p.imag + offset))

    # --- Interface Tkinter ---
    root = tk.Tk()
    root.title(f"Marcar índices para '{letter}'")
    canvas = tk.Canvas(root, width=CANVAS_SIZE, height=CANVAS_SIZE, bg="white")
    canvas.pack()

    # Desenha o contorno da letra (em preto)
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        canvas.create_line(x1, y1, x2, y2, fill="black", width=2)

    markers = []

    def redraw_preview():
        """
        Refaz a pré-visualização:
          - Desenha círculos vazados (outline azul) para cada marcador
          - Desenha o número posicionado approximadamente (provisório), MAS
            a exportação real virá de build_marker_paths.
        """
        canvas.delete("mark")
        for idx, (x, y) in enumerate(markers, start=1):
            # Círculo outline (apenas para você ver onde clicou)
            canvas.create_oval(
                x - MARKER_RADIUS, y - MARKER_RADIUS,
                x + MARKER_RADIUS, y + MARKER_RADIUS,
                outline="blue", width=2, tags="mark"
            )
            # Número provisório: apenas para referência visual
            canvas.create_text(
                x, y, text=str(idx),
                fill="blue", font=("Arial", int(MARKER_RADIUS * 1.2)),
                tags="mark"
            )

    def on_click(evt):
        if len(markers) < MAX_MARKERS:
            markers.append((evt.x, evt.y))
            redraw_preview()

    def on_key(evt):
        # 'u' → desfaz o último círculo numerado
        if evt.char == "u" and markers:
            markers.pop()
            redraw_preview()
        # 's' → salva no Dart (“exportar os SVG paths”) e fecha
        elif evt.char == "s":
            elems = build_marker_paths(markers, transform, font, glyphset)
            append_to_dart(letter, elems)
            root.destroy()

    canvas.bind("<Button-1>", on_click)
    root.bind("<Key>", on_key)

    print(f"Clique até {MAX_MARKERS} pontos (círculos). Tecle 'u' para desfazer. Tecle 's' para salvar.")
    root.mainloop()
