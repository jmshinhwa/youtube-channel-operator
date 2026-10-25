# YouTube Channel Operator — Lite (kostenlos)

**Deine YouTube-Woche mit einem Befehl: letzte 7 Tage vs. die 7 davor, jedes neue Video vs. dein eigener Median im gleichen Alter und die eine Sache, die du ändern solltest — berechnet aus deinem eigenen Kanal, nicht von einem Prompt geraten.**

![Echter Lauf von `yto.py demo` auf dem mitgelieferten Beispielkanal](docs/demo.gif)

<sub>Echter Lauf auf dem **Beispielkanal** (erfundene Daten) · [English](README.md) · Deutsch · [Español](README.es.md) · [Português](README.pt.md) · [日本語](README.ja.md)</sub>

## Installation in Claude Code

```
/plugin marketplace add jmshinhwa/youtube-channel-operator
/plugin install yt-operator-lite@readystack-youtube
```

Dann fragen: **„Zeig mir eine Demo des YouTube-Wochenberichts“** (ohne Anmeldung) und später **„Verbinde meinen YouTube-Kanal“** ([Einrichtung, ca. 10 Minuten](plugins/yt-operator-lite/docs/SETUP.md)). Berichte auf Deutsch: `--lang de`.

- 5 Skills: `weekly` · `profile` · `chapters` · `check` · `connect` — die Skripte rechnen, Claude orchestriert.
- Nur lesender Zugriff mit **deinem eigenen** Google-OAuth-Client; die Daten bleiben auf deinem Rechner (`~/.youtube-operator`).
- Nur Python-Standardbibliothek, nichts zu installieren. Ein Wochenlauf mit 60 Videos brauchte im Test 5 von 10.000 Data-API-Einheiten pro Tag.
- Pro (12 Skills): Zuschauerbindung, Thumbnail-CTR, Suchbegriffe ohne eigenes Video, Kommentar-Warteschlange, Ausreißer der Konkurrenz, Wochenplan, Monatsrückblick → https://getreadystack.com/apps/youtube-channel-operator-skill-pack/

MIT · [ReadyStack](https://getreadystack.com) · nicht mit YouTube oder Google verbunden.
