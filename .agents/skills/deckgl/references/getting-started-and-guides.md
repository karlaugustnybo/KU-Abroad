# deck.gl Structured Reference — Getting Started & Developer Guide

Compiled from `/var/folders/vq/zz5zmfk13pg6hzq4y94xjdtr0000gn/T/opencode/deck.gl/docs/get-started/*`, `/developer-guide/*` (excluding `custom-layers/` deep tree), `faq.md`, `roadmap.md`, `upgrade-guide.md`, and `CONTRIBUTING.md`.

---

## Getting Started

### Installation

- **Single meta package**: `npm install deck.gl` / `yarn add deck.gl`.
  - Includes all features except `@deck.gl/test-utils`.
  - Tree-shaking supported (Webpack/Rollup exclude unused exports).
- **Selective install** (manual version sync required):
  - Core/gfx: `@deck.gl/core`
  - Primitives: `@deck.gl/layers`
  - Aggregations: `@deck.gl/aggregation-layers`
  - Geospatial formats/tiles: `@deck.gl/geo-layers`
  - 3D meshes/scenegraphs: `@deck.gl/mesh-layers`
  - JSON declarative API: `@deck.gl/json`
  - Mapbox integration: `@deck.gl/mapbox`
  - React wrapper: `@deck.gl/react`
  - UI widgets: `@deck.gl/widgets`
  - Testing: `@deck.gl/test-utils`
- **Examples**: clone repo, checkout `8.0-release` (or `master` for latest unreleased), `cd examples/get-started/pure-js/basic`, `npm install`, `npm start`.
  - Mapbox examples need `MapboxAccessToken` env var.
  - `npm run start-local` builds example against local deck.gl source after running `npm install` at repo root.

### Standalone (Pure JS / Scripting)

- `@deck.gl/core` has no React/Mapbox/MapLibre dependency.
- ES module:
  ```js
  import {Deck} from '@deck.gl/core';
  import {ScatterplotLayer} from '@deck.gl/layers';

  const deckInstance = new Deck({
    initialViewState: {latitude: 37.8, longitude: -122.45, zoom: 15},
    controller: true,
    layers: [
      new ScatterplotLayer({
        data: [{position: [-122.45, 37.8], color: [255, 0, 0], radius: 100}],
        getPosition: d => d.position,
        getFillColor: d => d.color,
        getRadius: d => d.radius
      })
    ]
  });
  ```
- Scripting API (Codepen/JSFiddle/Observable):
  - `<script src="https://unpkg.com/deck.gl@latest/dist.min.js"></script>`
  - Exposes globals `deck` and `luma`; classes as `deck.<Class>`.
  - `DeckGL` scripting class extends core `Deck` and adds Mapbox/MapLibre integration.
  - Mapbox script/CSS: `https://api.mapbox.com/mapbox-gl-js/v3.2.0/mapbox-gl.js` + css
  - MapLibre script/CSS: `https://unpkg.com/maplibre-gl@3.0.0/dist/maplibre-gl.js` + css
  - Example:
    ```js
    const {DeckGL, ScatterplotLayer} = deck;
    new DeckGL({
      mapboxApiAccessToken: '<mapbox-access-token>',
      mapStyle: 'mapbox://styles/mapbox/light-v9',
      initialViewState: {...},
      controller: true,
      layers: [...]
    });
    ```

### React

- Import: `import {DeckGL} from '@deck.gl/react';`
- Render layers as prop:
  ```tsx
  import {DeckGL} from '@deck.gl/react';
  import {MapViewState} from '@deck.gl/core';
  import {LineLayer} from '@deck.gl/layers';

  const INITIAL_VIEW_STATE: MapViewState = {longitude: -122.41669, latitude: 37.7853, zoom: 13};

  function App() {
    const layers = [
      new LineLayer<DataType>({id: 'line-layer', data: '/path/to/data.json', getSourcePosition: d => d.from, getTargetPosition: d => d.to})
    ];
    return <DeckGL initialViewState={INITIAL_VIEW_STATE} controller layers={layers} />;
  }
  ```
