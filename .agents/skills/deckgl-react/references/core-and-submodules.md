# deck.gl Core + Submodules — Structured Skill Reference

Quick reference for generating deck.gl code. Covers `@deck.gl/core` classes, `@deck.gl/extensions`, `@deck.gl/json`, `@deck.gl/widgets`, `@deck.gl/react`, and `@deck.gl/test-utils`.

---

## 1. DeckGL Core Class (`Deck`)

**Import**
```js
import {Deck} from '@deck.gl/core';
```

**Basic snippet**
```js
const deck = new Deck({
  initialViewState: {longitude: -122.45, latitude: 37.78, zoom: 12},
  controller: true,
  layers: [new ScatterplotLayer({data})]
});
```

### Constructor / key props

| Prop | Type | Default / Notes |
|------|------|---------------|
| `canvas` | `HTMLCanvasElement \| string` | auto-created if not supplied |
| `device` | `Device` (luma.gl) | auto-created |
| `deviceProps` | object | passed to luma.gl Device creation |
| `gl` | WebGLContext | deprecated, use `device` |
| `id` | string | `'deckgl-overlay'` |
| `parent` | HTMLElement | `document.body` |
| `debug` | boolean | enables luma.gl debug mode |
| `_typedArrayManagerProps` | object | `{overAlloc, poolSize}` experimental memory tuning |
| `width` / `height` | number \| string | `'100%'` |
| `style` | object | extra canvas CSS |
| `useDevicePixels` | boolean \| number | `true` |
| `parameters` | object | luma.gl GPU parameters; default blend config is pre-set |
| `layers` | `Layer[]` / nested | `[]` |
| `layerFilter` | `({layer, viewport, isPicking, cullRect, renderPass}) => boolean` | filter layers per render pass |
| `views` | `View \| View[]` | defaults to `new MapView()` |
| `viewState` | object | externally-managed view state |
| `initialViewState` | object | internally-tracked initial view state |
| `effects` | `Effect[]` | `[LightingEffect]` by default if empty is supplied |
| `_framebuffer` | object | experimental render target |
| `_animate` | boolean | force redraw each frame |
| `controller` | boolean \| object \| Controller class | default interactivity |
| `getCursor` | function | returns CSS cursor string |
| `getTooltip` | function | returns tooltip content object/string/null |
| `pickingRadius` | number | extra picking pixels |
| `touchAction` | string | default `'none'` |
| `eventRecognizerOptions` | object | `{pan, pinch, multipan, click, dblclick}` |
| `_pickable` | boolean | `true`; global picking toggle |

**`parameters` default blend config**
```js
{
  blend: true,
  blendColorSrcFactor: 'src-alpha',
  blendColorDstFactor: 'one-minus-src-alpha',
  blendAlphaSrcFactor: 'one',
  blendAlphaDstFactor: 'one-minus-src-alpha',
  polygonOffsetFill: true,
  depthWriteEnabled: true,
  depthCompare: 'less-equal'
}
```

### Callbacks

- `onDeviceInitialized(device)`
- `onViewStateChange({viewState, interactionState, oldViewState})` — return viewState to override
- `onInteractionStateChange(interactionState)`
- `onHover(info, event)`
- `onClick(info, event)`
- `onDragStart(info, event)` / `onDrag(info, event)` / `onDragEnd(info, event)`
- `onLoad()`
- `onResize({width, height}, canvasContext?)`
- `onBeforeRender(gl)` / `onAfterRender(gl)`
- `onError(error, layer?)`
- `_onMetrics(metrics)`

### Methods

```js
deck.finalize();
deck.getCanvas();             // HTMLCanvasElement | null
deck.getViews();              // View[]
deck.getView(viewId);         // View | undefined
deck.getViewports(rect?);     // Viewport[]
deck.setProps({...});
deck.redraw(force?);
await deck.pickObjectAsync({x, y, radius?, layerIds?, unproject3D?});
await deck.pickObjectsAsync({x, y, width?, height?, layerIds?, maxObjects?});
deck.pickObject({x, y, ...});            // WebGL only
deck.pickMultipleObjects({x, y, depth?, ...});
deck.pickObjects({x, y, width?, height?, ...});
```

