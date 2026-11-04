"""Funções compartilhadas pelos scripts de importação para o AnythingLLM.

Fica na mesma pasta dos scripts (D:\\BASE_LEIS). Só usa a biblioteca padrão.
"""
import json
import os
import pathlib
import socket
import sys
import time
import urllib.error
import urllib.request

API = os.environ.get("ANYTHINGLLM_API", "http://localhost:3001/api/v1")
ARQ_CHAVE = pathlib.Path(os.environ.get("ANYTHINGLLM_CHAVE_ARQ", r"D:\IA_LOCAL\anythingllm_api_key.txt"))

TENTATIVAS = 3          # tentativas por chamada antes de desistir do arquivo
ESPERA_INICIAL = 5      # segundos; dobra a cada nova tentativa (5, 10, 20)
MAX_FALHAS_SEGUIDAS = 5  # para o lote se o AnythingLLM parecer fora do ar

ERROS_DE_REDE = (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError)


def ler_chave():
    """Lê a chave da API: variável ANYTHINGLLM_API_KEY ou o arquivo em ARQ_CHAVE."""
    chave = os.environ.get("ANYTHINGLLM_API_KEY")
    if chave:
        return chave.strip()
    if not ARQ_CHAVE.exists():
        sys.exit(f"Chave da API não encontrada. Crie {ARQ_CHAVE} ou defina ANYTHINGLLM_API_KEY.")
    return ARQ_CHAVE.read_text(encoding="utf-8").strip()


def argumento_int(nome):
    """Valor inteiro de um argumento como --limite 20, ou None."""
    if nome not in sys.argv:
        return None
    try:
        return int(sys.argv[sys.argv.index(nome) + 1])
    except (IndexError, ValueError):
        sys.exit(f"{nome} precisa de um número, por exemplo: {nome} 20")


class Cliente:
    def __init__(self, chave, api=API):
        self.chave = chave
        self.api = api

    def _uma_vez(self, caminho, corpo, timeout):
        dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
        req = urllib.request.Request(
            self.api + caminho,
            data=dados,
            headers={"Authorization": f"Bearer {self.chave}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)

    def chamar(self, caminho, corpo=None, timeout=300):
        """POST (com corpo) ou GET (sem corpo), com novas tentativas em erro de rede ou 5xx.

        Erros 4xx (chave errada, caminho errado) não são repetidos: sobem na hora.
        Um número fixo de tentativas garante que o script nunca fica em loop.
        """
        espera = ESPERA_INICIAL
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                return self._uma_vez(caminho, corpo, timeout)
            except urllib.error.HTTPError as e:
                if e.code < 500 or tentativa == TENTATIVAS:
                    raise
                motivo = f"HTTP {e.code}"
            except ERROS_DE_REDE as e:
                if tentativa == TENTATIVAS:
                    raise
                motivo = str(getattr(e, "reason", e))
            print(f"  aviso: {caminho} falhou ({motivo}); nova tentativa em {espera}s "
                  f"({tentativa}/{TENTATIVAS})")
            time.sleep(espera)
            espera *= 2


def ler_registro(arq):
    """Conjunto de linhas de um arquivo de registro (vazio se não existir)."""
    if not arq.exists():
        return set()
    return {l.strip() for l in arq.read_text(encoding="utf-8").splitlines() if l.strip()}


def anotar(arq, linha):
    """Acrescenta uma linha e grava no disco na hora, para a retomada valer mesmo após queda."""
    with open(arq, "a", encoding="utf-8") as f:
        f.write(linha + "\n")
        f.flush()
        os.fsync(f.fileno())


class Trava:
    """Impede que duas importações rodem ao mesmo tempo na mesma pasta.

    Se o PC desligar no meio, o arquivo .lock fica para trás: confira que nenhuma
    importação está rodando e rode de novo com --forcar.
    """

    def __init__(self, arq):
        self.arq = arq
        self.minha = False

    def __enter__(self):
        if "--forcar" in sys.argv and self.arq.exists():
            self.arq.unlink()
        try:
            fd = os.open(self.arq, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            sys.exit(f"Outra importação parece estar rodando ({self.arq.name} existe). "
                     "Se não estiver, rode de novo com --forcar.")
        os.write(fd, f"{os.getpid()} {time.strftime('%Y-%m-%d %H:%M:%S')}\n".encode())
        os.close(fd)
        self.minha = True
        return self

    def __exit__(self, *exc):
        if self.minha and self.arq.exists():
            self.arq.unlink()
        return False
