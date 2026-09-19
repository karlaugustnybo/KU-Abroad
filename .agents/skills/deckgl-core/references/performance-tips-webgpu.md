# Performance Optimization, Tips & Tricks, and WebGPU Reference

## Performance Optimization

### General Expectations

- Most basic layers like `ScatterplotLayer` render at 60 FPS on 2015 dual-GPU MacBook Pros up to about **1 million** data items during pan/zoom.
- Frame rates drop into the **10–20 FPS** range as data approaches **10 million** items.
- Browser memory limits cap contiguous allocations (Chrome ~1 GB); layers usually crash during GPU buffer generation between **10M and 100M** items. Work around this by chunking data across multiple layers.
- Modern phones render surprisingly well but are very sensitive to memory pressure, and load data slower than desktops.

### Minimize Data Changes

- Layer update time is proportional to item count. Recalculating all GPU buffers is the most expensive layer operation and can take seconds for multi-million-item layers; frequent updates cause stutter even with thousands of items.
- Avoid creating a new `data` array on every render. deck.gl does a shallow comparison; pass the same object when nothing has changed, or use the `dataComparator` prop for custom equality.

**Bad practice** — `filter` creates a new array each render:
```ts
new ScatterplotLayer({
  data: DATA.filter(d => d.time >= settings.minTime && d.time <= settings.maxTime),
  getPosition: d => d.position,
  getRadius: settings.radius
})
```

**Good practice (TypeScript)** — cache the filtered result:
```ts
let filteredData: DataType[];
let lastSettings: Settings;

function render(settings: Settings) {
  if (!lastSettings ||
      settings.minTime !== lastSettings.minTime ||
      settings.maxTime !== lastSettings.maxTime) {
    filteredData = DATA.filter(d =>
      d.time >= settings.minTime && d.time <= settings.maxTime
    );
  }
  lastSettings = settings;

  new ScatterplotLayer({
    data: filteredData,
    getPosition: d => d.position,
    getRadius: settings.radius
  });
}
```

**Good practice (React)** — use `useMemo` with stable dependencies:
```tsx
const filteredData = React.useMemo(() => {
  return DATA.filter(d =>
    d.time >= settings.minTime && d.time <= settings.maxTime
  );
}, [settings.minTime, settings.maxTime]);

new ScatterplotLayer({
  data: filteredData,
  getPosition: d => d.position,
  getRadius: settings.radius
});
```

### Use updateTriggers

- Changing `data` recalculates *all* buffers. When only some fields change, keep `data` stable and use `updateTriggers` to invalidate selected attributes.

**Bad practice** — reconstructing `data` per year just to update radius:
```ts
new ScatterplotLayer({
  data: DATA.map(d => ({
    centroid: d.centroid,
    population: d.populationsByYear[year]
  })),
  getPosition: d => d.centroid,
  getRadius: d => Math.sqrt(d.population)
})
```

**Good practice** — stable `data`, radius invalidated via `updateTriggers`:
```ts
new ScatterplotLayer({
  data: DATA,
  getPosition: d => d.centroid,
  getRadius: d => Math.sqrt(d.populationsByYear[year]),
  updateTriggers: {
    getRadius: year
  }
})
```

### Incremental / Async Data Loading

- Appending a new chunk to an existing array forces the layer to regenerate buffers for all rows.
- Prefer one layer per chunk with stable, unique `id`s so only the new chunk's layer updates.
- Since v7.2.0, async iterables let a single layer update only the sub-buffer for new rows.

**Bad practice** — concatenating into one array each chunk:
```ts
let loadedData: DataType[] = [];
while (chunk = await fetchNextChunk()) {
  loadedData = loadedData.concat(chunk);
}

new ScatterplotLayer({
  id: 'points',
  data: loadedData,
  getPosition: d => d.position
})
```

**Good practice** — one layer per chunk:
```ts
const layers = dataChunks.map((chunk, chunkIndex) =>
  new ScatterplotLayer({
    id: `points-${chunkIndex}`,
    data: chunk,
    getPosition: d => d.position
  })
);
```

**Good alternative** — async iterable:
```ts
async function* getData() {
  while (chunk = await fetchNextChunk()) {
    yield chunk;
  }
}

new ScatterplotLayer({
  id: 'points',
  data: getData(),
  getPosition: d => d.position
})
```

### Favor `visible` Over Adding/Removing Layers

- Removing a layer discards its internal buffers; re-adding rebuilds them. Use the `visible` prop to toggle display instantly.