### Members

- `isInitialized: boolean`
- `metrics: object` — performance stats incl. `fps`, `setPropsTime`, `layersCount`, `drawLayersCount`, `updateAttributesCount`, `updateAttributesTime`, `framesRedrawn`, `pickTime`, `pickCount`, `pickLayersCount`, `gpuTime`, `gpuTimePerFrame`, `cpuTime`, `cpuTimePerFrame`, `bufferMemory`, `textureMemory`, `renderbufferMemory`, `gpuMemory`.

---

## 2. Layer Base Class (`Layer`)

**Import**
```js
import {Layer} from '@deck.gl/core';
```

### Static members

- `layerName: string` — required for id / profiling.
- `defaultProps: object` — prop defaults and types.

### Constructor
```js
new Layer({...});
new Layer({...propsA}, {...propsB}); // Object.assign merge
```

### Core props

| Prop | Type | Default |
|------|------|---------|
| `id` | string | class name |
| `data` | Iterable \| string \| Promise \| AsyncIterable \| object | `[]` |
| `visible` | boolean | `true` |
| `opacity` | number | `1` |
| `extensions` | `LayerExtension[]` | `[]` |
| `onError` | function | - |
| `pickable` | boolean \| `'3d'` | `false` |
| `onHover` / `onClick` / `onDragStart` / `onDrag` / `onDragEnd` | function | - |
| `highlightColor` | Color \| function | `[0, 0, 128, 128]` |
| `highlightedObjectIndex` | number \| null | `null` |
| `autoHighlight` | boolean | `false` |
| `coordinateSystem` | string | `'default'` (one of `'default'`, `'cartesian'`, `'lnglat'`, `'meter-offsets'`, `'lnglat-offsets'`) |
| `coordinateOrigin` | `[x,y,z]` | `[0,0,0]` |
| `wrapLongitude` | boolean | `false` |
| `modelMatrix` | number[16] | - |
| `positionFormat` | `'XYZ' \| 'XY'` | `'XYZ'` |
| `colorFormat` | `'RGBA' \| 'RGB'` | `'RGBA'` |
| `numInstances` | number | derived from data |
| `updateTriggers` | object | `{}` |
| `loaders` | Loader[] | `[]` |
| `loadOptions` | object | `null` |
| `fetch` | function | `load(url, loaders, loadOptions)` |
| `onDataLoad` | function | - |
| `parameters` | object | GPU params while rendering this layer |
| `getPolygonOffset` | function | `({layerIndex}) => [0, -layerIndex * 100]` |
| `transitions` | object | `{}` |

### Lifecycle methods (for subclassing)

```js
initializeState(context)
shouldUpdateState({props, oldProps, context, changeFlags})
updateState({props, oldProps, context, changeFlags})
draw({moduleParameters, uniforms, context})
getPickingInfo({info, mode})
finalizeState()
```

### Projection / picking methods

```js
layer.project(coordinates);            // world -> screen
layer.unproject(pixels);                // screen -> world
layer.projectPosition(coordinates, params?);
layer.decodePickingColor(color);       // Uint8Array -> index
layer.encodePickingColor(index);       // index -> [r,g,b]
layer.nullPickingColor();
```

### Members

- `context: {gl, viewport, deck}`
- `state: {attributeManager}`
- `props`
- `isLoaded: boolean`
- `parent: Layer | null`

---

## 3. CompositeLayer

**Import**
```js
import {CompositeLayer} from '@deck.gl/core';
```

```js
class MyCompositeLayer extends CompositeLayer {
  renderLayers() {
    return [
      new ScatterplotLayer({id: 'sub', data: this.props.data, ...})
    ];
  }
}
```

### Unique props

| Prop | Type | Notes |
|------|------|-------|
| `_subLayerProps` | object | `{subLayerId: {propOverride}}` experimental |

### Unique methods

