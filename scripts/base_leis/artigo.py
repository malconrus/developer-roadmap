"""Consulta direta por artigo, sem IA. Exemplos:
  python artigo.py cf 5
  python artigo.py cf 5 II            (só o inciso II do art. 5º)
  python artigo.py cf 103-B
  python artigo.py cf adct 97
  python artigo.py cdc 26
  python artigo.py lei 28             (Lei 14.133)
"""
import sys, re, pathlib

sys.stdout.reconfigure(encoding="utf-8")
BASE = pathlib.Path(__file__).parent / "md"


def limpar(txt):
    if txt.startswith("---"):
        txt = txt.split("---", 2)[2]
    return re.sub(r'<a id="[^"]*"></a>', "", txt).strip()


def arquivos_md(pasta, prefixo, num):
    nome = re.sub(r"[^0-9a-z]+", "-", num.lower())
    m = re.match(r"(\d+)(.*)", nome)
    nome = m.group(1).zfill(3) + m.group(2)
    p = BASE / pasta / f"{prefixo}-{nome}.md"
    return [p] if p.exists() else []


def inciso(txt, romano):
    secoes = re.split(r"(?m)(?=^## )", txt)
    alvo = [s for s in secoes if re.match(rf"## Inciso {romano}\b", s.strip(), re.I)]
    return "\n".join(alvo).strip() or None


def main():
    a = [x.lower() for x in sys.argv[1:]]
    if len(a) < 2:
        print(__doc__)
        return
    lei = a[0]
    resto = a[1:]
    romano = None
    if len(resto) >= 2 and re.fullmatch(r"[ivxlc]+", resto[-1]):
        romano = resto.pop().upper()
    if lei == "cf":
        adct = resto[0] == "adct"
        num = resto[-1]
        achados = arquivos_md("CF_1988", "adct-art" if adct else "art", num)
        nome = "Constituição Federal de 1988"
    elif lei == "cdc":
        num = resto[-1]
        achados = arquivos_md("CDC_8078_1990", "art", num)
        nome = "Código de Defesa do Consumidor (Lei nº 8.078/1990)"
    elif lei == "cp":
        num = resto[-1].upper()
        achados = []
        for p in sorted((BASE / "CP_337").glob("*.md")):
            m = re.search(r"Fonte: .*?, art\. ([0-9A-Z\-]+)", p.read_text(encoding="utf-8"))
            if m and m.group(1) == num:
                achados.append(p)
        nome = "Código Penal (arts. 337-E a 337-P)"
    elif lei in ("lei", "14133"):
        num = resto[-1].upper()
        achados = []
        for p in sorted((BASE / "Lei_14133_2021").glob("*.md")):
            t = p.read_text(encoding="utf-8")
            m = re.search(r"Fonte: .*, art\. ([0-9A-Z\-]+)", t)
            if m and m.group(1).rstrip("ºo°") == num.rstrip("ºo°"):
                achados.append(p)
        nome = "Lei nº 14.133/2021"
    else:
        print("Lei desconhecida. Use: cf, cdc ou lei.")
        return
    if not achados:
        print(f"Não encontrei o artigo {num} em {nome}.")
        return
    for p in achados:
        txt = limpar(p.read_text(encoding="utf-8"))
        if romano:
            txt = inciso(txt, romano) or f"(inciso {romano} não encontrado em {p.name})"
        print(f"=== {nome} | {p.relative_to(BASE)} ===\n{txt}\n")


main()