**Bad practice**:
```ts
[
  layerVisibility.circles && new ScatterplotLayer({ id: 'circles' /* ... */ }),
  layerVisibility.labels && new TextLayer({ id: 'labels' /* ... */ })
]
```

**Good practice**:
```ts
[
  new ScatterplotLayer({ id: 'circles', visible: layerVisibility.circles /* ... */ }),
  new TextLayer({ id: 'labels', visible: layerVisibility.labels /* ... */ })
]
```

### Accessor Optimization

- 99% of buffer-update CPU time is spent in accessors, so cost is multiplied by data size.
- Favor constant values over callbacks:
  - `getFillColor: [255, 0, 0, 128]` uploads 4 numbers.
  - `getFillColor: () => [255, 0, 0, 128]` builds a `4 × data.length` typed array and calls the function `data.length` times.
- Use `*Scale` uniform props for global multipliers instead of per-object accessors in animations.

**Bad practice** — per-object scaling on every frame:
```ts
new ScatterplotLayer({
  data,
  getRadius: d => d.size * radius,
  updateTriggers: { getRadius: radius }
})
```

**Good practice** — uniform scale, smooth 60 FPS:
```ts
new ScatterplotLayer({
  data,
  getRadius: d => d.size,
  radiusScale: radius
})
```

- Make accessors trivial and reuse precomputed / constant values.

**Bad practice** — repeated heavy computation and new-array creation per object:
```ts
new ScatterplotLayer({
  data: DATA,
  getPosition: d => d.centroid,
  getFillColor: d => {
    const maxPopulation = Math.max.apply(null, Object.values(d.populationsByYear));
    if (maxPopulation > 1000000) return [255, 0, 0];
    if (maxPopulation > 100000) return [0, 255, 0];
    return [0, 0, 255];
  },
  getRadius: d => {
    const maxPopulation = Math.max.apply(null, Object.values(d.populationsByYear));
    return Math.sqrt(maxPopulation);
  }
})
```

**Good practice** — precompute once and index into cached values:
```ts
const maxPopulations = DATA.map(precomputeMaxPopulation);
const COLORS = {
  ONE_MILLION: [255, 0, 0],
  HUNDRED_THOUSAND: [0, 255, 0],
  OTHER: [0, 0, 255]
};

new ScatterplotLayer({
  data: DATA,
  getPosition: d => d.centroid,
  getFillColor: (d, {index}) => {
    const maxPopulation = maxPopulations[index];
    if (maxPopulation > 1000000) return COLORS.ONE_MILLION;
    if (maxPopulation > 100000) return COLORS.HUNDRED_THOUSAND;
    return COLORS.OTHER;
  },
  getRadius: (d, {index}) => Math.sqrt(maxPopulations[index])
})
```

### Binary Data

- Avoid repacking binary data into classic JS arrays; it wastes CPU and memory.
- Pass a non-iterable object with a `length` field; accessors receive `index`, `data`, and optional `target` instead of an object.

**Bad practice** — unpacking a typed array into objects:
```ts
const data: DataType[] = [];
for (let i = 0; i < binaryData.length; i += 6) {
  data.push({
    position: [binaryData[i], binaryData[i + 1]],
    radius: binaryData[i + 2],
    color: [binaryData[i + 3], binaryData[i + 4], binaryData[i + 5]]
  });
}

new ScatterplotLayer({
  data,
  getPosition: d => d.position,
  getRadius: d => d.radius,
  getFillColor: d => d.color
})
```

**Good practice** — read directly from the binary buffer:
```ts
const DATA = { src: binaryData, length: binaryData.length / 6 };

new ScatterplotLayer({
  data: DATA,
  getPosition: (_, {index, data}) =>
    data.src.subarray(index * 6, index * 6 + 2),
  getRadius: (_, {index, data}) =>
    data.src[index * 6 + 2],
  getFillColor: (_, {index, data}) =>
    data.src.subarray(index * 6 + 3, index * 6 + 6)
})
```

**Good alternative** — write into the provided `target` array to avoid allocations:
```ts
getPosition: (_, {index, data, target}) => {
  target[0] = data.src[index * 6];
  target[1] = data.src[index * 6 + 1];
  target[2] = 0;
  return target;
}
```

### External Attributes

- For maximum throughput, precompute attribute buffers (in a worker or server) and bypass CPU accessors.
- Pass buffers as `data.attributes.<accessorName>` with `value` (typed array) or `buffer` (luma.gl Buffer).
- External attributes work with primitive layers, not composite layers. Variable-width layers such as `PathLayer` and `SolidPolygonLayer` need extra metadata.

