# json_generator.py

"""
Script para gerar SOMENTE os arquivos JSON de pontos normalizados, um por letra.
Não altera nenhum arquivo Dart. Usa a mesma lógica de normalização (flip+escala+centralização)
do utils.py, mas, desta vez, também inverte o eixo Y para ficar compatível com o shape invertido
que será desenhado no Flutter (shape.py já aplica flip vertical).

Saídas:
  - Para cada letra em LETTERS, um arquivo JSON chamado "<letra>_PointsInfo.json"
    na pasta OUTPUT_JSON_DIR, com pontos normalizados para cada stroke contínuo.
    **OBS¹**: Note que fazemos Y_final = 1 - (y_original/SCALE) para “flipar” verticalmente.
    **OBS²**: SCALE deve ser igual ao usado no shape.py (600).
"""

import os
import json
import uuid
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

from utils import normalize_glyph_path

# --- CONFIGURAÇÃO ---
TTF_PATH          = "Cursive-Regular.ttf"    # Mesmo .ttf usado em shape.py
OUTPUT_JSON_DIR   = "assets"                 # Pasta onde cada "<letra>_PointsInfo.json" será salvo
SCALE             = 600.0                    # Igual ao SCALE de shape.py
EXCLUDE           = set("KYWkyw")            # Mesmos caracteres que shape.py pula
POINTS_PER_STROKE = 12                       # Quantos pontos amostrar por stroke
LETTERS           = [
    c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if c not in EXCLUDE
]

def main():
    # 1) Cria a pasta de saída, se não existir
    os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)

    # 2) Carrega a fonte e obtém o mapping Unicode→glifo
    font     = TTFont(TTF_PATH)
    glyphset = font.getGlyphSet()
    cmap     = font.getBestCmap()

    # 3) Para cada letra, extrai e normaliza, depois gera JSON
    for char in LETTERS:
        glyph_name = cmap.get(ord(char))
        if not glyph_name:
            print(f"[WARN] Glifo não encontrado para '{char}', pulando JSON.")
            continue

        # 3.1) Extrai o comando SVG bruto do glifo
        pen = SVGPathPen(glyphset)
        glyphset[glyph_name].draw(pen)
        raw_commands = pen.getCommands()

        # 3.2) Normaliza: flip vertical + centralização + escala
        normalized_path, scale, tx, ty = normalize_glyph_path(raw_commands, SCALE)

        # 3.3) Para cada stroke (_subpath_), amostra POINTS_PER_STROKE pontos
        strokes = []
        for subpath in normalized_path.continuous_subpaths():
            pts = []
            for k in range(POINTS_PER_STROKE):
                t = k / (POINTS_PER_STROKE - 1)
                p = subpath.point(t)
                # ────────────────────────────────────────────────────────────────────
                # Aqui fazemos o “flip vertical” ao nível do JSON:
                x_norm = p.real / SCALE
                y_norm = 1.0 - (p.imag / SCALE)
                pts.append(f"{x_norm:.4f},{y_norm:.4f}")
            strokes.append({"points": pts})

        # 3.4) Monta o dicionário e salva no arquivo JSON
        info = {
            "id": str(uuid.uuid4()),
            "style": "default",
            "char": char,
            "strokes": strokes
        }
        json_filename = os.path.join(OUTPUT_JSON_DIR, f"{char}_PointsInfo.json")
        with open(json_filename, "w", encoding="utf-8") as jf:
            json.dump(info, jf, indent=2, ensure_ascii=False)

        print(f"Gerado JSON: {json_filename}")

    print(f"✅ Todos os JSONs foram gerados em: {OUTPUT_JSON_DIR}/")


if __name__ == "__main__":
    main()