- `renderLayers() => null \| Layer \| Layer[]`
- `filterSubLayer({layer, viewport, isPicking, renderPass}) => boolean`
- `getPickingInfo({info, mode, sourceLayer}) => info \| null`
- `getSubLayerProps(subLayerProps) => propsObject`
- `shouldRenderSubLayer(id, data) => boolean`
- `getSubLayerClass(id, DefaultLayerClass) => LayerClass`
- `getSubLayerRow(row, sourceObject, sourceObjectIndex) => row`
- `getSubLayerAccessor(accessor)`

### Members

- `isComposite: true`
- `isLoaded: boolean` — includes sublayers

---

## 4. Views & Controllers

### Base View

**Import**
```js
import {View} from '@deck.gl/core';
```

```js
new View({
  id: 'default',
  x: 0, y: 0,
  width: '100%', height: '100%',
  padding: {left, right, top, bottom},
  controller: true,
  viewState: null,
  clear: false,
  clearColor: [0,0,0,0],
  clearDepth: 1.0,
  clearStencil: 0,
  parameters: {}
});
```

### Specialized Views

| View | Import | Controller default | View state fields |
|------|--------|--------------------|-------------------|
| `MapView` | `import {MapView} from '@deck.gl/core'` | `MapController` | `longitude, latitude, zoom, pitch?, bearing?, maxZoom, minZoom, maxPitch, minPitch, position?` |
| `GlobeView` | `import {_GlobeView as GlobeView} from '@deck.gl/core'` | `GlobeController` | `longitude, latitude, zoom, bearing?, pitch?, maxZoom, minZoom, maxPitch, minPitch` |
| `OrbitView` | `import {OrbitView} from '@deck.gl/core'` | `OrbitController` | `target?, rotationOrbit?, rotationX?, zoom?, minZoom, maxZoom, minRotationX, maxRotationX` |
| `OrthographicView` | `import {OrthographicView} from '@deck.gl/core'` | `OrthographicController` | `target?, zoom?, zoomX?, zoomY?, minZoom, maxZoom, minZoomX/Y, maxZoomX/Y` |
| `FirstPersonView` | `import {FirstPersonView} from '@deck.gl/core'` | `FirstPersonController` | `longitude?, latitude?, position?, bearing?, pitch?, maxPitch, minPitch` |

**MapView extras:** `repeat`, `nearZMultiplier`, `farZMultiplier`, `projectionMatrix`, `fovy`, `altitude`, `orthographic`.
**GlobeView extras:** `resolution`, `nearZMultiplier`, `farZMultiplier`, `parameters: {cullMode: 'back'}`.
**OrbitView extras:** `orbitAxis: 'Y' | 'Z'`, `projectionMatrix`, `fovy`, `near`, `far`, `orthographic`.
**OrthographicView extras:** `flipY`, `near`, `far`.
**FirstPersonView extras:** `projectionMatrix`, `fovy`, `near`, `far`, `focalDistance`.

### Controllers

**Base options** (`controller: { ... }` or passed to `View.controller`):

| Option | Type | Default |
|--------|------|---------|
| `scrollZoom` | boolean \| `{speed?, smooth?}` | `true` |
| `dragPan` | boolean | `true` |
| `dragRotate` | boolean | `true` |
| `doubleClickZoom` | boolean | `true` |
| `doubleClickDragZoom` | boolean | `true` |
| `touchZoom` | boolean | `true` |
| `touchRotate` | boolean | `false` |
| `keyboard` | boolean \| `{zoomSpeed?, moveSpeed?, rotateSpeedX?, rotateSpeedY?}` | `true` |
| `dragMode` | `'pan' \| 'rotate'` | view-specific |
| `inertia` | boolean \| number | `false` |
| `maxBounds` | `[min, max]` | - |

**Per-controller defaults**