Example with typed arrays:
```ts
new PointCloudLayer({
  data: {
    length: pointCount,
    attributes: {
      getPosition: { value: data.positions, size: 3 },
      getColor: { value: data.colors, size: 3 }
    }
  },
  getNormal: [0, 0, 1]
})
```

Example with a single interleaved buffer:
```ts
const buffer = deckInstance.device.createBuffer({ data: data.positionsAndColors });

new PointCloudLayer({
  data: {
    length: data.pointCount,
    attributes: {
      getPosition: { buffer, size: 3, offset: 0, stride: 24 },
      getColor: { buffer, size: 3, offset: 12, stride: 24 }
    }
  },
  getNormal: [0, 0, 1]
})
```

### Rendering Performance

- Rendering time is proportional to vertex shader invocations (data item count) and fragment shader invocations (pixels drawn).
- Overdraw can dominate: a 5-pixel radius produces ~100 pixels per point; 10M points can generate ~1B fragment invocations per frame.
- Rule of thumb: keep point radii small or use aggregation for dense data.

### Picking Performance

- Picking draws the layer to an off-screen buffer; performance tracks visual rendering.
- **Limits**: picking distinguishes at most **16,777,216 (16M) items per layer** and supports at most **256 pickable layers**.

### Number of Layers

- Typical advanced apps use ~100 deck.gl layers without issues; a few hundred is possible.
- deck.gl was not designed for thousands of layers.

### Common Performance Issues

- Disable Retina/High DPI if not needed: `useDevicePixels` renders 4× the fragments by default.
- Do not enable luma.gl debug mode in production (queries GPU error state after each operation).
- Keep `pickable: false` on layers that do not need picking; picking has a small overhead.

---

## Tips and Tricks

### Per-Layer GPU Parameters

Use the `parameters` prop to control GPU state such as depth testing and blending:

```js
new ScatterplotLayer({
  parameters: {
    depthCompare: 'always'
  }
})
```

### Z-Fighting and Depth Testing

- Z-fighting occurs when multiple objects share the same depth; the z-buffer cannot resolve ordering reliably.
- If you are not using 3D extrusions, disable depth testing globally or per-layer:

```js
new SomeLayer({
  parameters: {
    depthCompare: 'always'
  }
})
```

- For z-fighting *between* layers, use the `polygonOffset` prop instead.

### Browser Blending Modes

- deck.gl renders in a transparent overlay div, so browser CSS compositing affects final appearance.
- Use `mix-blend-mode: multiply` on the canvas to darken overlays while preserving underlying map legends:

```css
.overlays canvas {
  mix-blend-mode: multiply;
}
```

- To prevent `mix-blend-mode` from affecting sibling elements, isolate the DeckGL parent:

```css
.deckgl-parent-class {
  isolation: 'isolate';
}
```

### Mobile CSS / JS Guards

- Disable browser touch UI behaviors on the root element and canvas:

```css
#deck-root,
#deck-root canvas {
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  -webkit-tap-highlight-color: transparent;
}
```

- For iOS embeds, prevent native callouts on canvas while preserving pointer events:

```js
const root = document.getElementById('deck-root');
const preventCanvasBrowserUI = event => {
  if (event.target instanceof HTMLCanvasElement) {
    event.preventDefault();
  }
};

for (const type of ['contextmenu', 'selectstart', 'gesturestart', 'gesturechange', 'gestureend']) {
  root.addEventListener(type, preventCanvasBrowserUI, { passive: false });
}
```

### Experimental Memory Controls

The `Deck` class exposes experimental props to reduce memory on restricted devices:

- `_pickable`
- `_typedArrayManagerProps`

Example trade-off:

```js
new Deck({
  _pickable: false,
  _typedArrayManagerProps: isMobile ? { overAlloc: 1, poolSize: 0 } : null
})
```

---

## WebGPU

### Status

- WebGPU support in deck.gl v9 is **work in progress and not production ready**.
- Support is landing layer by layer and feature by feature.

Legend:

- ✅ explicit WebGPU/WGSL implementation exists or is a thin wrapper.
- 🚧 some paths work, but the full API surface is not ported.
- ❌ no in-tree WebGPU implementation yet.

### How to Enable

Configure luma.gl to use the `webgpuAdapter` via `deviceProps`:

```ts
import { webgpuAdapter } from '@luma.gl/webgpu';

new Deck({
  deviceProps: {
    type: 'webgpu',
    adapters: [webgpuAdapter]
  }
});
```