- JSX layers/views/widgets as children (React-like style, no perf advantage):
  ```tsx
  <DeckGL initialViewState={INITIAL_VIEW_STATE} controller>
    <LineLayer id="line-layer" data="/path/to/data.json" getSourcePosition={d => d.from} getTargetPosition={d => d.to} />
    <MapView id="map" width="50%" controller><Map mapStyle="mapbox://..."/></MapView>
    <FirstPersonView width="50%" x="50%" fovy={50} />
    <ZoomWidget/>
  </DeckGL>
  ```
- Base-map companions:
  - `react-map-gl` for Mapbox GL JS / MapLibre GL JS.
  - `@vis.gl/react-google-maps` for Google Maps JavaScript API.
- Performance:
  - Avoid expensive React state updates inside `onHover`, `onViewStateChange`, etc.; use `useMemo` for layers where possible.
  - Recreating layer instances on each render is cheap; deck.gl diffs internally.
- SSR (Next.js/Gatsby):
  - v9 is ESM-compliant and supports `import` and `require()`.
  - SSR may fail because upstream deps like `d3` are ESM-only.
  - Mitigations: add `"type": "module"` to package.json, or dynamically import with `ssr: false`:
    ```tsx
    const Map = dynamic(() => import('../components/map'), {ssr: false});
    ```

### TypeScript

- **v9+**: official types at package roots.
  ```ts
  import {DeckGL} from '@deck.gl/react';
  import type {DeckGLRef} from '@deck.gl/react';
  import type {GeoJsonLayerProps} from '@deck.gl/layers';
  ```
- **v8.8–v8.9**: opt-in via `/typed` entry points.
  ```ts
  import DeckGL from '@deck.gl/react/typed';
  import type {GeoJsonLayerProps} from '@deck.gl/layers/typed';
  ```
- **pre-v8.8**: install `@danmarshall/deckgl-typings@^3.0.0` etc., declare module `deck.gl`.

### Map Integration

- Integration modes:
  - **Overlaid**: separate Deck canvas on top of base map; cameras synchronized.
  - **Interleaved**: Deck renders into base map's WebGL2 context, enabling occlusion with labels/3D features.
    - Deck cannot render into WebGL1; verify base map supports WebGL2.
- Library support grid:
  - **Mapbox GL JS**: Pure JS, React, Overlaid, Interleaved (`@deck.gl/mapbox` / `MapboxOverlay`).
  - **MapLibre GL JS**: Pure JS, React, Overlaid, Interleaved (`@deck.gl/mapbox` / `MapboxOverlay`; uses maplibre-gl imports).
  - **Google Maps Platform**: Pure JS, React, Overlaid, Interleaved (`@deck.gl/google-maps` / `GoogleMapsOverlay`).
  - **ArcGIS**: Pure JS, React, Interleaved (`@deck.gl/arcgis` / `DeckLayer`).
  - **Leaflet / OpenLayers / harp.gl / Apple Maps**: Overlaid only.
- Mapbox example:
  ```ts
  import {MapboxOverlay} from '@deck.gl/mapbox';
  import mapboxgl from 'mapbox-gl';

  const map = new mapboxgl.Map({container: 'map', style: 'mapbox://styles/mapbox/light-v9', accessToken: '<token>', center: [0.45, 51.47], zoom: 11});
  map.once('load', () => {
    map.addControl(new MapboxOverlay({interleaved: true, layers: [...]}));
  });
  ```
  - Interleaved requires `mapbox-gl@>2.13`; MapLibre interleaved requires `maplibre-gl@>3`.
- MapLibre React (`react-map-gl/maplibre`):
  - Use `useControl(() => new MapboxOverlay(props))`.
- Google Maps React (`@vis.gl/react-google-maps`):
  ```tsx
  import {GoogleMapsOverlay} from '@deck.gl/google-maps';
  function DeckGLOverlay(props: DeckProps) {
    const map = useMap();
    const overlay = useMemo(() => new GoogleMapsOverlay(props), []);
    useEffect(() => { overlay.setMap(map); return () => overlay.setMap(null); }, [map]);
    overlay.setProps(props);
    return null;
  }
  ```
  - Google Maps vector map ID required for interleaved mode.
