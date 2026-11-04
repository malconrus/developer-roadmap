# GitHub Copilot com Ollama (agente local, sem custo de API)

A tela "Configure a model provider" (Provider + API key guardada no chaveiro do
sistema) é do **GitHub Copilot** (CLI ou app). Os dois aceitam Ollama como
provedor, então o Copilot vira mais um executor local do orquestrador.

Docs: [Copilot CLI com modelos próprios](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-byok-models)
· [Copilot app com modelos próprios](https://docs.github.com/en/copilot/how-tos/github-copilot-app/use-byok-models)

## Limites desta máquina (leia antes)

- O Copilot exige um modelo com **tool calling e streaming**. O qwen3 tem os dois.
- A GitHub recomenda **128k de contexto**; com 4 GB de VRAM o máximo prático é
  **16k**. As instruções internas do agente já ocupam boa parte disso, então use
  só para tarefas curtas e mecânicas.
- 16k de contexto não cabe inteiro na GPU junto com o modelo: parte vai para a
  CPU e fica lento. Rode **uma tarefa por vez** e sem outro lote de GPU.
- Ainda é preciso entrar com a conta GitHub; o plano Copilot não é exigido
  quando se usa provedor próprio (segundo a doc do app).

## 1. Criar o modelo do agente (uma vez)

Salve como `D:\ACERVO_MALCON\prompts\local\Modelfile.agente`:

```
FROM qwen3:4b-gpu-direto
PARAMETER num_ctx 16384
PARAMETER temperature 0.2
```

Depois, no PowerShell:

```powershell
ollama create qwen3:4b-agente -f D:\ACERVO_MALCON\prompts\local\Modelfile.agente
ollama run qwen3:4b-agente "responda só: ok"
```

Partindo do `-gpu-direto`, o thinking continua desligado.

## 2a. Copilot CLI (terminal)

```powershell
setx COPILOT_PROVIDER_BASE_URL "http://localhost:11434/v1"
setx COPILOT_MODEL "qwen3:4b-agente"
setx COPILOT_PROVIDER_MAX_PROMPT_TOKENS "14000"
setx COPILOT_PROVIDER_MAX_OUTPUT_TOKENS "1500"
setx COPILOT_OFFLINE "true"
```

Feche e abra o terminal. Sem API key: o Ollama local não pede.
`COPILOT_OFFLINE=true` impede o envio de qualquer coisa para a GitHub.
Se der erro de endereço, tente a URL sem `/v1`. Ver exemplos:
`copilot help providers`.

Uso pelo orquestrador (uma tarefa, não interativo):

```powershell
copilot -p "Renomeie os arquivos de D:\pasta para o padrão art-NNN.md. Não apague nada."
```

## 2b. Copilot app (a tela da imagem)

1. **Provider**: `Ollama (local)`.
2. **Base URL**: `http://localhost:11434/v1` (já vem preenchida).
3. **Model ID**: o nome exato que aparece em `ollama list`, de preferência
   `qwen3:4b-agente`. Enquanto ele não for criado, `qwen3:4b-gpu-direto`
   funciona, mas com contexto pequeno o agente pode cortar as instruções.
4. **Save and continue** (Ctrl+Enter). Não há campo de API key para Ollama.

## 3. Conferir

- `python D:\ACERVO_MALCON\prompts\local\rodar_local.py status` deve mostrar
  `qwen3:4b-agente` carregado enquanto o Copilot trabalha.
- Se o Copilot ficar repetindo a mesma ação, pare com Ctrl+C: as regras
  anti-loop do orquestrador valem para ele também (2 erros = volta para o Claude).