### Layer Support

| Module | Layer | WebGL | WebGPU |
| --- | --- | --- | --- |
| `@deck.gl/layers` | `ArcLayer` | ✅ | ❌ |
| `@deck.gl/layers` | `BitmapLayer` | ✅ | ❌ |
| `@deck.gl/layers` | `IconLayer` | ✅ | ✅ |
| `@deck.gl/layers` | `LineLayer` | ✅ | ✅ |
| `@deck.gl/layers` | `PointCloudLayer` | ✅ | ✅ |
| `@deck.gl/layers` | `ScatterplotLayer` | ✅ | ✅ |
| `@deck.gl/layers` | `ColumnLayer` | ✅ | ❌ |
| `@deck.gl/layers` | `GridCellLayer` | ✅ | ❌ |
| `@deck.gl/layers` | `PathLayer` | ✅ | ✅ |
| `@deck.gl/layers` | `PolygonLayer` | ✅ | ❌ |
| `@deck.gl/layers` | `GeoJsonLayer` | ✅ | ❌ |
| `@deck.gl/layers` | `TextLayer` | ✅ | ❌ |
| `@deck.gl/layers` | `SolidPolygonLayer` | ✅ | ❌ |
| `@deck.gl/aggregation-layers` | `ScreenGridLayer`, `HexagonLayer`, `ContourLayer`, `GridLayer`, `HeatmapLayer` | ✅ | ❌ |
| `@deck.gl/mesh-layers` | `SimpleMeshLayer`, `ScenegraphLayer` | ✅ | ❌ |
| `@deck.gl/geo-layers` | `A5Layer`, `GreatCircleLayer`, `S2Layer`, `QuadkeyLayer`, `TileLayer`, `TripsLayer`, `H3ClusterLayer`, `H3HexagonLayer`, `Tile3DLayer`, `TerrainLayer`, `MVTLayer`, `GeohashLayer` | ✅ | ❌ |
| `@deck.gl/carto` | `ClusterTileLayer`, `H3TileLayer`, `HeatmapTileLayer`, `PointLabelLayer`, `QuadbinTileLayer`, `RasterTileLayer`, `VectorTileLayer` | ✅ | ❌ |

### Extensions

All extensions in `@deck.gl/extensions` remain WebGL-only:

| Extension | WebGL | WebGPU |
| --- | --- | --- |
| `BrushingExtension` | ✅ | ❌ |
| `DataFilterExtension` | ✅ | ❌ |
| `Fp64Extension` | ✅ | ❌ |
| `PathStyleExtension` | ✅ | ❌ |
| `FillStyleExtension` | ✅ | ❌ |
| `ClipExtension` | ✅ | ❌ |
| `CollisionFilterExtension` | ✅ | ❌ |
| `MaskExtension` | ✅ | ❌ |

### Effects

| Effect | WebGL | WebGPU | Notes |
| --- | --- | --- | --- |
| `LightingEffect` | ✅ | 🚧 | Material lighting modules ported to WGSL; shadow path still GLSL-only. |
| `PostProcessEffect` | ✅ | ❌ | Screen-pass chain is generated from GLSL fragment shader templates. |

### Feature Gaps

| Feature | Status | Comment |
| --- | --- | --- |
| Views | 🚧 | Core `project` / `project32` WGSL ports exist; standard view/projection work. |
| Picking | ❌ | `Deck` skips picking entirely on WebGPU. |
| Shader hooks / layer extensions | ❌ | WGSL shader hook list is empty; injection-based extensions not portable. |
| GPU transforms | 🚧 | Underlying APIs evolving; transform-gated tests remain. |
| Constant attributes | 🚧 | `AttributeManager` materializes constants into full buffers as a compatibility path. |
| Attribute transitions | 🚧 | Some layers disable transitions; utilities still use WebGL-specific buffer reads. |
| Base map overlays | ❌ | Premultiplied-alpha work still needed across deck and base map stack. |
| Base map interleaving | ❌ | No base map integration path supports WebGPU interleaving. |

### Practical Rules of Thumb

- Treat WebGPU support as experimental and expect crashes for unsupported layers/effects.
- Prefer `ScatterplotLayer`, `LineLayer`, `PointCloudLayer`, `IconLayer`, and `PathLayer` when testing under WebGPU.
- Avoid picking, extensions, and post-processing when running on WebGPU.
- Keep data updates infrequent and buffer sizes under GPU memory limits; WebGPU is no shortcut around the same memory rules that apply to WebGL.