- Reverse-controlled (DeckGL owns camera):
  - React with Mapbox: `<DeckGL ...><Map .../></DeckGL>`.
  - React with Google Maps: `<APIProvider><DeckGL ...><Map mapId="..."/></DeckGL></APIProvider>`.
  - Use `@deck.gl/widgets` instead of base-map controls.

---

## Developer Guide

### Using Layers

- Layer construction:
  - Constructor takes a single props object.
  - **Required/typical props**:
    - `id` (string): unique identifier; use explicit id to avoid collisions. Deck.gl matches layers across renders by `id`.
    - `data` (array | Map | Set | length object | Promise | URL): source.
    - `visible` (boolean): cheap visibility toggle; default true.
    - `pickable` (boolean | `'3d'`): enables picking; default false.
    - `opacity` (number): default 1.
    - `coordinateSystem` (string): one of `'lnglat'`, `'meter-offsets'`, `'lnglat-offsets'`, `'cartesian'`.
    - `coordinateOrigin` ([lon, lat, alt] | [x, y, z]):
      - Required for `'meter-offsets'` / `'lnglat-offsets'`.
      - Optional for `'cartesian'`; default `[0,0,0]`.
    - `modelMatrix` (number[16]): 4x4 transform; best for cartesian/meter-offsets.
    - `updateTriggers` (object): force accessor re-evaluation.
    - `transitions` (object or number): animate props.
    - `parameters` (object): GPU state overrides.
    - `loaders`, `loadOptions`: data and resource loading options.
- **Accessors** (props starting with `get`):
  - Signature: `(object, objectInfo) => value`.
  - `objectInfo.index`, `objectInfo.data`, `objectInfo.target` (preallocated array).
  - If `data` is non-iterable, `object` is `null`; use `index`/`data.src` to read binary.
  - Constants are allowed and much faster than functions.
- Reactively update layers by creating new instances with the same `id`.
  ```js
  deckInstance.setProps({layers: [new ScatterplotLayer({id: 'circles', data: newData, ...})]});
  ```
- Update semantics:
  - Creating new layer instances is cheap; deck.gl diffs and reuses internal state.
  - Props are shallow-compared.
  - Accessor functions are **not** compared by identity for attribute updates; rely on `updateTriggers` to tell deck.gl to recompute.
  - Changing `data` rebuilds all GPU buffers.

### Interactivity — Picking Events

- Enable camera controller:
  ```js
  new Deck({initialViewState: {...}, controller: true});      // or {doubleClickZoom: false, touchRotate: true}
  ```
- Built-in layer event handlers:
  - `onHover(info, event)`, `onClick(info, event)`, `onDragStart`, `onDrag`, `onDragEnd`.
  - Registered per layer (on the layer itself) or globally on `Deck`/`DeckGL`.
  - Layer handler is called first; if it returns truthy, event is consumed; otherwise bubbles to Deck canvas.
- Global event callbacks on `Deck`/`DeckGL`:
  - `onHover`, `onClick`, `onDragStart`, `onDrag`, `onDragEnd`.
- `pickable` prop on a layer enables picking.
- `PickingInfo` fields:
  - `picked` (boolean)
  - `index` (number)
  - `layer` (top-level layer)
  - `sourceLayer` (immediate sub-layer)
  - `object` (data element; may be null)
  - `x`, `y` (viewport-relative mouse position)
  - `coordinate` ([lon, lat, z=0]); set `pickable: '3d'` or use direct picking with `unproject3D: true` for 3D.
  - `viewport` (possibly misidentified if overlapping views do not clear background)
- Picking limits:
  - 255 layers, 16M objects per layer.
  - Offscreen objects cannot be picked via built-in engine.
- Built-in tooltip:
  - `Deck` prop `getTooltip(info)` returning string or `{html, style}`.
- Custom tooltip: build DOM/React element from `info.x`, `info.y`, `info.object`.
- Direct picking API:
  ```ts
  const pickInfo = await deckInstance.pickObjectAsync({x, y, radius: 1});
  const pickInfos = await deckInstance.pickObjectsAsync({x, y, width, height, ...}); // not fully detailed here
  ```
