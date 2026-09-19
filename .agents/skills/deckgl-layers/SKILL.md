---
name: deckgl-layers
description: |
  Generate deck.gl layer code, choose the right layer for geospatial or abstract data, and configure layer props/accessors/events correctly. Use whenever the user asks about deck.gl layers such as ScatterplotLayer, GeoJsonLayer, HeatmapLayer, TileLayer, ArcLayer, TextLayer, PathLayer, PolygonLayer, ScenegraphLayer, or any @deck.gl/layers/@deck.gl/geo-layers/@deck.gl/aggregation-layers/@deck.gl/mesh-layers class. Also use to map data columns to accessors, set color/radius/elevation, or handle picking and data loading.
compatibility: |
  Requires code-generation tools. No runtime dependency.
---

# deck.gl layers skill

You generate deck.gl layer code. You know every built-in layer class, its package, props, accessors, and events from `references/layers.md`.

## How to respond

1. **Identify the user's data and visualization goal.** Ask only if essential; otherwise infer from the prompt.
2. **Pick the layer(s).** Prefer the smallest set of layers that express the visualization. Combine layers when needed (e.g. `GeoJsonLayer` for polygons + `TextLayer` for labels).
3. **Look up exact class name and package** in `references/layers.md`. Do not guess.
4. **Write a complete, runnable example** with imports, sample data, layer configuration, and a `Deck`/`DeckGL` wrapper.
5. **Use exact prop names**. Accessor functions are called with one feature/element and can return values or arrays.

## Import style

Use named imports in v9.

- Layers: `import {ScatterplotLayer} from '@deck.gl/layers'`
- Geo layers: `import {TileLayer} from '@deck.gl/geo-layers'`
- Aggregation layers: `import {HeatmapLayer} from '@deck.gl/aggregation-layers'`
- Mesh layers: `import {ScenegraphLayer} from '@deck.gl/mesh-layers'`
- React wrapper: `import {DeckGL} from '@deck.gl/react'`
- Standalone core: `import {Deck} from '@deck.gl/core'`
- Extensions: `import {DataFilterExtension} from '@deck.gl/extensions'`

## Data conventions

- GeoJSON layers accept `FeatureCollection`.
- Most layers accept an array of objects via `data`.
- Accessors can be a string field name or a function `(object) => value`.
- For binary data mention `data.attributes`.

## Events

Standard layer callbacks: `onHover`, `onClick`, `onDrag`, `onDragStart`, `onDragEnd`, `onDataLoad`, `onError`, `onTileError`, etc. The event object contains `object`, `coordinate`, `index` when an object is picked.

## Common gotchas

- `getPosition` accessor defaults to `[object.lng, object.lat]` for geo layers.
- `getColor` accepts `[r, g, b, a]` arrays where each channel is 0–255.
- `getElevation` and `getRadius` are in meters by default for geo layers.
- `transitions` object animates when prop values change (e.g. `transitions: {getFillColor: 500}`).
- When using `GeoJsonLayer`, set `stroked`, `filled`, `extruded`, and `wireframe` booleans explicitly.
- For performance-sensitive layers, read `references/performance-tips-webgpu.md`. Prefer stable `data` objects, `updateTriggers`, `*Scale` props, and `visible` toggles over removing layers.

## Output

- Short recommendation text.
- Full runnable layer example(s).
- A **tips** block covering the most likely pitfalls for the chosen layer(s).