- `MapController`: `dragMode: 'pan'`, keyboard arrows pan/rotate, +/- zoom, `normalize: true`, `rotationPivot: 'center' \| '2d' \| '3d'`.
- `GlobeController`: `dragPan: 'pan'`, `touchRotate` for bearing, `maxBounds` on `[lng,lat]`.
- `OrbitController`: `dragMode: 'rotate'`, `maxBounds` on target.
- `OrthographicController`: `dragPan: 'pan'`, no rotation, `zoomAxis: 'X' \| 'Y' \| 'all'`, `maxBounds`.
- `FirstPersonController`: `dragMode: 'rotate'`, scroll moves forward/backward, `maxBounds`.
- `TerrainController`: extends `MapController`, `rotationPivot: '3d'`, requires `pickable: '3d'` layer for elevation.

**Custom controller snippet**
```js
import {Controller} from '@deck.gl/core';
class MyController extends Controller {
  events = ['pointermove'];
  handleEvent(event) { ... }
}
// usage
new Deck({controller: {type: MyController}});
```

### View class methods

```js
view.equals(otherView);
view.clone(newProps);
view.makeViewport({width, height, viewState});
view.getDimensions({width, height}); // {x, y, width, height}
```

---

## 5. Viewports

### Viewport

**Import**
```js
import {Viewport} from '@deck.gl/core';
```

```js
new Viewport({
  width, height,
  viewMatrix,
  projectionMatrix,
  latitude, longitude, zoom,
  focalDistance, position, modelMatrix,
  fovy, near, far, orthographic
});
```

```js
viewport.equals(other);
viewport.project(coordinates, {topLeft?});
viewport.unproject(pixels, {topLeft?, targetZ?});
viewport.projectPosition(coordinates);     // -> [x,y,z] WebMercator
viewport.unprojectPosition(coordinates);   // -> [lng,lat,altitude]
viewport.getBounds({z?});                    // [minX, minY, maxX, maxY]
viewport.getFrustumPlanes();
```

### WebMercatorViewport

**Import**
```js
import {WebMercatorViewport} from '@deck.gl/core';
```

```js
const viewport = new WebMercatorViewport({
  width, height,
  longitude, latitude, zoom,
  pitch, bearing, altitude,
  nearZMultiplier, farZMultiplier, orthographic, projectionMatrix
});
```

```js
viewport.project([lng, lat, altitudeMeters], {topLeft?});
viewport.unproject([x, y, z], {topLeft?, targetZ?});
viewport.getDistanceScales();
viewport.addMetersToLngLat(lngLatZ, xyz);
viewport.panByPosition3D(coords, pixel);
viewport.fitBounds(bounds, {width?, height?, minExtent?, maxZoom?, padding?, offset?});
```

### GlobeViewport (experimental)

**Import**
```js
import {_GlobeViewport as GlobeViewport} from '@deck.gl/core';
```

```js
new GlobeViewport({width, height, longitude, latitude, zoom, bearing, pitch, altitude, nearZMultiplier, farZMultiplier});
```

---

## 6. Transitions / Interpolators

### TransitionInterpolator (base)

**Import**
```js
import {TransitionInterpolator} from '@deck.gl/core';
```

Constructor takes an object or array of prop names:
```js
new TransitionInterpolator({compare: [...], extract: [...], required: [...]});
new TransitionInterpolator(['longitude', 'latitude', 'zoom']);
```

Implement:
- `getDuration(startViewState, endViewState) => number`
- `initializeProps(start, end) => {start, end}`
- `interpolateProps(start, end, t) => viewStateFields`

### LinearInterpolator

**Import**
```js
import {LinearInterpolator} from '@deck.gl/core';
```

```js
new LinearInterpolator({
  transitionProps: ['target', 'zoom'],
  around: [x, y],
  makeViewport: props => new WebMercatorViewport(props)
});
```

Default `transitionProps`: `['longitude', 'latitude', 'zoom', 'bearing', 'pitch']`.

### FlyToInterpolator

**Import**
```js
import {FlyToInterpolator} from '@deck.gl/core';
```

```js
new FlyToInterpolator({curve: 1.414, speed: 1.2, screenSpeed?, maxDuration?});
```

### ViewState transition usage