- Camera reset example:
  ```js
  import {FlyToInterpolator} from '@deck.gl/core';
  deckInstance.setProps({
    initialViewState: {
      longitude: -122.4, latitude: 37.8, zoom: 10,
      transitionInterpolator: new FlyToInterpolator({speed: 2}),
      transitionDuration: 'auto'
    }
  });
  ```
- External view state (stateless mode):
  ```js
  new Deck({
    viewState: {...},
    controller: true,
    onViewStateChange: ({viewState}) => deckInstance.setProps({viewState})
  });
  ```
  - Do not combine `initialViewState` and `viewState`; `viewState` wins.

### Coordinate Systems

- Default:
  - `'lnglat'` in geospatial views (`MapView`, `GlobeView`).
  - `'cartesian'` in non-geospatial views (`OrbitView`, `OrthographicView`).
- Systems:
  - `coordinateSystem: 'lnglat'`: positions `[longitude, latitude, altitude]`; origin ignored.
  - `coordinateSystem: 'meter-offsets'`: positions `[Δx, Δy, Δz]` meters from `coordinateOrigin`; map-east x, map-north y, up z; geospatial views only.
  - `coordinateSystem: 'lnglat-offsets'`: positions `[Δlon, Δlat, Δalt]` degrees from origin; geospatial views only.
  - `coordinateSystem: 'cartesian'`: positions `[x, y, z]`; linear, uniform units.
- Dimension units (`*Units` props such as `radiusUnits`, `widthUnits`, `sizeUnits`):
  - `'meters'`: physical size; useful for real-world dimensions.
  - `'common'`: viewport-zoom-relative; one unit projects to same size independent of latitude; good for abstract values.
  - `'pixels'`: screen pixels; constant on screen; may appear larger near camera in perspective views; focal point 1px == 1 CSS px.
- Conversions:
  - `MapView` / `FirstPersonView`: 512 common units = `C * cos(phi)` meters (C = earth circumference, phi = latitude rad).
  - `GlobeView`: 512 common units = earth diameter.
  - `OrbitView` / `OrthographicView`: 1 meter = 1 common unit.
  - 1 common unit = `2 ** zoom` pixels.
- `modelMatrix` recommended for pre-transforms (scale, rotate, translate) on cartesian/meter-offsets; avoid CPU-side coordinate conversion on large data.
- Limitations:
  - Offset systems (`METER_OFFSETS`, `LNGLAT_OFFSETS`) are linear approximations; use `LNGLAT` for country/continental scales.

### Views and Projections

- View classes exported from `@deck.gl/core`:
  - `MapView` (default): Web Mercator; matches Mapbox/MapLibre/Google base maps.
  - `GlobeView`: 3D globe; experimental.
  - `FirstPersonView`: driver-perspective camera.
  - `OrbitView`: 3D info-vis, rotate around target.
  - `OrthographicView`: 2D info-vis, top-down no rotation.
  - `View`: base class; supply custom matrices.
- Viewport layout props (on `View`): `id`, `x`, `y`, `width`, `height`, `controller`.
  - CSS-style expressions supported: numbers, percentages, `px`, parentheses, `calc(50% - 10px)`.
- Single non-geospatial view:
  ```js
  new Deck({views: new OrthographicView()});
  ```
- Multiple views:
  ```js
  new Deck({
    views: [
      new MapView({id: 'left', x: 0, width: '50%', controller: true}),
      new MapView({id: 'right', x: '50%', width: '50%', controller: true})
    ],
    viewState: {longitude: -122.4, latitude: 37.8, zoom: 12},
    onViewStateChange: ({viewState}) => deckInstance.setProps({viewState})
  });
  ```
- Per-view view states:
  - Provide object keyed by view `id`.
  - Use `view.id` in `onViewStateChange` to selectively synchronize.
- `layerFilter` prop: choose which layers draw/pick per viewport.
  ```js
  layerFilter: ({layer, viewport, isPicking}) => {
    if (viewport.id === 'first-person' && layer.id === 'car') return false;
    if (isPicking && viewport.id === 'minimap') return false;
    return true;
  }
  ```
