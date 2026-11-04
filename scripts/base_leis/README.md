# Base de leis para o AnythingLLM

Scripts que montam uma base local de legislação (Lei nº 14.133/2021, CF/88, CDC e Código Penal)
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
| `artigo.py` | Consulta direta por artigo, sem IA: `python artigo.py cf 5 II`, `python artigo.py lei 28` |
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

## Versão 3: dispositivo em cada linha

Desde a v3, cada trecho enviado traz o dispositivo escrito na própria linha, para o modelo
citar inciso e parágrafo certos:

- CF e CDC (cabeçalhos do lexbr): `## Inciso XXI` vira `## [art. 37, XXI] Inciso XXI`,
  `## § 3º` vira `## [art. 37, § 3º] § 3º`, e `### Inciso I` / `### Alínea a` herdam o `##` anterior.
- Lei 14.133 e Código Penal (texto corrido): `I - pregão;` vira `[art. 28, I] I - pregão;`,
  e incisos depois de um `§` pertencem a esse parágrafo.

A v3 usa registros novos (`importados_v3*.txt`, `falhas_v3.txt`); os `*_v2*.txt` ficam como histórico.

## Retomada

A importação pode ser interrompida a qualquer momento (Ctrl+C, queda de energia,
AnythingLLM fechado) e continua de onde parou na próxima vez:

- Cada arquivo concluído entra em `importados_v3.txt` (v1: `importados.txt`) assim
  que termina, gravado direto no disco. Esses arquivos são pulados nas rodadas seguintes.
- Artigos longos são divididos em pedaços de até 5.000 caracteres. Cada pedaço enviado
  entra em `importados_v3_partes.txt`, então um artigo que parou no meio não manda de
  novo os pedaços que já entraram (não cria duplicatas no workspace).
- Arquivos que falharam vão para `falhas_v3.txt` (v1: `falhas.txt`). Como não estão em
  `importados_v3.txt`, são tentados de novo automaticamente na próxima rodada.

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

Os workspaces criados por `importar_por_lei.py` são `Lei 14.133`, `CF 1988`, `CDC` e `Código Penal`,
em modo `query`, com temperatura 0,1, `topN` 8, limiar de similaridade 0,2 e um prompt que
obriga a citar lei, artigo e inciso exatos (inciso logo após o caput é "art. X, I", não "§ 1º"),
a copiar valores e prazos como estão, a avisar quando o trecho diz "Vide Decreto" e a responder
"Não encontrei na base." quando o contexto não traz a resposta.

O AnythingLLM corta o nome do documento no primeiro ponto, então os títulos são enviados sem
pontos ("Lei nº 14133/2021 - Art 28").

## Instalar no PC

Copie `comum.py`, `importar_por_lei.py` e `importar_anythingllm.py` para `D:\BASE_LEIS`
(os três precisam ficar na mesma pasta). Rode sem `python -I`: essa opção tira a pasta do
script do caminho de importação e o `comum.py` não é encontrado. Não troque os arquivos
enquanto uma importação estiver rodando.

Requer Python 3.8+ e só a biblioteca padrão.