```js
new Deck({
  controller: true,
  initialViewState: {longitude: -122.45, latitude: 37.78, zoom: 12},
  onViewStateChange: ({viewState}) => ({
    ...viewState,
    transitionDuration: 1000,
    transitionInterpolator: new FlyToInterpolator()
  })
});
```

---

## 7. Effects / Lights

### Lights

| Light | Import | Props |
|-------|--------|-------|
| `AmbientLight` | `import {AmbientLight} from '@deck.gl/core'` | `{color: [255,255,255], intensity: 1.0}` |
| `DirectionalLight` | `import {DirectionalLight} from '@deck.gl/core'` | `{color, intensity, direction: [0,0,-1], _shadow?}` |
| `PointLight` | `import {PointLight} from '@deck.gl/core'` | `{color, intensity, position: [0,0,1], attenuation: [1,0,0]}` |
| `_CameraLight` | `import {_CameraLight as CameraLight} from '@deck.gl/core'` | `{color, intensity}` |
| `_SunLight` | `import {_SunLight as SunLight} from '@deck.gl/core'` | `{timestamp, color, intensity}` |

### LightingEffect

**Import**
```js
import {LightingEffect} from '@deck.gl/core';
```

```js
new LightingEffect({
  ambientLight: new AmbientLight({color: [255,255,255], intensity: 1}),
  directionalLights: [new DirectionalLight(...)],
  pointLights: [new PointLight(...)]
});
```

Default ambient + two directional lights.

### PostProcessEffect

**Import**
```js
import {PostProcessEffect} from '@deck.gl/core';
import {brightnessContrast} from '@luma.gl/effects';
```

```js
const effect = new PostProcessEffect(brightnessContrast, {brightness: 1.0, contrast: 1.0});
new Deck({effects: [effect], ...});
```

---

## 8. Extensions (`@deck.gl/extensions`)

**Import**
```js
import {DataFilterExtension, PathStyleExtension, FillStyleExtension, BrushingExtension, ClipExtension, MaskExtension, CollisionFilterExtension, Fp64Extension, _TerrainExtension as TerrainExtension} from '@deck.gl/extensions';
```

### DataFilterExtension

```js
new DataFilterExtension({filterSize: 1, categorySize: 0, fp64: false, countItems: false})
```

Layer props added:
- `getFilterValue` / `getFilterCategory`
- `filterRange` / `filterCategories`
- `filterSoftRange`
- `filterTransformSize`, `filterTransformColor`
- `filterEnabled`
- `onFilteredItemsChange`

### PathStyleExtension

```js
new PathStyleExtension({dash: true, highPrecisionDash: false, offset: false})
```

Layer props added:
- `getDashArray: [3, 2]`
- `dashJustified: false`
- `getOffset: 0`
- `dashGapPickable: false`

### FillStyleExtension

```js
new FillStyleExtension({pattern: true})
```

Layer props added:
- `fillPatternAtlas`
- `fillPatternEnabled: true`
- `fillPatternMapping`
- `fillPatternMask: true`
- `getFillPattern`
- `getFillPatternScale: 1`
- `getFillPatternOffset: [0, 0]`

### BrushingExtension

```js
new BrushingExtension()
```

Layer props added:
- `brushingRadius` (meters)
- `brushingEnabled: true`
- `brushingTarget: 'source' | 'target' | 'source_target' | 'custom'`
- `getBrushingTarget`

### ClipExtension

```js
new ClipExtension()
```

Layer props added:
- `clipBounds: [left, bottom, right, top]`
- `clipByInstance`

### MaskExtension

```js
new MaskExtension()
```

Mask layer must use `operation: 'mask'`. Masked layer props:
- `maskId`
- `maskByInstance`
- `maskInverted: false`

### CollisionFilterExtension

```js
new CollisionFilterExtension()
```

Layer props added:
- `collisionEnabled: true`
- `collisionGroup`
- `collisionTestProps`
- `getCollisionPriority`

### Fp64Extension

```js
new Fp64Extension()
```

Requires layer `coordinateSystem: 'lnglat'`.

### TerrainExtension (experimental)

```js
import {_TerrainExtension as TerrainExtension} from '@deck.gl/extensions';
new TerrainExtension()
```