- Avoid rendering expensive layers (`TileLayer`, `MVTLayer`, `HeatmapLayer`, `ScreenGridLayer`) into multiple views; create separate instances per view and limit with `layerFilter`.
- React-only: auto-position children under views using `viewId` / `viewportId` props on `DeckGL` children.

### Animations and Transitions

- **Camera transitions**: attach to `viewState` / `initialViewState` props:
  - `transitionInterpolator`: `LinearInterpolator` (default), `FlyToInterpolator`, custom `TransitionInterpolator`.
  - `transitionDuration`: ms, or `'auto'` with `FlyToInterpolator`.
  - `transitionEasing`: `(t: number) => number`; default `t => t`.
  - `transitionInterruption`: `TRANSITION_EVENTS.BREAK` (default), `SNAP_TO_END`, `IGNORE`.
  - `onTransitionStart`, `onTransitionInterrupt`, `onTransitionEnd`.
  - Example restrict to `bearing`:
    ```js
    {transitionDuration: 1000, transitionInterpolator: new LinearInterpolator(['bearing']), onTransitionEnd: rotateCamera}
    ```
  - "Set and forget": initial values of duration/interpolator/easing/interruption carry through.
- **Layer prop transitions**:
  - Uniform prop transitions (numbers/number[]) run on CPU.
  - Attribute transitions (`get*`) run on GPU; can be expensive for large data.
  - Configure via `transitions` prop:
    ```js
    new HexagonLayer({
      ..., transitions: {elevationScale: 3000}
    });
    ```
  - Object form:
    - `type`: `'interpolation'` (default) | `'spring'`
    - `enter(value, fromChunk?)`: backfill value for new objects/vertices.
    - `onStart`, `onEnd`, `onInterrupt`
    - Interpolation-only: `duration`, `easing`
    - Spring-only: `stiffness`, `damping`
  - Attribute backfilling happens on CPU when data/vertex count grows, then uploaded to GPU.
  - Objects matched by data-array index; insertions/removals may produce unexpected transitions.
- **Custom animations**: drive props every frame externally (popmotion, requestAnimationFrame).
  ```js
  import {animate} from 'popmotion';
  const t = animate({from: 0, to: 1800, duration: 5000, repeat: Infinity, onUpdate: currentTime => {
    deckInstance.setProps({layers: [new TripsLayer({currentTime, ...})]});
  }});
  ```

### Loading Data

- Uses **loaders.gl** under the hood.
- Core includes JSON and standard image loaders; layers include format-specific loaders.
- `loadOptions` prop customizes fetch/image/loader options:
  ```ts
  new ScatterplotLayer({
    data: 'https://secure-server.com/userActivity',
    loadOptions: {
      core: {fetch: {method: 'POST', body: JSON.stringify(body), headers: {'Authorization': `Bearer ${token}`}}}
    }
  });
  ```
- Default image loader options: `{image: {type: 'auto'}, imagebitmap: {premultiplyAlpha: 'none'}}`.
  - SVG without intrinsic dimensions needs `resizeWidth/Height`.
  - Override `imagebitmap.imageOrientation: 'flipY'` if needed.
- Add custom loaders with `loaders` prop:
  ```ts
  import {CSVLoader} from '@loaders.gl/csv';
  new HexagonLayer({data: '/path/to/data.tsv', loaders: [CSVLoader], loadOptions: {csv: {delimiter: '\t'}}});
  ```
- Force URL reload by changing query parameter (data prop must shallow-change).
- Web workers:
  - Workers loaded from unpkg by default.
  - Host locally: copy `node_modules/@loaders.gl/<module>/dist/<name>-worker.js`; set `loadOptions.<name>.workerUrl`.
  - Disable workers: `{loaders: [MVTLoader], loadOptions: {core: {worker: false}}}`.
- Resource without URL:
  - ImageData / Blob URLs.
  - Use `@loaders.gl/core` `parse` utility with a loader.
  - Binary attributes: see Performance > Use Binary Data.

### Effects

