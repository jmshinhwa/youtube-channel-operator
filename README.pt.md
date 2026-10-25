# YouTube Channel Operator — Lite (grátis)

**Sua semana no YouTube em um comando: últimos 7 dias vs. os 7 anteriores, cada vídeo novo vs. a sua própria mediana na mesma idade e o único ajuste a fazer — calculado com o seu canal, não chutado por um prompt.**

![Execução real de `yto.py demo` no canal de exemplo incluído](docs/demo.gif)

<sub>Execução real no **canal de exemplo** (dados fictícios) · [English](README.md) · [Deutsch](README.de.md) · [Español](README.es.md) · Português · [日本語](README.ja.md)</sub>

## Instalar no Claude Code

```
/plugin marketplace add jmshinhwa/youtube-channel-operator
/plugin install yt-operator-lite@readystack-youtube
```

Depois peça: **"me mostra uma demo do relatório semanal do YouTube"** (sem login) e depois **"conecta meu canal do YouTube"** ([configuração de ~10 minutos](plugins/yt-operator-lite/docs/SETUP.md)). Relatórios em português: `--lang pt`.

- 5 skills: `weekly` · `profile` · `chapters` · `check` · `connect` — os scripts calculam, o Claude só orquestra.
- Acesso somente leitura com **o seu próprio** cliente OAuth do Google; os dados ficam no seu computador (`~/.youtube-operator`).
- Só a biblioteca padrão do Python. Um relatório semanal de 60 vídeos usou no teste 5 das 10.000 unidades diárias da Data API.
- Pro (12 skills): retenção, CTR de miniaturas, buscas sem vídeo seu, fila de comentários, vídeos fora da curva dos rivais, plano da semana, resumo do mês → https://getreadystack.com/apps/youtube-channel-operator-skill-pack/

MIT · [ReadyStack](https://getreadystack.com) · sem vínculo com o YouTube ou o Google.