Layer prop added:
- `terrainDrawMode: 'offset' | 'drape'`

Requires a terrain source layer with `operation: 'terrain'` or `'terrain+draw'`.

---

## 9. JSON Converter / Configuration (`@deck.gl/json`)

**Import**
```js
import {JSONConverter, JSONConfiguration} from '@deck.gl/json';
```

```js
const configuration = new JSONConfiguration({
  classes: {MapView, ScatterplotLayer},
  functions: {scaleRadius: ({value}) => value * 2},
  constants: {MapController},
  enumerations: {GL},
  reactComponents: {},
  React,
  typeKey: '@@type',
  functionKey: '@@function',
  convertFunction: str => ..., // hook for `@@=...`
  preProcessClassProps: (classRef, props) => props,
  postProcessConvertedJson: json => json
});

const converter = new JSONConverter({configuration});
const deckProps = converter.convert(json);
```

### Conversion prefixes

| Prefix | Meaning | Example |
|--------|---------|---------|
| `@@type` | instantiate class / React component | `"@@type": "ScatterplotLayer"` |
| `@@function` | call registered function | `"@@function": "calculateRadius"` |
| `@@=` | parse mini-expression into accessor | `"@@=[lng, lat]"` |
| `@@#` | constant | `"@@#MapController"` |
| `@@#<Enum>.<Value>` | enumeration | `"@@#GL.ONE"` |

---

## 10. React Wrappers / Widgets (`@deck.gl/react`)

### DeckGL React Component

**Import**
```js
import {DeckGL} from '@deck.gl/react';
```

```tsx
<DeckGL
  initialViewState={{longitude: -122.45, latitude: 37.78, zoom: 12}}
  controller
  layers={[new ScatterplotLayer({data})]}
>
  <Map mapStyle="..." />
</DeckGL>
```

Exposes all `Deck` props plus:
- `ContextProvider: React.Component` — passes deck context to children.
- JSX layers (`<LineLayer .../>`), JSX views (`<MapView .../>`), JSX widgets (`<ZoomWidget .../>`).
- Children can be functions: `{(x, y, width, height, viewState, viewport) => ReactNode}`.

Public callable methods: `pickObjectAsync`, `pickObjectsAsync`, `pickObject`, `pickMultipleObjects`, `pickObjects`.

### useWidget hook

**Import**
```js
import DeckGL, {useWidget} from '@deck.gl/react';
```

```tsx
const CompassWidget = (props) => {
  const widget = useWidget(UniversalCompassWidget, props);
  return null;
};
```

Signature:
```ts
useWidget<T extends Widget, PropsT>(WidgetClass, props): T
```

### Re-exported React widgets from `@deck.gl/react`

All `@deck.gl/widgets` classes are re-exported as React components, e.g.:
```tsx
import {DeckGL, ZoomWidget, CompassWidget, FullscreenWidget} from '@deck.gl/react';
```

---

## 11. Widgets (`@deck.gl/widgets`)

**Base class**
```js
import {Widget} from '@deck.gl/core';
```

### Common WidgetProps

| Prop | Type | Default |
|------|------|---------|
| `id` | string | class name |
| `style` | object | `{}` |
| `className` | string | `''` |
| `_container` | string \| HTMLDivElement | viewId or `'root'` |
| `viewId` | string \| null | `null` |
| `placement` | string | `'top-left'` (also `'top-right'`, `'bottom-left'`, `'bottom-right'`, `'fill'`) |

### Built-in widgets

