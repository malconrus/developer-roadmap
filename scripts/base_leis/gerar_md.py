import sys, pathlib
base = pathlib.Path(__file__).parent
sys.path.insert(0, str(base / "ferramentas" / "lexbr" / "src"))
import re, lexbr
from lexbr.parser import _html_para_texto
executar = "--executar" in sys.argv
alvo = {"L14133.html": "Lei_14133_2021"}
for arq, nome in alvo.items():
    bruto = (base / "html" / arq).read_bytes().decode("cp1252")
    texto = _html_para_texto(re.sub(r"\s+", " ", bruto))
    lei = lexbr.ler_norma(texto, "Lei 14.133")
    trechos = list(lei.trechos(max_caracteres=1500))
    print(f"{lei.nome}: {len(trechos)} trechos")
    saida = base / "md" / nome
    for i, t in enumerate(trechos):
        if executar:
            saida.mkdir(parents=True, exist_ok=True)
            (saida / f"{i:04d}.md").write_text(f"{t.texto}\n\nFonte: {t.citacao}\n", encoding="utf-8")
    if not executar:
        print("SIMULAÇÃO. Primeiros:", [t.citacao for t in trechos[:3]])
