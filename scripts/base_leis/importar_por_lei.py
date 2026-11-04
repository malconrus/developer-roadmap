"""Importa os artigos de md/ no AnythingLLM, um workspace por lei.

Uso:
    python importar_por_lei.py                    (simulação: mostra o que faria)
    python importar_por_lei.py --executar         (envia tudo o que falta)
    python importar_por_lei.py --executar --limite 150

Retomada: cada arquivo concluído vai para importados_v2.txt e cada pedaço enviado
para importados_v2_partes.txt. Rodar de novo continua de onde parou, sem duplicar.
Arquivos que falharam vão para falhas_v2.txt e são tentados de novo na próxima rodada.
"""
import pathlib
import re
import sys
import urllib.error

from comum import (ERROS_DE_REDE, MAX_FALHAS_SEGUIDAS, Cliente, Trava, anotar,
                   argumento_int, ler_chave, ler_registro)

BASE = pathlib.Path(__file__).parent
executar = "--executar" in sys.argv
limite = argumento_int("--limite")

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
LOG_PARTES = BASE / "importados_v2_partes.txt"
FALHAS = BASE / "falhas_v2.txt"
TRAVA = BASE / "importacao.lock"
MAX = 5000


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


def pendentes(feitos):
    lista = []
    for pasta in LEIS:
        for p in sorted((BASE / "md" / pasta).glob("*.md")):
            if not p.name.startswith("_") and str(p.relative_to(BASE)) not in feitos:
                lista.append((pasta, p))
    return lista


def preparar_workspaces(api):
    slugs = {}
    existentes = {w["name"]: w["slug"] for w in api.chamar("/workspaces")["workspaces"]}
    for pasta, (ws_nome, _) in LEIS.items():
        slug = existentes.get(ws_nome) or api.chamar("/workspace/new", {"name": ws_nome})["workspace"]["slug"]
        api.chamar(f"/workspace/{slug}/update", {
            "openAiPrompt": PROMPT, "topN": 8, "similarityThreshold": 0.2, "chatMode": "query",
            "queryRefusalResponse": "Não encontrei na base.",
        })
        slugs[pasta] = slug
    return slugs


def enviar_arquivo(api, slug, pasta, p, rel, partes_feitas):
    """Envia os pedaços que faltam de um arquivo. Devolve True se todos entraram no workspace."""
    ok = True
    for n, (titulo, texto) in enumerate(partes(p, LEIS[pasta][1]), 1):
        chave_parte = f"{rel}#{n}"
        if chave_parte in partes_feitas:
            continue
        r = api.chamar("/document/raw-text", {"textContent": texto, "metadata": {"title": titulo}})
        local = "custom-documents/" + pathlib.PureWindowsPath(r["documents"][0]["location"]).name
        ws = api.chamar(f"/workspace/{slug}/update-embeddings", {"adds": [local]})["workspace"]
        if any(d["docpath"] == local for d in ws.get("documents", [])):
            anotar(LOG_PARTES, chave_parte)
        else:
            ok = False
            print(f"FALHOU o embedding: {rel} ({titulo})")
    return ok


def main():
    feitos = ler_registro(LOG)
    arquivos = pendentes(feitos)
    if limite:
        arquivos = arquivos[:limite]
    print(f"{len(arquivos)} arquivos a importar em {len(LEIS)} workspaces (já feitos: {len(feitos)})")
    if not arquivos:
        print("Nada a fazer.")
        return
    if not executar:
        pasta, p = next((x for x in arquivos if x[0] == "CF_1988"), arquivos[0])
        ex = partes(p, LEIS[pasta][1])
        print(f"exemplo: {p.name} -> {len(ex)} pedaço(s); primeiro:\n{ex[0][1][:300]}")
        print("SIMULAÇÃO: nada enviado. Use --executar (opcional --limite N).")
        return

    api = Cliente(ler_chave())
    with Trava(TRAVA):
        try:
            slugs = preparar_workspaces(api)
        except ERROS_DE_REDE as e:
            sys.exit(f"Não consegui falar com o AnythingLLM em {api.api} ({getattr(e, 'reason', e)}). "
                     "Ele está aberto? Nada foi enviado.")
        print("workspaces:", slugs)
        partes_feitas = ler_registro(LOG_PARTES)
        ok_total = falhas_total = seguidas = 0
        try:
            for i, (pasta, p) in enumerate(arquivos, 1):
                rel = str(p.relative_to(BASE))
                try:
                    ok = enviar_arquivo(api, slugs[pasta], pasta, p, rel, partes_feitas)
                except urllib.error.HTTPError as e:
                    if e.code in (401, 403):
                        sys.exit(f"A API recusou a chave (HTTP {e.code}). Confira a chave em ANYTHINGLLM_API_KEY ou no arquivo da chave; nada mais foi enviado.")
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
        print(f"concluído: {ok_total} importados, {falhas_total} com falha "
              f"(ver {FALHAS.name}), {len(arquivos) - ok_total - falhas_total} não tentados")


if __name__ == "__main__":
    main()