| Widget | Import | Key props |
|--------|--------|-----------|
| `ZoomWidget` | `{ZoomWidget}` | `orientation`, `zoomAxis`, `zoomInLabel`, `zoomOutLabel`, `transitionDuration`, `onZoom` |
| `CompassWidget` | `{CompassWidget}` | `label`, `transitionDuration`, `onReset` |
| `GimbalWidget` | `{GimbalWidget}` | `label`, `strokeWidth`, `transitionDuration`, `onReset` |
| `ResetViewWidget` | `{ResetViewWidget}` | `label`, `initialViewState`, `onReset` |
| `FullscreenWidget` | `{FullscreenWidget}` | `container`, `enterLabel`, `exitLabel`, `onFullscreenChange` |
| `ScreenshotWidget` | `{ScreenshotWidget}` | `label`, `filename`, `imageFormat`, `onCapture` |
| `LoadingWidget` | `{LoadingWidget}` | `label`, `onLoadingChange` |
| `StatsWidget` | `{_StatsWidget}` | `type`, `stats`, `title`, `initialExpanded`, `framesPerUpdate`, `formatters`, `resetOnUpdate`, `expanded`, `onExpandedChange` |
| `ScaleWidget` | `{_ScaleWidget}` | `label` |
| `GeocoderWidget` | `{_GeocoderWidget}` | `label`, `geocoder`, `apiKey`, `customGeocoder`, `_geolocation`, `transitionDuration`, `onGeocode` |
| `ThemeWidget` | `{ThemeWidget}` | `lightModeTheme`, `darkModeTheme`, `initialThemeMode`, `themeMode`, `onThemeModeChange`, `lightModeLabel`, `darkModeLabel` |
| `TimelineWidget` | `{_TimelineWidget}` | `timeRange`, `step`, `initialTime`, `time`, `onTimeChange`, `autoPlay`, `loop`, `playInterval`, `playing`, `onPlayingChange`, `formatLabel`, `timeline`; methods `play()`, `stop()` |
| `InfoWidget` | `{InfoWidget}` | `mode: 'hover' \| 'click'`, `getTooltip`, `minOffset`, `placement`, `offset`, `arrow` |
| `PopupWidget` | `{PopupWidget}` | `position`, `content`, `marker`, `defaultIsOpen`, `closeButton`, `closeOnClickOutside`, `onOpenChange`, `placement`, `offset`, `arrow` |
| `ContextMenuWidget` | `{ContextMenuWidget}` | `menuItems`, `getMenuItems`, `onMenuItemSelected`, `placement`, `offset`, `arrow` |
| `IconWidget` | `{IconWidget}` | `icon` (required), `label`, `color`, `onClick` |
| `ToggleWidget` | `{ToggleWidget}` | `initialChecked`, `icon`, `onIcon`, `label`, `onLabel`, `color`, `onColor`, `onChange` |
| `SelectorWidget` | `{SelectorWidget}` | `options: {value, icon, label?}[]`, `initialValue`, `onChange` |
| `ScrollbarWidget` | `{ScrollbarWidget}` | `contentBounds`, `orientation`, `stepSize`, `pageSize`, `captureWheel`, `decorations` |
| `SplitterWidget` | `{_SplitterWidget}` | `viewLayout: {views, orientation, initialSplit, editable, minSplit, maxSplit}`, `onChange`, `onDragStart`, `onDragEnd` |

### View layout helper

```js
import {buildViewsFromViewLayout} from '@deck.gl/widgets';
const compiled = buildViewsFromViewLayout({layout, width, height, previous?, splitValues?, viewPropsById?});
// compiled.views, compiled.rectsById, compiled.splittersById
```

### Styling / themes

```ts
import '@deck.gl/widgets/stylesheet.css';
import {DarkGlassTheme, LightGlassTheme, DarkTheme, LightTheme} from '@deck.gl/widgets';
```

Custom theme via CSS variables: `--button-size`, `--button-border-radius`, `--widget-margin`, `--button-background`, `--button-stroke`, `--button-shadow`, `--button-icon-idle`, `--button-icon-hover`, `--button-text-color`, `--menu-*`, `--range-*`, and per-widget icon variables.

---

## 12. Test Utils (`@deck.gl/test-utils`)

### Install

```bash
npm install --save-dev @deck.gl/test-utils vitest @vitest/browser playwright
```

```ts
import {test, expect} from 'vitest';
import {testLayer, testLayerAsync, generateLayerTests} from '@deck.gl/test-utils/vitest';
```

### testLayer / testLayerAsync

