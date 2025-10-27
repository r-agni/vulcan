# vulcan

Turns retail security cameras into a real-time assistant — who's in the store, where they linger, and when staff should step in.

Passive cameras record footage nobody watches. This reads the feed live: tracks people, reads behaviour, and alerts staff to the moment that matters.

[Demo video](https://www.youtube.com/watch?v=kxA8C1J06KE)

## How it works

- **YOLOv8 detection + tracking** for per-person trajectories, dwell time per zone, occupancy counts, and line-crossing entry/exit tallies.
- **Gemini reads the store layout** and auto-generates tracking zones (entrance, checkout, aisles) and counting lines — no manual zone drawing.
- **Behavioural analysis every 5s** — Gemini classifies emotion (interest, confusion, frustration), browsing vs. purposeful shopping, and purchase intent from frames.
- **Two alert channels** — engagement opportunities for salespeople, operational issues (queues, overcrowding, dead zones) for managers.
- **RAG over the analytics** so you can ask questions of the history in natural language instead of scrubbing footage.
- **Live dashboard** — heatmaps, trajectories, zone metrics, updating in real time.

~21,000 lines across 83 files.

## Run it

```bash
cp .env.example .env      # add GEMINI_API_KEY, point CAMERA_SOURCE at a stream
pip install -r requirements.txt
python -m app             # dashboard + live analysis
```

Full architecture, the analytics pipeline and alert logic: [docs/README-full.md](docs/README-full.md).
