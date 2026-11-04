"""Versão 1: importa todos os .md de md/ em um único workspace ("Leis").

Substituída por importar_por_lei.py (um workspace por lei), mas mantida porque
o workspace "Leis" e o registro importados.txt foram feitos com ela.

Uso:
    python importar_anythingllm.py                 (simulação)
    python importar_anythingllm.py --executar [--limite 20]

Retomada: cada arquivo concluído vai para importados.txt; rodar de novo pula esses.
Falhas vão para falhas.txt e são tentadas de novo na próxima rodada.
"""
import pathlib
import sys
import urllib.error

from comum import (ERROS_DE_REDE, MAX_FALHAS_SEGUIDAS, Cliente, Trava, anotar,
                   argumento_int, ler_chave, ler_registro)

BASE = pathlib.Path(__file__).parent
WORKSPACE = "Leis"
executar = "--executar" in sys.argv
limite = argumento_int("--limite")
LOG = BASE / "importados.txt"
FALHAS = BASE / "falhas.txt"
TRAVA = BASE / "importacao.lock"


def main():
    feitos = ler_registro(LOG)
    arquivos = [p for p in sorted((BASE / "md").rglob("*.md"))
                if not p.name.startswith("_") and str(p.relative_to(BASE)) not in feitos]
    if limite:
        arquivos = arquivos[:limite]
    print(f"{len(arquivos)} arquivos a importar no workspace '{WORKSPACE}' (já feitos: {len(feitos)})")
    if not executar:
        print("SIMULAÇÃO: nada enviado. Use --executar (opcional --limite 20 para teste).")
        return
    if not arquivos:
        return

    api = Cliente(ler_chave())
    with Trava(TRAVA):
        slug = WORKSPACE.lower()
        try:
            if slug not in [w["slug"] for w in api.chamar("/workspaces", timeout=60)["workspaces"]]:
                api.chamar("/workspace/new", {"name": WORKSPACE})
        except ERROS_DE_REDE as e:
            sys.exit(f"Não consegui falar com o AnythingLLM em {api.api} ({getattr(e, 'reason', e)}). "
                     "Ele está aberto? Nada foi enviado.")
        ok_total = falhas_total = seguidas = 0
        try:
            for i, p in enumerate(arquivos, 1):
                rel = str(p.relative_to(BASE))
                try:
                    r = api.chamar("/document/raw-text", {
                        "textContent": p.read_text(encoding="utf-8"),
                        "metadata": {"title": f"{p.parent.name}/{p.stem}"},
                    }, timeout=120)
                    local = "custom-documents/" + pathlib.PureWindowsPath(r["documents"][0]["location"]).name
                    ws = api.chamar(f"/workspace/{slug}/update-embeddings", {"adds": [local]}, timeout=120)["workspace"]
                    ok = any(d["docpath"] == local for d in ws.get("documents", []))
                    if not ok:
                        print(f"FALHOU o embedding de {rel}; seguindo.")
                except urllib.error.HTTPError as e:
                    if e.code in (401, 403):
                        sys.exit(f"A API recusou a chave (HTTP {e.code}); nada mais foi enviado.")
                    print(f"FALHOU: {rel} (HTTP {e.code})")
                    ok = False
                except ERROS_DE_REDE as e:
                    print(f"FALHOU: {rel} (rede: {getattr(e, 'reason', e)})")
                    ok = False
                anotar(LOG if ok else FALHAS, rel)
                if ok:
                    ok_total += 1
                    seguidas = 0
                else:
                    falhas_total += 1
                    seguidas += 1
                    if seguidas >= MAX_FALHAS_SEGUIDAS:
                        print(f"{seguidas} falhas seguidas: o AnythingLLM parece fora do ar. "
                              "Parando; rode de novo para continuar de onde parou.")
                        break
                if i % 25 == 0:
                    print(f"{i}/{len(arquivos)}")
        except KeyboardInterrupt:
            print("\nInterrompido. O progresso está salvo; rode de novo para continuar.")
        print(f"concluído: {ok_total} importados, {falhas_total} com falha (ver {FALHAS.name})")


if __name__ == "__main__":
    main()
