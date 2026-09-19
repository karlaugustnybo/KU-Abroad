---
name: deckgl
description: |
  Build high-performance data-visualization apps with deck.gl. Use this skill whenever the user asks for deck.gl code, wants to integrate deck.gl with React, a map library, or pure JS/TS, needs help picking the right layer, writing a custom layer, or optimizing performance. Also trigger for WebGPU/WebGL2 geospatial visualization, large dataset rendering, heatmaps, 3D meshes, trips, or deck.gl layer configuration questions.
compatibility: |
  Requires code-generation tools (write/edit, bash). Useful with a JS/TS project; can also produce standalone HTML/JS snippets. No runtime dependency.
---

# deck.gl skill

You are a deck.gl expert. Your goal is to generate correct, runnable, idiomatic deck.gl code based on the user's request.

## When to use this skill

Use this skill whenever the user asks anything involving:

- deck.gl code or setup
- geospatial/big-data visualization in a browser
- choosing or configuring deck.gl layers
- React + deck.gl integration
- map integrations (Mapbox, MapLibre, Google Maps, ArcGIS, CARTO)
- custom layers, shaders, or layer extensions
- performance tuning, picking, animations, transitions, coordinate systems

## First step: classify the request

After reading the user's prompt, decide which sub-skill is most relevant. If the request clearly belongs to one of the sub-skills below, delegate by loading that skill's SKILL.md and following its instructions. If multiple apply, pick the dominant one. If it is a simple overview or getting-started question, answer directly using `references/getting-started-and-guides.md`.

## Sub-skill routing

Use these exact skill names when delegating:

| If the user needs...                                      | Use sub-skill |
|-----------------------------------------------------------|---------------|
| Choosing or configuring built-in layers, accessors, props, events | `deckgl-layers` |
| Writing a custom layer, shader, layer extension, subclass, composite layer | `deckgl-custom-layer` |
| React usage, widgets, `@deck.gl/react`, hooks | `deckgl-react` |
| Integration with Mapbox, MapLibre, Google Maps, ArcGIS, CARTO | `deckgl-basemap` |
| `Deck`/`DeckGL` initialization, views, controllers, camera, effects, transitions, extensions, JSON configuration, performance, WebGPU | `deckgl-core` |

When delegating, hand off the user's exact request plus any context you have gathered (framework, base map, layer names, data shape). Then follow the sub-skill instructions.

## General code-generation principles

1. **Use modern v9 imports**. The documentation has moved to named exports.
   - React: `import {DeckGL} from '@deck.gl/react'` (preferred; default import still works but is deprecated).
   - Standalone: `import {Deck} from '@deck.gl/core'` (use `Deck`, not `DeckGL`, unless you are using the scripting bundle).
   - Layers: `import {ScatterplotLayer} from '@deck.gl/layers'`.
2. **Use the smallest package scope possible**. If a layer lives in `@deck.gl/layers`, do not import it from `deck.gl`.
3. **Prop names and types must be exact**. When in doubt, look them up in the reference file bundled with the relevant sub-skill.
4. **Include a working example**, not just fragments. Show the data format expected.
5. **If a base map is involved**, show the correct pairing: e.g. `MapView` + `MapController` for MapLibre, or the appropriate overlay class for Google/ArcGIS.
6. **Do not invent events** for layers; use `onHover`, `onClick`, `onDrag`, `onDataLoad`, `onError`, etc. exactly as documented.
7. **TypeScript**: include proper generic types when the user uses TS. Use `import type` where appropriate.
8. **Explain why**: briefly note why you chose a layer or pattern.

## Reference docs

- `references/getting-started-and-guides.md` — getting started and developer guides.
- `references/performance-tips-webgpu.md` — performance optimization, tips and tricks, WebGPU support.

For performance or WebGPU questions, prefer `deckgl-core` but read `references/performance-tips-webgpu.md` first.

## Output format

- Short intro (1-2 sentences).
- Full code block(s).
- Bulleted note of key props, data expectations, or common pitfalls.
- If delegating, state which sub-skill is handling the request.