- Deck applies effects via the `effects` prop.
- **Lighting**:
  - Default `LightingEffect` is automatically used; custom list replaces it.
  - Light types: `AmbientLight`, `PointLight`, `DirectionalLight`, `CameraLight`, `SunLight`.
  - Example:
    ```ts
    const ambientLight = new AmbientLight({color: [255,255,255], intensity: 1.0});
    const sunLight = new SunLight({timestamp: Date.UTC(2024,7,1,22), color: [255,255,255], intensity: 1.0});
    const lightingEffect = new LightingEffect({ambientLight, directionalLight: sunLight});
    new Deck({..., effects: [lightingEffect]});
    ```
  - Shadows: `_shadow` option on `DirectionalLight`/`SunLight` (experimental); opt out per layer with `shadowEnabled: false`.
  - **Material** prop on 3D/extruded layers:
    - `ambient`, `diffuse`, `shininess`, `specularColor`.
    - `material: true` sets defaults.
    - Applies to extruded `PolygonLayer`/`HexagonLayer` and mesh layers.
- **Post-processing**:
  - `PostProcessEffect` from `@deck.gl/core`.
  - Effects from `@luma.gl/effects`, e.g. `brightnessContrast`.
  ```ts
  import {brightnessContrast} from '@luma.gl/effects';
  new Deck({..., effects: [new PostProcessEffect(brightnessContrast, {brightness: 1, contrast: 1})]});
  ```

### Performance Tips

- General expectations:
  - ~1M points fluid at 60 FPS on decent hardware; ~10M drops to 10–20 FPS.
  - Browser allocation limits (Chrome ~1 GB per buffer) usually crash between 10M–100M items; split data across layers.
  - Mobile is more memory-sensitive and loads slower.
- Minimize layer updates (buffer regeneration is the single most expensive step):
  - Keep `data` reference stable when nothing changes; use `dataComparator` if shallow identity must change.
  - Use `updateTriggers` to recompute only changed accessors instead of replacing `data`.
- Incremental loading:
  - Avoid `data = data.concat(chunk)`; either create one layer per chunk with stable ids, or pass an **async iterable** (v7.2+).
- Visibility:
  - Use `visible` prop to toggle layers; removing/remounting regenerates GPU resources.
- Optimize accessors:
  - Prefer constants over functions.
  - Prefer `*Scale` uniforms over per-object recalculation every frame.
  - Keep accessor bodies trivial; precompute derived values outside the accessor.
- Use binary data:
  - Provide non-iterable `data` with `length` property; accessor receives `null` object and uses `{index, data, target}`.
  - Example:
    ```ts
    const DATA = {src: binaryData, length: binaryData.length / 6};
    new ScatterplotLayer({
      data: DATA,
      getPosition: (_, {index, data, target}) => { target[0]=data.src[index*6]; target[1]=data.src[index*6+1]; target[2]=0; return target; },
      getRadius:  (_, {index, data}) => data.src[index*6+2],
      getFillColor: (_, {index, data, target}) => { target[0]=data.src[index*6+3]; ... target[3]=255; return target; }
    });
    ```
- Supply attributes directly:
  ```ts
  new PointCloudLayer({
    data: {length: pointCount, attributes: {
      getPosition: {value: positions, size: 3},
      getColor: {value: colors, size: 3}
    }},
    getNormal: [0,0,1]
  });
  ```
  - Can use interleaved buffer via `buffer`, `offset`, `stride`.
  - External attributes do **not** work for composite layers or variable-geometry layers (`PathLayer`, `SolidPolygonLayer`) without extra info.
- Rendering:
  - Reduce overdraw; large radii massively increase fragment count.
  - Disable picking (`pickable: false`) for layers that don't need it.
  - Disable high-DPI rendering with `useDevicePixels: false` if GPU-bound.
  - Avoid luma.gl debug mode in production.
- `parameters: {depthCompare: 'always'}` can eliminate z-fighting for non-3D layers.

### Building Apps

- v9 package formats:
  - `dist/index.js`: ESM, ES2020 target, tree-shakable.
  - `dist/index.cjs`: CommonJS, Node16 target, bundled without deps.
  - `dist.min.js`: UMD for script tag.
  - `dist/dist.dev.js`: unminified UMD.
