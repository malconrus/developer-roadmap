"""Chamadas locais baratas e com limites para o orquestrador.

Uso:
  python rodar_local.py ollama "texto"            (ou texto via stdin)
  python rodar_local.py ollama --modelo qwen3:1.7b-gpu-direto "texto"
  python rodar_local.py rag lei-14133 "pergunta"
  python rodar_local.py status

Só biblioteca padrão. Toda chamada tem timeout, teto de tokens e no máximo
uma nova tentativa, para nunca entrar em laço.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
ANYTHING = os.environ.get("ANYTHINGLLM_URL", "http://localhost:3001")
MODELO_PADRAO = os.environ.get("MODELO_LOCAL", "qwen3:4b-gpu-direto")
MAX_SAIDA = 4000  # caracteres devolvidos ao Claude, para economizar tokens
TENTATIVAS = 2    # a original + uma nova tentativa


def post(url, corpo, timeout, cabecalhos=None):
    dados = json.dumps(corpo).encode("utf-8")
    req = urllib.request.Request(url, data=dados, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (cabecalhos or {}).items():
        req.add_header(k, v)
    ultimo_erro = None
    for tentativa in range(TENTATIVAS):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            ultimo_erro = e
            if tentativa + 1 < TENTATIVAS:
                time.sleep(3)
    raise SystemExit(f"FALHOU: {url} -> {ultimo_erro}")


def get(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:  # status é só informativo
        return {"erro": str(e)}


def limpar(texto):
    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()
    if len(texto) > MAX_SAIDA:
        texto = texto[:MAX_SAIDA] + "\n[...cortado]"
    return texto


def cmd_ollama(a):
    texto = a.texto or sys.stdin.read()
    corpo = {
        "model": a.modelo,
        "messages": [
            {"role": "system", "content": "Responda em português, de forma direta e curta."},
            {"role": "user", "content": texto},
        ],
        "stream": False,
        "think": False,
        "keep_alive": "5m",
        "options": {"num_predict": a.max_tokens, "num_ctx": a.ctx, "temperature": 0.2},
    }
    r = post(f"{OLLAMA}/api/chat", corpo, timeout=a.timeout)
    print(limpar(r.get("message", {}).get("content", "")))


def cmd_rag(a):
    chave = os.environ.get("ANYTHINGLLM_API_KEY")
    if not chave:
        raise SystemExit("FALHOU: defina ANYTHINGLLM_API_KEY")
    corpo = {"message": a.pergunta, "mode": "query"}
    r = post(
        f"{ANYTHING}/api/v1/workspace/{a.workspace}/chat",
        corpo,
        timeout=a.timeout,
        cabecalhos={"Authorization": f"Bearer {chave}"},
    )
    print(limpar(r.get("textResponse") or ""))
    fontes = [s.get("title", "?") for s in r.get("sources", [])][:5]
    if fontes:
        print("\nFontes: " + "; ".join(fontes))


def processos_python():
    if os.name == "nt":
        ps = ("Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
              "ForEach-Object { \"$($_.ProcessId) $($_.CommandLine)\" }")
        cmd = ["powershell", "-NoProfile", "-Command", ps]
    else:
        cmd = ["ps", "-eo", "pid,args"]
    try:
        saida = subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout
    except Exception as e:
        return [f"(não consegui listar processos: {e})"]
    eu = str(os.getpid())
    return [l.strip() for l in saida.splitlines()
            if "python" in l.lower() and ".py" in l and not l.strip().startswith(eu)
            and "rodar_local.py" not in l]


def cmd_status(_a):
    procs = processos_python()
    print("Scripts Python rodando:", len(procs))
    for p in procs:
        print("  ", p[:200])
    ps = get(f"{OLLAMA}/api/ps")
    modelos = [m.get("name") for m in ps.get("models", [])] if "models" in ps else ps
    print("Ollama carregado:", modelos)
    print("AnythingLLM:", get(f"{ANYTHING}/api/ping"))
    duplicados = {}
    for p in procs:
        partes = p.split(None, 1)
        if len(partes) == 2:
            duplicados.setdefault(partes[1], []).append(partes[0])
    for linha, pids in duplicados.items():
        if len(pids) > 1:
            print(f"ATENÇÃO: {len(pids)} cópias do mesmo comando (PIDs {', '.join(pids)}): {linha[:120]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    o = sub.add_parser("ollama")
    o.add_argument("texto", nargs="?")
    o.add_argument("--modelo", default=MODELO_PADRAO)
    o.add_argument("--max-tokens", type=int, default=800)
    o.add_argument("--ctx", type=int, default=4096)
    o.add_argument("--timeout", type=int, default=120)
    o.set_defaults(func=cmd_ollama)

    r = sub.add_parser("rag")
    r.add_argument("workspace")
    r.add_argument("pergunta")
    r.add_argument("--timeout", type=int, default=180)
    r.set_defaults(func=cmd_rag)

    s = sub.add_parser("status")
    s.set_defaults(func=cmd_status)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
