import sys, urllib.request, pathlib
executar = "--executar" in sys.argv
base = pathlib.Path(__file__).parent
for linha in (base / "leis.txt").read_text(encoding="utf-8").splitlines():
    if not linha.strip() or linha.startswith("#"):
        continue
    nome, url = linha.split(";", 1)
    destino = base / "html" / f"{nome}.html"
    if destino.exists():
        print(f"já existe, pulando: {destino.name}")
    elif not executar:
        print(f"SIMULAÇÃO: baixaria {url} -> {destino}")
    else:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        dados = urllib.request.urlopen(req, timeout=180).read()
        destino.write_bytes(dados)
        print(f"baixado: {destino.name} ({len(dados)} bytes)")
