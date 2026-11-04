import sys, re, json, pathlib, urllib.request

BASE = pathlib.Path(__file__).parent
API = "http://localhost:3001/api/v1"
CHAVE = pathlib.Path(r"D:\IA_LOCAL\anythingllm_api_key.txt").read_text(encoding="utf-8").strip()
executar = "--executar" in sys.argv
limite = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else None

LEIS = {
    "Lei_14133_2021": ("Lei 14.133", "Lei nº 14.133/2021 (Nova Lei de Licitações e Contratos)"),
    "CF_1988": ("CF 1988", "Constituição Federal de 1988"),
    "CDC_8078_1990": ("CDC", "Código de Defesa do Consumidor (Lei nº 8.078/1990)"),
}
PROMPT = (
    "Você responde perguntas sobre a legislação brasileira usando SOMENTE os trechos do contexto. "
    "Sempre cite a lei e o artigo exatos que aparecem no trecho (ex.: Lei nº 8.078/1990, art. 26). "
    "Se o contexto não trouxer a resposta, responda exatamente: Não encontrei na base. "
    "Nunca atribua um artigo a uma lei diferente da que está escrita no trecho."
)
LOG = BASE / "importados_v2.txt"
FALHAS = BASE / "falhas_v2.txt"
feitos = set(LOG.read_text(encoding="utf-8").splitlines()) if LOG.exists() else set()
MAX = 5000


def chamar(caminho, corpo=None):
    req = urllib.request.Request(
        API + caminho,
        data=json.dumps(corpo).encode("utf-8") if corpo is not None else None,
        headers={"Authorization": f"Bearer {CHAVE}", "Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req, timeout=300))


def campo(fm, nome):
    m = re.search(rf"(?m)^{nome}:\s*(.+)$", fm)
    return m.group(1).strip().strip('"') if m else ""


def partes(p, nome_lei):
    """Devolve lista de (titulo, texto) prontos para enviar, com a lei no começo de cada pedaço."""
    bruto = p.read_text(encoding="utf-8")
    if bruto.startswith("---"):
        fm, corpo = bruto.split("---", 2)[1:3]
        rotulo = campo(fm, "rotulo")
        hier = [campo(fm, h) for h in ("titulo", "capitulo", "secao")]
        cab = " › ".join([nome_lei] + [h for h in hier if h] + [rotulo])
        corpo = re.sub(r"<a id=\"[^\"]*\"></a>", "", corpo).strip()
        titulo = f"{nome_lei} - {rotulo}"
    else:
        cab = ""
        corpo = bruto.strip()
        m = re.search(r"Fonte: (.+)$", corpo)
        titulo = m.group(1).strip() if m else p.stem
    if len(corpo) <= MAX:
        blocos = [corpo]
    else:
        blocos, atual = [], ""
        for sec in re.split(r"(?m)(?=^## )", corpo):
            if atual and len(atual) + len(sec) > MAX:
                blocos.append(atual)
                atual = ""
            atual += sec
        blocos.append(atual)
    saida = []
    for n, b in enumerate(blocos, 1):
        t = titulo if len(blocos) == 1 else f"{titulo} (parte {n}/{len(blocos)})"
        saida.append((t, (cab + "\n\n" + b).strip() if cab else b))
    return saida


arquivos = []
for pasta, (ws_nome, nome_lei) in LEIS.items():
    for p in sorted((BASE / "md" / pasta).glob("*.md")):
        if not p.name.startswith("_") and str(p.relative_to(BASE)) not in feitos:
            arquivos.append((pasta, p))
if limite:
    arquivos = arquivos[:limite]
print(f"{len(arquivos)} arquivos a importar em {len(LEIS)} workspaces (já feitos: {len(feitos)})")
if not executar:
    pasta, p = next((x for x in arquivos if x[0] == "CF_1988"), arquivos[0])
    ex = partes(p, LEIS[pasta][1])
    print(f"exemplo: {p.name} -> {len(ex)} pedaço(s); primeiro:\n{ex[0][1][:300]}")
    print("SIMULAÇÃO: nada enviado. Use --executar (opcional --limite N).")
    sys.exit()

slugs = {}
existentes = {w["name"]: w["slug"] for w in chamar("/workspaces")["workspaces"]}
for pasta, (ws_nome, _) in LEIS.items():
    slug = existentes.get(ws_nome) or chamar("/workspace/new", {"name": ws_nome})["workspace"]["slug"]
    chamar(f"/workspace/{slug}/update", {
        "openAiPrompt": PROMPT, "topN": 8, "similarityThreshold": 0.2, "chatMode": "query",
        "queryRefusalResponse": "Não encontrei na base.",
    })
    slugs[pasta] = slug
print("workspaces:", slugs)

for i, (pasta, p) in enumerate(arquivos, 1):
    rel = str(p.relative_to(BASE))
    ok = True
    for titulo, texto in partes(p, LEIS[pasta][1]):
        r = chamar("/document/raw-text", {"textContent": texto, "metadata": {"title": titulo}})
        local = "custom-documents/" + pathlib.PureWindowsPath(r["documents"][0]["location"]).name
        ws = chamar(f"/workspace/{slugs[pasta]}/update-embeddings", {"adds": [local]})["workspace"]
        if not any(d["docpath"] == local for d in ws.get("documents", [])):
            ok = False
            print(f"FALHOU: {rel} ({titulo})")
    with open(LOG if ok else FALHAS, "a", encoding="utf-8") as f:
        f.write(rel + "\n")
    if i % 25 == 0:
        print(f"{i}/{len(arquivos)}")
print("concluído")