- Known issues:
  - Older bundlers (Webpack 4) may choke on modern syntax; transpile `node_modules`.
  - SSR may fail due to ESM-only upstream deps (see React SSR mitigation).
  - Legacy code paths may need `skipLibCheck: true`.
- Bundle size estimates (v9.0.1, gzip):
  - `Deck + Layer`: 145.3 kb baseline.
  - `DeckGL` (React): +3.84 kb.
  - `HexagonLayer`: +11.3 kb.
  - `GeoJsonLayer`: +27.7 kb (includes common primitives).
  - `MVTLayer`: +52.6 kb.
  - `Tile3DLayer`: +75.1 kb.

### Debugging

- Enable deck.gl logging in console:
  ```js
  deck.log.enable();
  deck.log.level = 2; // 1=redraws/picking, 2=layer updates, 3+=lifecycle/prop diff
  ```
  - Debug module stripped in production (`NODE_ENV=production`); add debug module after main bundle:
    ```html
    <script src="https://unpkg.com/@deck.gl/core@^9.0.0/debug.min.js"></script>
    ```
- luma.gl logging:
  ```js
  luma.log.enable();
  luma.log.level = 2; // 4 traces every GL call
  ```
- `Deck`/`DeckGL` `debug` prop instruments context; validates uniforms/attributes and reports GPU errors.

### Testing

- Unit tests for layers: `testLayer({Layer, testCases})` from `@deck.gl/test-utils`.
  - Test case props: `props`, `updateProps`, `assert({layer, oldState, subLayers})`.
- `generateLayerTests({Layer, sampleProps, assert})` creates conformance test cases.
- Integration / visual regression:
  - `SnapshotTestRunner` + probe.gl `BrowserTestDriver`.
  - Starts Chromium + webpack-dev-server, renders tests, compares screenshots to golden images.
  - Entry command: `new BrowserTestDriver().run({server: {command: 'webpack-dev-server', arguments: ['--env.render-test']}, headless: true})`.
- Repo test commands (Vitest browser mode):
  - `yarn test`: full suite.
  - `yarn test-fast`: lint + node smoke.
  - `yarn test-headless`: headless Chromium.
  - `yarn test-browser`: headed Chromium debugging.
  - `yarn test-ci`: full suite with coverage.
  - Render/interaction tests: `npx playwright install chromium`.

---

## FAQ / Roadmap / Upgrade / Contributing

### FAQ

- **Is regenerating layers every render okay?** Yes. Layers are cheap descriptors; deck.gl diffs and reuses GPU state.
- **Why doesn't my layer update?** Accessor function identity changes are ignored; use `updateTriggers` or change the value inside the data.
- **Why can't I extend Layer?** `Layer` is `Object.seal`; persistent state belongs in `layer.state`.
- **Z-fighting?** Mitigate via depth testing, `parameters.depthCompare`, `polygonOffset`, or layer ordering.
- **Easy entry points**: scripting API, JSON playground, kepler.gl.

### Roadmap (high-level / historical)

- Public direction shared via roadmap doc, vis.gl blog, RFCs in `dev-docs/RFCs`, GitHub issues.
- `@deck.gl/experimental-layers`: early layers; pin versions, expect API churn.
- Focus areas over releases:
  - Aggregation layers, info-vis, GPGPU/WebGL2, visual effects, transitions/animations, multi-viewport, pure JS support, module splitting, code size reduction.
- Status grid for current WebGPU support (v9 work in progress, not production ready):
  - `MapView` core project ported; picking not yet; shader hooks/extensions not yet; base map overlays/interleaving not yet.
  - `@deck.gl/layers`: `LineLayer`, `PointCloudLayer`, `PathLayer`, `ScatterplotLayer`, `IconLayer` have WebGPU implementations; most others WebGL-only.
  - All `@deck.gl/extensions` WebGL-only.
  - `LightingEffect` partial; `PostProcessEffect` WebGL-only.

### Upgrade Notes

