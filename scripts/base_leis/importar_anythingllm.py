import sys, json, pathlib, urllib.request

BASE = pathlib.Path(__file__).parent
API = "http://localhost:3001/api/v1"
CHAVE = pathlib.Path(r"D:\IA_LOCAL\anythingllm_api_key.txt").read_text(encoding="utf-8").strip()
WORKSPACE = "Leis"
executar = "--executar" in sys.argv
limite = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else None
LOG = BASE / "importados.txt"
feitos = set(LOG.read_text(encoding="utf-8").splitlines()) if LOG.exists() else set()


def chamar(caminho, corpo):
    req = urllib.request.Request(
        API + caminho,
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Authorization": f"Bearer {CHAVE}", "Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req, timeout=120))


arquivos = [p for p in sorted((BASE / "md").rglob("*.md")) if not p.name.startswith("_") and str(p.relative_to(BASE)) not in feitos]
if limite:
    arquivos = arquivos[:limite]
print(f"{len(arquivos)} arquivos a importar no workspace '{WORKSPACE}' (já feitos: {len(feitos)})")
if not executar:
    print("SIMULAÇÃO: nada enviado. Use --executar (opcional --limite 20 para teste).")
    sys.exit()

def pegar(caminho):
    req = urllib.request.Request(API + caminho, headers={"Authorization": f"Bearer {CHAVE}"})
    return json.load(urllib.request.urlopen(req, timeout=60))


slug = WORKSPACE.lower()
if slug not in [w["slug"] for w in pegar("/workspaces")["workspaces"]]:
    chamar("/workspace/new", {"name": WORKSPACE})

for i, p in enumerate(arquivos, 1):
    rel = str(p.relative_to(BASE))
    r = chamar("/document/raw-text", {
        "textContent": p.read_text(encoding="utf-8"),
        "metadata": {"title": f"{p.parent.name}/{p.stem}"},
    })
    local = "custom-documents/" + pathlib.PureWindowsPath(r["documents"][0]["location"]).name
    ws = chamar(f"/workspace/{slug}/update-embeddings", {"adds": [local]})["workspace"]
    if not any(d["docpath"] == local for d in ws.get("documents", [])):
        print(f"FALHOU o embedding de {rel}; seguindo.")
        with open(BASE / "falhas.txt", "a", encoding="utf-8") as f:
            f.write(rel + "\n")
        continue
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(rel + "\n")
    if i % 25 == 0:
        print(f"{i}/{len(arquivos)}")
print("concluído")
