# YouTube Channel Operator — Lite (gratis)

**Tu semana de YouTube en un comando: últimos 7 días vs. los 7 anteriores, cada vídeo nuevo vs. tu propia mediana a la misma edad y la única mejora que conviene hacer — calculado con tu propio canal, no adivinado por un prompt.**

![Ejecución real de `yto.py demo` con el canal de ejemplo incluido](docs/demo.gif)

<sub>Ejecución real con el **canal de ejemplo** (datos ficticios) · [English](README.md) · [Deutsch](README.de.md) · Español · [Português](README.pt.md) · [日本語](README.ja.md)</sub>

## Instalar en Claude Code

```
/plugin marketplace add jmshinhwa/youtube-channel-operator
/plugin install yt-operator-lite@readystack-youtube
```

Luego pide: **«enséñame una demo del informe semanal de YouTube»** (sin iniciar sesión) y después **«conecta mi canal de YouTube»** ([configuración de ~10 minutos](plugins/yt-operator-lite/docs/SETUP.md)). Informes en español: `--lang es`.

- 5 skills: `weekly` · `profile` · `chapters` · `check` · `connect` — los scripts calculan, Claude solo orquesta.
- Acceso de solo lectura con **tu propio** cliente OAuth de Google; los datos se quedan en tu ordenador (`~/.youtube-operator`).
- Solo la biblioteca estándar de Python. Un informe semanal de 60 vídeos usó en la prueba 5 de las 10.000 unidades diarias de la Data API.
- Pro (12 skills): retención, CTR de miniaturas, búsquedas sin vídeo propio, cola de comentarios, vídeos atípicos de rivales, plan semanal, resumen mensual → https://getreadystack.com/apps/youtube-channel-operator-skill-pack/

MIT · [ReadyStack](https://getreadystack.com) · sin relación con YouTube ni Google.
