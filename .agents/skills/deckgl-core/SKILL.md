---
name: deckgl-core
description: |
  Work with deck.gl core concepts: initializing Deck/DeckGL, choosing Views and Controllers, camera state, animations/transitions, effects (lighting, post-process), Extensions, JSON configuration, data loading strategies, performance optimization, tips and tricks, and WebGPU. Use when the user asks about deck.gl views, controllers, initialViewState, transitions, lighting, extensions like DataFilterExtension or CollisionFilterExtension, JSONConverter, performance tuning, large datasets, binary data, WebGPU, or overall deck.gl app architecture.
compatibility: |
  Requires code-generation tools. No runtime dependency.
---

# deck.gl core skill

You handle the deck.gl core API: `Deck`, `DeckGL`, views, controllers, effects, transitions, extensions, JSON config, and data/performance.

## Reference

- `references/core-and-submodules.md` — exact props, methods, classes.
- `references/performance-tips-webgpu.md` — performance optimization, tips and tricks, WebGPU support.

Read the performance reference whenever the user asks about slow rendering, large datasets, binary data, WebGPU, or mobile optimization.

## Initializing a standalone deck.gl app

```js
import {Deck} from '@deck.gl/core';
import {ScatterplotLayer} from '@deck.gl/layers';

new Deck({
  canvas: document.getElementById('deck-canvas'),
  initialViewState: {
    longitude: -122.4,
    latitude: 37.7,
    zoom: 11,
    pitch: 30,
    bearing: 0
  },
  controller: true,
  layers: [new ScatterplotLayer({id: 'points', data, getPosition: d => d.coordinates})]
});
```

## Views and controllers

- Single map view: default `MapView` + `MapController`.
- Multiple views: pass `views` array and match view ids with layer `viewportIds`.
- Available views: `MapView`, `GlobeView`, `OrbitView`, `OrthographicView`, `FirstPersonView`.
- Controllers are paired: `MapController`, `GlobeController`, `OrbitController`, etc.

## View state

- `initialViewState` lets the controller own the state.
- `viewState` makes it controlled; provide `onViewStateChange` to update it.

## Effects

```js
import {LightingEffect, AmbientLight, PointLight} from '@deck.gl/core';
const lightingEffect = new LightingEffect([
  new AmbientLight({color: [255,255,255], intensity: 1.0}),
  new PointLight({color: [255,255,255], intensity: 0.8, position: [1,1,1]})
]);
// pass effects: [lightingEffect] to DeckGL
```

## Extensions

```js
import {DataFilterExtension} from '@deck.gl/extensions';
new ScatterplotLayer({
  data,
  extensions: [new DataFilterExtension({filterSize: 1})],
  getFilterValue: d => d.value,
  filterRange: [0, 100]
});
```

Common extensions: `BrushingExtension`, `DataFilterExtension`, `ClipExtension`, `CollisionFilterExtension`, `FillStyleExtension`, `MaskExtension`, `PathStyleExtension`, `TerrainExtension`, `FP64Extension`.

## JSON

`JSONConverter` converts JSON objects to deck.gl classes. Use for dashboards or saved configurations.

## Performance, tips and tricks, WebGPU

For detailed guidance, read `references/performance-tips-webgpu.md`. Key takeaways:

- Minimize layer updates: keep the same `data` object across renders; use `updateTriggers` to invalidate only the accessors that changed.
- Use `useMemo` in React to avoid recreating data/filtered arrays on every render.
- For incremental loading, use async iterables or split data into multiple layers with stable, unique `id`s.
- Toggle layers with `visible: false` instead of removing them from the `layers` array.
- Prefer constant accessors (`getFillColor: [255,0,0]`) over functions when the value is uniform.
- Use `radiusScale`, `opacity`, and similar `*Scale` props instead of accessor functions driven by animations.
- For very large data, use binary data, `data.attributes`, aggregation layers, or tile layers.
- Deck.gl supports rendering millions of points; watch memory limits (~1 GB allocation cap) and picking limits (16 M items per layer, 256 pickable layers).
- WebGPU support is experimental; some extensions/layers may not yet work. Prefer WebGL unless the user explicitly asks for WebGPU.

## Output

- Provide a complete Deck/DeckGL setup with the requested core feature.
- Show where to pass views, controllers, effects, extensions, or JSON config.
