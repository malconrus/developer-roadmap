# prompts/

Prompts para rodar Claude Code, Ollama e AnythingLLM juntos, com o mínimo de tokens e sem laço infinito.

| Arquivo | Para quê |
|---|---|
| [orquestrador-claude-code.md](orquestrador-claude-code.md) | Texto para colar no Claude Code ou no projeto da nuvem. Cada entrada vira um prompt remodelado. |
| [local/rodar_local.py](local/rodar_local.py) | Chamadas ao Ollama e ao AnythingLLM com timeout, teto de tokens e no máximo uma nova tentativa; `status` detecta scripts duplicados. |
| [local/copilot-ollama.md](local/copilot-ollama.md) | Como ligar o GitHub Copilot (CLI ou app) ao Ollama local, como agente sem custo de API. |
| [skills.md](skills.md) | Skills instaladas que o orquestrador usa e as sugeridas. |

## Instalação no PC

1. Copie a pasta `prompts/` para `D:\ACERVO_MALCON\prompts\`.
2. Defina a chave do AnythingLLM: `setx ANYTHINGLLM_API_KEY "<sua chave>"`.
3. Teste: `python D:\ACERVO_MALCON\prompts\local\rodar_local.py status`.
4. Cole o bloco de `orquestrador-claude-code.md` nas instruções do projeto ou no `CLAUDE.md`.
