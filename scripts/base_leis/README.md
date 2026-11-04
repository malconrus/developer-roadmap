# Base de leis para o AnythingLLM

Scripts que montam uma base local de legislação (Lei nº 14.133/2021, CF/88 e CDC)
e a importam no AnythingLLM, para consulta com um modelo local pelo Ollama
(embedder `bge-m3`, modelo `qwen3:4b`). Tudo roda no PC, em `D:\BASE_LEIS`.

Só os scripts estão aqui. O texto das leis (`html/`, `md/`), os registros de
importação e a chave da API ficam no PC e não são versionados (ver `.gitignore`).

## Arquivos

| Arquivo | O que faz |
|---|---|
| `leis.txt` | Lista das leis a baixar, uma por linha: `nome;url` |
| `baixar_leis.py` | Baixa o HTML de cada lei do Planalto para `html/` |
| `gerar_md.py` | Usa o [lexbr](https://github.com/yagodejesus/lexbr) (em `ferramentas/lexbr`) para gerar um `.md` por trecho em `md/` |
| `importar_por_lei.py` | **Atual.** Importa `md/` no AnythingLLM, um workspace por lei |
| `importar_anythingllm.py` | Versão 1: importa tudo em um único workspace `Leis` |
| `comum.py` | Chamadas à API com novas tentativas, trava e registro, usado pelos dois importadores |

## Uso

Todos os scripts começam em **simulação** e só mudam algo com `--executar`.

```bat
cd /d D:\BASE_LEIS
python baixar_leis.py                 & rem mostra o que baixaria
python baixar_leis.py --executar
python gerar_md.py --executar
python importar_por_lei.py            & rem mostra quantos arquivos faltam e um exemplo
python importar_por_lei.py --executar --limite 150
```

`--limite N` envia só os próximos N arquivos pendentes. Rodar de novo pega os N seguintes.

## Retomada

A importação pode ser interrompida a qualquer momento (Ctrl+C, queda de energia,
AnythingLLM fechado) e continua de onde parou na próxima vez:

- Cada arquivo concluído entra em `importados_v2.txt` (v1: `importados.txt`) assim
  que termina, gravado direto no disco. Esses arquivos são pulados nas rodadas seguintes.
- Artigos longos são divididos em pedaços de até 5.000 caracteres. Cada pedaço enviado
  entra em `importados_v2_partes.txt`, então um artigo que parou no meio não manda de
  novo os pedaços que já entraram (não cria duplicatas no workspace).
- Arquivos que falharam vão para `falhas_v2.txt` (v1: `falhas.txt`). Como não estão em
  `importados_v2.txt`, são tentados de novo automaticamente na próxima rodada.

## Proteções contra travar ou ficar em loop

- Cada chamada à API tenta no máximo 3 vezes (espera 5 s, depois 10 s) em erro de rede
  ou erro 5xx. Erros 4xx não são repetidos.
- Chave recusada (HTTP 401/403) para tudo na hora.
- Depois de 5 arquivos seguidos com falha, o lote para com a mensagem de que o
  AnythingLLM parece fora do ar. Nada se perde: é só rodar de novo.
- Uma trava (`importacao.lock`) impede duas importações ao mesmo tempo na mesma pasta.
  Se o PC desligou no meio e a trava ficou para trás, confira que nada está rodando e
  use `--forcar`.

## Configuração

| Variável | Padrão |
|---|---|
| `ANYTHINGLLM_API` | `http://localhost:3001/api/v1` |
| `ANYTHINGLLM_API_KEY` | (vazia: lê do arquivo abaixo) |
| `ANYTHINGLLM_CHAVE_ARQ` | `D:\IA_LOCAL\anythingllm_api_key.txt` |

Os workspaces criados por `importar_por_lei.py` são `Lei 14.133`, `CF 1988` e `CDC`,
em modo `query`, com `topN` 8, limiar de similaridade 0,2 e um prompt que obriga a citar
lei e artigo exatos e a responder "Não encontrei na base." quando o contexto não traz a resposta.

## Instalar no PC

Copie `comum.py`, `importar_por_lei.py` e `importar_anythingllm.py` para `D:\BASE_LEIS`
(os três precisam ficar na mesma pasta). Os registros existentes (`importados_v2.txt`,
`falhas_v2.txt`) continuam valendo, porque o formato não mudou. Não troque os arquivos
enquanto uma importação estiver rodando.

Requer Python 3.8+ e só a biblioteca padrão.
