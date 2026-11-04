# Skills para o orquestrador

Ordem de uso: primeiro as já instaladas, depois as sugeridas (só com aprovação).

## Já instaladas (verificado em 04/11/2026)

| Skill / ferramenta | Quando usar |
|---|---|
| `superpowers:writing-plans` | Tarefa com vários passos: plano curto antes de executar. |
| `superpowers:systematic-debugging` | Script travado, reprocessando ou com erro. |
| `superpowers:verification-before-completion` | Antes de dizer "pronto": contagem + amostra. |
| `superpowers:dispatching-parallel-agents` | Só quando você escrever "pode paralelizar com agentes" (custa tokens). |
| `mattpocock-skills:writing-for-agents` | Escrever ou revisar o próprio prompt / CLAUDE.md. |
| `mattpocock-skills:grilling` | Quando a entrada for vaga e precisar de perguntas. |
| `anthropic-skills:xlsx`, `pdf`, `docx` | Ler ou gerar planilhas e documentos. |
| Plugin `context-meter` | Ver o uso de contexto e cortar a sessão antes de encarecer. |
| MCP `acervo` (Claude Desktop) | Consultar o acervo local sem ler pastas inteiras. |

## Sugeridas (criar só com OK)

1. **Skill própria `remodelar-comando`**: transforma este prompt em skill
   (via `anthropic-skills:skill-creator`), para não precisar colar a cada sessão.
2. **Agent-skill no AnythingLLM** de busca nas leis com citação de artigo
   (a pasta de agent-skills está vazia hoje).
3. **Plugin de uso de tokens** (comunidade) para medir o custo por entrada.