```ts
testLayer({
  Layer: ScatterplotLayer,
  testCases: [
    {props: {data: []}},
    {
      props: {data: [{position: [0, 0]}], getPosition: d => d.position},
      onAfterUpdate({layer, oldState, subLayers, subLayer, spies}) { ... }
    },
    {updateProps: {radiusScale: 2}}
  ],
  viewport?: Viewport,
  spies?: string[],
  onError: (err, title) => expect(err).toBeFalsy()
});

await testLayerAsync({Layer, testCases, ...});
```

### generateLayerTests

```ts
const testCases = generateLayerTests({
  Layer: GeoJsonLayer,
  sampleProps: {data: SAMPLE_GEOJSON},
  assert: (cond, msg) => expect(cond, msg).toBeTruthy(),
  onBeforeUpdate?: ({testCase, layer}) => {},
  onAfterUpdate?: ({layer, subLayers}) => {}
});
```

### InteractionTestRunner

```js
import {InteractionTestRunner} from '@deck.gl/test-utils';
```

```js
const runner = new InteractionTestRunner(deckProps);
runner.add([{
  name: 'MapController pan',
  events: [{type: 'drag', startX: 400, startY: 200, endX: 300, endY: 200, steps: 3}],
  onBeforeEvents: ({deck}) => ({viewport: deck.getViewports()[0]}),
  onAfterEvents: ({deck, context}) => { ... }
}]);
await runner.run({timeout: 2000});
```

Supported event types: `keypress`, `click`, `mousemove`, `drag`, `wait`.

### SnapshotTestRunner

```js
import {SnapshotTestRunner} from '@deck.gl/test-utils';
```

```js
const runner = new SnapshotTestRunner({width: 800, height: 600});
runner.add([{
  name: 'ScatterplotLayer',
  viewState: {...},
  layers: [...],
  onAfterRender: ({deck, layers, done}) => done(),
  goldenImage: './golden.png',
  imageDiffOptions: {tolerance, threshold, ...}
}]);
await runner.run({
  timeout: 2000,
  imageDiffOptions: {...},
  onTestStart, onTestPass, onTestFail
});
```

---

## 13. Internal / Custom Layer Helpers

### AttributeManager

```js
import {AttributeManager} from '@deck.gl/core';
```

```js
const manager = new AttributeManager({id: 'attribute-manager'});
manager.add({
  positions: {size: 2, accessor: 'getPosition', update: calculatePositions},
  colors: {size: 4, type: 'unorm8', accessor: 'getColor', update: calculateColors}
});
manager.addInstanced({...});
manager.remove(['positions']);
manager.invalidate('getColor');
manager.invalidateAll();
manager.update({data, numInstances, transitions, startIndex, endIndex, props, buffers, context});
manager.getBufferLayouts(modelInfo);
```

### Attribute

```js
import {Attribute} from '@deck.gl/core';
```

```js
const positions = new Attribute({
  id: 'vertexPositions',
  size: 3,
  value: new Float32Array([...])
});
positions.update({value: newValue});
positions.getBuffer();
positions.delete();
```

### Shader modules

- `project` shader module functions: `project_position`, `project_size`, `project_size_to_pixel`, `project_pixel_size`, `project_pixel_size_to_clipspace`, `project_normal`, `project_common_position_to_clipspace`, `project_get_orientation_matrix`.
- `project32`: 32-bit `project_position_to_clipspace`.
- `project64`: 64-bit `project_position_to_clipspace`, `project_position_fp64`, `project_common_position_to_clipspace_fp64`.

---

## 14. Scripting `DeckGL` class

For standalone / bundle usage `deck.DeckGL` extends `Deck` with Mapbox/MapLibre integration.

Extra props: `container`, `map`, `mapStyle`, `mapboxApiAccessToken`, `mapOptions`.
Extra method: `getMapboxMap()`.

```js
new deck.DeckGL({
  mapStyle: 'https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json',
  initialViewState: {longitude: -122.45, latitude: 37.8, zoom: 12},
  controller: true,
  layers: [new deck.ScatterplotLayer({...})]
});
```