- **v9.4**: `pickMultipleObjects()` default depth guarantee reduced to 10 unique objects/layer for layers using shader instance IDs. Custom layers reading `instancePickingColors` should use `picking_setPickingColorFromInstanceID()` / `picking_getPickingColorFromIndex`.
- **v9.3**:
  - Upgraded luma.gl v9.3 / loaders.gl v4.4.
  - `OrthographicView`: per-axis `zoom: [x,y]` deprecated; use `zoomX`/`zoomY`.
  - Widget renames/removals: `ViewSelectorWidget` → `SelectorWidget`; `FpsWidget` → `StatsWidget`; `InfoWidget`, `SplitterWidget`, `ContextMenuWidget`, `ThemeWidget`, `LoadingWidget` stable exports changed.
- **v9.1**:
  - mjolnir.js v3; event renames: `tripan`→`multipan`, `tap`→`click`, `doubletap`→`dblclick`; default touch pitch uses 2 fingers.
  - `GlobeView` zoom semantics changed to match MapLibre.
  - `GPUGridLayer` / `CPUGridLayer` removed; use `GridLayer` with `gpuAggregation`.
  - Uniform buffers required for custom GLSL; WebGL1-style global uniforms removed.
- **v9.0**:
  - TypeScript types at package roots; `/typed` entry points removed.
  - `DeckProps.gl` → `DeckProps.device` (luma.gl `Device`).
  - `glOptions` → `deviceProps.webgl`; `preserveDrawingBuffers` and `powerPreference: 'high-performance'` are defaults.
  - GPU parameters use WebGPU-style string constants (`blendColorOperation`, etc.).
  - `MapboxLayer` removed; use `MapboxOverlay`.
  - `@deck.gl/carto`: `CartoLayer` removed; use data source + `VectorTileLayer`.
  - Custom effects: implement `setup()` lifecycle; `preRender`/`postRender` signature changed.
  - Binary attribute `type` is string vertex format, not GL constant.
- **v8.x highlights**:
  - Layers commonly need size multiplied by `2/3` at v8.5 for billboard sizes.
  - `TextLayer.maxWidth` normalized to text size at v8.9 (divide old values by 64).
  - `TileLayer` tile callbacks now receive `index: {x, y, z}` instead of `x, y, z` root props.
  - `wrapLongitude` behavior changed to normalize to `[-180, 180]` at v8.4; use `MapView({repeat: true})` for continuous world copies.
  - `COORDINATE_SYSTEM` enum became string-valued; `METERS` → `METER_OFFSETS`.
  - `getStrokeWidth` → `getWidth` for `ArcLayer`/`LineLayer`.
  - v7.0: `HexagonCellLayer` removed; use `ColumnLayer`. `lightSettings` → `material` + `LightingEffect`. `PerspectiveView` → `FirstPersonView`. `ThirdPersonView` → `MapView`/`OrbitView`.
  - v6.x: core/layers split into `@deck.gl/layers`. `getColor` → `getFillColor`/`getLineColor` in several layers.
  - v5.x: `projectionMode` → `coordinateSystem`, `projectionOrigin` → `coordinateOrigin`; `queryObject` → `pickObject`, `queryVisibleObjects` → `pickObjects`.
  - v4.x: import `DeckGL` from `'deck.gl'` (not `'deck.gl/react'`). `radius` → `radiusScale`, `drawOutline` → `outline`, etc.

### Contributing

- Active branch: `master`; Node `>=22`; yarn/corepack; `.nvmrc` provided.
- Bootstrap: `git checkout master && yarn bootstrap && yarn test`.
- Key commands:
  - `yarn test-fast`: lint + node smoke.
  - `yarn test-headless`: headless browser.
  - `yarn test-browser`: headed browser debugging.
  - `yarn test-ci`: CI with coverage.
  - `yarn test-render`: golden-image comparisons.
- Examples can be run against local source: `yarn start-local` in example dir.
  - Use `--env.local-luma` / `--env.local-math` to link local luma.gl/math.gl.
- Governance: vis.gl under OpenJS Foundation; TSC listed in `CONTRIBUTING.md`; Slack `#deckgl`.
- M1 macOS: install arm64 deps (`pkg-config cairo pango libpng jpeg giflib librsvg`), ensure `python` exists, then `CPLUS_INCLUDE_PATH=/opt/homebrew/include yarn bootstrap`.
