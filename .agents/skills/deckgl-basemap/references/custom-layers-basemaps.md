# deck.gl Custom Layers & Base-Map Integrations — Skill Reference

Generated from deck.gl docs (developer-guide/custom-layers, developer-guide/base-maps, and API references for mapbox/google-maps/arcgis/carto).

---

## 1. Writing Custom Layers

### 1.1 Quick decisions

| Approach | When to use | Base class |
|----------|-------------|------------|
| Composite layer | Reuse existing layers, transform props/data, adapt APIs | `CompositeLayer` |
| Subclassed layer | Add/modify attributes, uniforms, or shaders of one existing layer | e.g. `ScatterplotLayer`, `PathLayer` |
| Primitive layer | Custom WebGL2/WebGPU geometry/shaders, full control | `Layer` |
| Layer extension | Same modification applied to many layer types | `LayerExtension` |

### 1.2 Layer class skeleton

```js
import {Layer} from '@deck.gl/core';

class AwesomeLayer extends Layer {
  initializeState() { /* GPU resources */ }
  updateState({props, oldProps, changeFlags}) { /* reactive updates */ }
  draw({uniforms}) { /* render */ }
  finalizeState() { /* cleanup */ }
}

AwesomeLayer.layerName = 'AwesomeLayer';
AwesomeLayer.defaultProps = {
  color: {type: 'color', value: [255, 0, 0]},
  opacity: {type: 'number', value: 0.5, min: 0, max: 1},
  getRadius: {type: 'accessor', value: d => d.radius}
};
```

Props passed to `new AwesomeLayer({...})` are resolved against `defaultProps` into `layer.props`.

---

### 1.3 Layer lifecycle

| Stage | Called | Typical use |
|-------|--------|-------------|
| Initialization | `initializeState()` | Create `Model`, register attributes, build textures/buffers |
| Should-update | `shouldUpdateState({props, oldProps, changeFlags})` | Skip expensive updates; default updates on prop/data changes |
| Update | `updateState({props, oldProps, changeFlags})` | Recalculate attributes, invalidate attribute manager, update uniforms |
| Render sublayers | `renderLayers()` (composite) | Return array of sub-layers |
| Draw | `draw({uniforms})` (primitive) | Call `state.model.render(...)` |
| Picking | `draw()` with picking uniforms, then `getPickingInfo({info, sourceLayer})` | Encode/decode picking color, augment info |
| Finalization | `finalizeState()` | Destroy GPU resources |

Key lifecycle rules:

- `updateState` is called both on init and on prop/context changes.
- `changeFlags` contains pre-computed flags such as `propsChanged`, `dataChanged`, `viewportChanged`.
- By default, when `props.data` changes, all attributes are invalidated and recalculated.
- Persist state across renders by calling `this.setState({...})`; later accessible as `this.state`.

---

### 1.4 Attributes

Two conceptual attribute categories:

- **Geometric attributes** — positions, normals, tangents. Fixed-primitive layers usually share these via a `Geometry`; variable-primitive layers generate them during tessellation.
- **Descriptive attributes** — colors, sizes, radii. For fixed primitives these are instanced (one value per data row). For variable primitives they are duplicated per generated vertex (or referenced via a `rowIndexes` texture).

Primitive layer attribute registration:

```js
import {Layer} from '@deck.gl/core';
import {Model} from '@luma.gl/core';

class CubeLayer extends Layer {
  initializeState() {
    const {gl} = this.context;
    this.state.attributeManager.add({
      instancePositions: {size: 3, accessor: 'getPosition'},
      instanceColors: {
        size: 4,
        type: 'uint8',
        normalized: true,
        accessor: 'getColor',
        update: this.calculateInstanceColors
      }
    });
    this.setState({model: this._getModel(gl)});
  }

  _getModel(gl) {
    return new Model(gl, Object.assign({}, this.getShaders(), {
      id: this.props.id,
      geometry: new CubeGeometry(),
      isInstanced: true
    }));
  }

  calculateInstanceColors(attribute) {
    const {value} = attribute;
    let i = 0;
    for (const object of this.props.data) {
      const color = this.props.getColor(object);
      value[i++] = color[0];
      value[i++] = color[1];
      value[i++] = color[2];
      value[i++] = color[3] ?? 255;
    }
  }
}
```

Dynamic (tessellated) geometry example:

```js
import {Model, Geometry} from '@luma.gl/core';

_getModel(gl) {
  return new Model(gl, Object.assign({}, this.getShaders(), {
    id: this.props.id,
    geometry: new Geometry({id: this.props.id, topology: 'line-list'}),
    vertexCount: 0,
    isIndexed: true
  }));
}
```

---

### 1.5 Prop types

Declare static `defaultProps` on the layer class.

```js
MyLayer.defaultProps = {
  texture: {type: 'object', value: null, async: true},
  strokeOpacity: {type: 'number', value: 1, min: 0, max: 1},
  strokeColor: {type: 'color', value: [255, 0, 0]},
  getRadius: {type: 'accessor', value: d => d.radius}
};
```

Built-in prop type options:

| Type | Notes | Options |
|------|-------|---------|
| `boolean` | truthiness compare | — |
| `number` | strict equal by default | `min`, `max` |
| `color` | RGB(A) array, deep equal | — |
| `image` | URL/Texture/Image/Canvas/Video/ImageBitmap/ImageData; auto-converts to `Texture2D` | `parameters` |
| `array` | value array | `optional`, `ignore`, `compare` |
| `object` | arbitrary object | `optional`, `ignore`, `compare` |
| `accessor` | function or constant | — |
| `function` | function type | `optional`, `ignore` (default `true`) |

Common meta-fields for any prop:

- `type` (required string)
- `value` (required default)
- `async` — allow Promise or URL string
- `transform` — `(value, propType, layer) => newValue`
- `release` — `(value, propType, layer) => void`
- `validate` — `(value, propType) => boolean`
- `equal` — `(value, oldValue, propType) => boolean`
- `deprecatedFor` — redirect old prop name to new prop name(s)

Performance tip: declare accessors with `type: 'accessor'` so inline function/array props do not trigger redundant layer updates.

---

### 1.6 Picking

deck.gl implements color-based picking on the GPU.

1. Each object gets a picking color with `layer.encodePickingColor(index)`.
2. Pickable layers render an off-screen picking buffer.
3. deck.gl decodes the pixel with `layer.decodePickingColor(color)`.
4. `getPickingInfo({info, sourceLayer})` is called bottom-up through the composite hierarchy to augment the info object.
5. Only the top-level layer's `onHover`/`onClick` callbacks fire.

Custom picking attribute when the logical picking index differs from the rendered instance id:

```js
class MyLayer extends Layer {
  initializeState() {
    this.state.attributeManager.add({
      rowIndexes: {
        size: 1,
        type: 'uint32',
        update: this.calculatePickingIndexes
      }
    });
  }

  calculatePickingIndexes(attribute) {
    const {value} = attribute;
    let i = 0;
    for (const object of this.props.data) {
      value[i] = i;
      i++;
    }
  }
}
```

Adding the picking module to a custom `Model`:

```js
import {Model} from '@luma.gl/core';
import {picking} from '@deck.gl/core';

new Model(gl, {
  vs: CUSTOM_VS,
  fs: CUSTOM_FS,
  modules: [picking]
});
```

GLSL picking pattern:

```glsl
// vertex shader
in float rowIndexes;

void main(void) {
  // ...
  geometry.pickingColor = picking_getPickingColorFromIndex(rowIndexes);
}

// fragment shader
void main(void) {
  // ...last color write
  gl_FragColor = picking_filterPickingColor(gl_FragColor);
}
```

Override `getPickingInfo` to customize the returned info:

```js
getPickingInfo({info, sourceLayer}) {
  info.object = this.props.data[info.index];
  return info;
}
```

---

### 1.7 Subclassed layers

Override attribute or shader behavior while keeping the rest of the layer.

Add an instanced attribute:

```js
import {PointCloudLayer} from '@deck.gl/layers';

class MyPointCloudLayer extends PointCloudLayer {
  initializeState() {
    super.initializeState();
    this.state.attributeManager.addInstanced({
      instanceRadiusPixels: {size: 1, accessor: 'getRadius'}
    });
  }

  getShaders() {
    return Object.assign({}, super.getShaders(), {
      vs: customVertexShader
    });
  }
}

MyPointCloudLayer.defaultProps = {
  getRadius: {type: 'accessor', value: 1}
};
```

Override shaders:

```js
class RoundedRectangleLayer extends ScatterplotLayer {
  draw({uniforms}) {
    super.draw({
      uniforms: {...uniforms, cornerRadius: this.props.cornerRadius}
    });
  }

  getShaders() {
    return Object.assign({}, super.getShaders(), {
      fs: customFragmentShader
    });
  }
}

RoundedRectangleLayer.defaultProps = {
  cornerRadius: {type: 'number', value: 0.1, min: 0, max: 1}
};
```

---

### 1.8 Composite layers

Use when building layers by composing other layers.

Basic composite layer:

```js
import {CompositeLayer, IconLayer, TextLayer} from '@deck.gl/core';

class LabeledIconLayer extends CompositeLayer {
  renderLayers() {
    return [
      new IconLayer(this.getSubLayerProps({
        id: 'icon',
        data: this.props.data,
        iconAtlas: this.props.iconAtlas,
        iconMapping: this.props.iconMapping,
        getPosition: this.props.getPosition,
        getIcon: this.props.getIcon,
        getSize: this.props.getIconSize,
        getColor: this.props.getIconColor,
        updateTriggers: {
          getPosition: this.props.updateTriggers.getPosition,
          getIcon: this.props.updateTriggers.getIcon,
          getSize: this.props.updateTriggers.getIconSize,
          getColor: this.props.updateTriggers.getIconColor
        }
      })),
      new TextLayer(this.getSubLayerProps({
        id: 'label',
        data: this.props.data,
        fontFamily: this.props.fontFamily,
        fontWeight: this.props.fontWeight,
        getPosition: this.props.getPosition,
        getText: this.props.getText,
        getSize: this.props.getTextSize,
        getColor: this.props.getTextColor,
        updateTriggers: {
          getPosition: this.props.updateTriggers.getPosition,
          getText: this.props.updateTriggers.getText,
          getSize: this.props.updateTriggers.getTextSize,
          getColor: this.props.updateTriggers.getTextColor
        }
      }))
    ];
  }
}

LabeledIconLayer.layerName = 'LabeledIconLayer';
LabeledIconLayer.defaultProps = {
  getPosition: {type: 'accessor', value: x => x.position},
  iconAtlas: null,
  iconMapping: {type: 'object', value: {}, async: true},
  getIcon: {type: 'accessor', value: x => x.icon},
  getIconSize: {type: 'accessor', value: 20},
  getIconColor: {type: 'accessor', value: [0, 0, 0, 255]},
  fontFamily: DEFAULT_FONT_FAMILY,
  fontWeight: DEFAULT_FONT_WEIGHT,
  getText: {type: 'accessor', value: x => x.text},
  getTextSize: {type: 'accessor', value: 12},
  getTextColor: {type: 'accessor', value: [0, 0, 0, 255]}
};
```

Composite helper methods:

- `compositeLayer.getSubLayerProps({id, ...})` — merges common props (`pickable`, `visible`, `coordinateSystem`, `opacity`) and generates a unique sublayer id (`${parentId}-${id}`).
- `compositeLayer.getSubLayerRow(datum, originalObject, index)` — decorate transformed sublayer data with a reference to the original object.
- `compositeLayer.getSubLayerAccessor(accessor)` — wrap a user accessor so it receives the original object even though the sublayer iterates transformed rows.
- `compositeLayer.getPickingInfo({info, sourceLayer})` — intercept sublayer picking info before it reaches the user.

Transform data and preserve original accessors:

```js
class MyCompositeLayer extends CompositeLayer {
  updateState({props, changeFlags}) {
    if (changeFlags.dataChanged) {
      const subLayerData = [];
      props.data.forEach((object, index) => {
        for (const timestamp of object.timestamps) {
          subLayerData.push(this.getSubLayerRow({timestamp}, object, index));
        }
      });
      this.setState({subLayerData});
    }
  }

  renderLayers() {
    const {subLayerData} = this.state;
    const {getPosition, getRadius, getFillColor, updateTriggers} = this.props;

    return new ScatterplotLayer(this.getSubLayerProps({
      id: 'scatterplot',
      data: subLayerData,
      getPosition: this.getSubLayerAccessor(getPosition),
      getRadius: this.getSubLayerAccessor(getRadius),
      getFillColor: this.getSubLayerAccessor(getFillColor),
      updateTriggers
    }));
  }
}
```

---

### 1.9 Primitive layers

Extend `Layer` directly when you need custom WebGL2/WebGPU rendering.

Single-model instanced layer:

```js
import {Layer} from '@deck.gl/core';
import {Model, CubeGeometry} from '@luma.gl/core';

export default class CubeLayer extends Layer {
  initializeState() {
    const {gl} = this.context;
    this.setState({model: this._getModel(gl)});
  }

  _getModel(gl) {
    return new Model(gl, Object.assign({}, this.getShaders(), {
      id: this.props.id,
      geometry: new CubeGeometry(),
      isInstanced: true
    }));
  }
}
```

Custom draw with extra uniforms:

```js
draw({uniforms}) {
  const {model} = this.state;
  model.setUniforms({...uniforms, customTime: this.props.time});
  model.draw();
}
```

---

### 1.10 Layer extensions

Use `LayerExtension` to avoid subclassing every affected layer.

```js
import {LayerExtension} from '@deck.gl/core';

const highlightUniforms = {
  name: 'highlight',
  fs: `\
uniform highlightUniforms {
  bool enabled;
} highlight;
`,
  uniformTypes: {enabled: 'f32'}
};

class RedFilter extends LayerExtension {
  getShaders(extension) {
    return {
      inject: {
        'fs:DECKGL_FILTER_COLOR': `
          if (highlight.enabled) {
            if (color.r / max(color.g, 0.001) > 2. && color.r / max(color.b, 0.001) > 2.) {
              color = vec4(1.0, 0.0, 0.0, 1.0);
            } else {
              discard;
            }
          }
        `
      },
      modules: [highlightUniforms]
    };
  }

  updateState(params) {
    const {highlightRed = true} = params.props;
    for (const model of this.getModels()) {
      model.shaderInputs.setProps({highlight: {enabled: highlightRed}});
    }
  }

  getSubLayerProps() {
    const {highlightRed = true} = this.props;
    return {highlightRed};
  }
}

// usage
new GeoJsonLayer({
  ...
  extensions: [new RedFilter()]
});
```

Extension lifecycle hooks execute relative to the host layer:

| Method | When called | Notes |
|--------|-------------|-------|
| `getShaders(extension)` | Shader assembly | Merge additional `vs`, `fs`, `modules`, `inject` |
| `initializeState(context, extension)` | after host `initializeState` | `this` is the layer |
| `updateState(params, extension)` | after host `updateState` | `params` is same as layer updateState |
| `draw(params, extension)` | before host `draw` | Useful for per-frame uniform injection |
| `finalizeState(extension)` | after host `finalizeState` | Release extension resources |
| `getSubLayerProps(extension)` | when building sublayers | Forward new props through composites |

---

### 1.11 Attribute management

The `AttributeManager` handles GPU buffer lifecycle:

1. `attributeManager.add(descriptor)` or `attributeManager.addInstanced(descriptor)` registers attributes.
2. `attributeManager.invalidate(name)` marks an attribute dirty.
3. `attributeManager.update()` rebuilds dirty attributes before rendering.

```js
this.state.attributeManager.add({
  instancePositions: {size: 3, accessor: 'getPosition'},
  instanceColors: {
    size: 4,
    type: 'uint8',
    normalized: true,
    accessor: 'getColor',
    update: this.calculateColors
  }
});

this.state.attributeManager.invalidate('instanceColors');
```

Manual buffer management:

- Applications can supply pre-built buffers as layer props for ultimate performance.
- Explicit picking index buffers only needed when logical picking id differs from rendered instance id.

Force updates after mutation:

- Increment `renderCount` to force a re-render.
- Increment `updateCount` to force buffer recalculation.

---

### 1.12 Shader writing

Include deck.gl/luma.gl shader modules in your `Model`:

```js
import {picking, project32, gouraudMaterial} from '@deck.gl/core';

const model = new Model(gl, {
  vs: CUSTOM_VS,
  fs: CUSTOM_FS,
  modules: [picking, project32, gouraudMaterial]
});
```

Key modules:

| Module | Purpose |
|--------|---------|
| `project` | Cartographic projection (lat/lon, meters, neutral / `COORDINATE_MODE`) |
| `project32` | 32-bit projection extension |
| `project64` | 64-bit projection extension |
| `gouraudMaterial` | Per-vertex lighting |
| `phongMaterial` | Per-fragment lighting |
| `picking` | Color picking helpers |
| `fp64` | Double-emulation math |

Standard shader injection hooks:

| Hook | Stage | Use |
|------|-------|-----|
| `vs:#decl` | vertex declarations | add uniforms |
| `vs:#main-start` | start of vertex main | early per-vertex logic |
| `vs:#main-end` | end of vertex main | final per-vertex logic |
| `vs:DECKGL_FILTER_SIZE` | vertex, before projection | `inout vec3 size`, `VertexGeometry geometry` |
| `vs:DECKGL_FILTER_GL_POSITION` | vertex, after projection | `inout vec4 position` |
| `vs:DECKGL_FILTER_COLOR` | vertex, after projection | `inout vec4 color` |
| `fs:#decl` | fragment declarations | add uniforms |
| `fs:#main-start` / `fs:#main-end` | fragment main entry/exit | |
| `fs:DECKGL_FILTER_COLOR` | fragment color | `inout vec4 color`, `FragmentGeometry geometry` |

`VertexGeometry` fields:

- `vec3 worldPosition`
- `vec3 worldPositionAlt`
- `vec3 normal`
- `vec2 uv`
- `vec4 position`
- `vec3 pickingColor`

`FragmentGeometry` fields:

- `vec2 uv`

Important built-in uniforms:

- `float layerIndex` — per-layer z offset
- `float opacity` — fragment opacity multiplier

Projection helpers:

- `project_position(vec3)` / `project_position_to_clipspace(...)`
- `project_scale(float)` — distance to world units
- `project_pixel_size_to_clipspace(vec2)`

Coordinate projection pattern:

```glsl
attribute vec3 positions;
attribute vec3 instancePositions;

void main(void) {
  vec3 offset = positions * project_scale(size);
  gl_Position = project_position_to_clipspace(
    instancePositions,
    vec3(0.0), // 64-bit low part
    offset,
    geometry.position
  );
}
```

Use `discard` in fragment shaders to drop fragments instead of writing alpha=0.

---

## 2. Base Maps and Integrations

### 2.1 Integration concepts

Three render modes for all base-map integrations:

| Mode | Description | Good for |
|------|-------------|----------|
| **Interleaved** | deck.gl renders into the map's own WebGL2 context; layers participate in the map layer stack | 3D occlusion, labels above/below deck.gl layers |
| **Overlaid** | deck.gl canvas sits on top of the map inside the map controls container | Using map controls/plugins without interleaving |
| **Reverse-controlled** | deck.gl root canvas drives the map as a child; deck.gl manages camera | Custom input, multiple views, non-map-centric layouts |

---

### 2.2 Mapbox / MapLibre (`@deck.gl/mapbox`)

Installation:

```bash
npm install @deck.gl/mapbox
```

Scripting bundle:

```html
<script src="https://unpkg.com/deck.gl@^9.0.0/dist.min.js"></script>
<!-- or load module dists: @deck.gl/core, @deck.gl/layers, @deck.gl/mapbox -->
<script type="text/javascript">
  const {MapboxOverlay} = deck;
</script>
```

Overlay class:

```ts
import {MapboxOverlay} from '@deck.gl/mapbox';
```

Constructor/methods:

```ts
new MapboxOverlay(props: MapboxOverlayProps);

overlay.setProps({layers: [...]});                    // update props
overlay.setProps(partialProps);                       // partial update
overlay.finalize();                                   // remove & cleanup
overlay.getCanvas();                                  // base-map canvas when interleaved
overlay.pickObject(...);                              // Delegates to Deck.pickObject
overlay.pickObjects(...);                             // Delegates to Deck.pickObjects
overlay.pickMultipleObjects(...);                     // Delegates to Deck.pickMultipleObjects
```

Key constructor options:

| Prop | Type | Meaning |
|------|------|---------|
| `interleaved` | `boolean` | `true` = render inside map's WebGL2 context; `false` = overlaid canvas. Default `false`. |
| `beforeId` | `string` | Per-layer prop; insert this deck.gl layer before the map layer with this id. Useful for interleaving. |
| `slot` | `string` | Mapbox v3 Standard Style slot prop for layer ordering. |

Notes:

- `MapboxOverlay` accepts most `Deck` props except `views`, `parent`/`canvas`/`device`, `viewState`/`initialViewState`, and `controller` is disabled.
- Internally uses a `MapView` with id `"mapbox"`.
- Mapbox v2.13+ with `useWebGL2: true` required for interleaving; mapbox v3+ supports interleaving out of the box.
- MapLibre v3+ supports interleaving (fallback to WebGL1 if WebGL2 unavailable).
- Multi-view: only one view can match the base map and receive interaction.

Standalone Mapbox example:

```ts
import {MapboxOverlay} from '@deck.gl/mapbox';
import {ScatterplotLayer} from '@deck.gl/layers';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

const map = new mapboxgl.Map({
  container: 'map',
  style: 'mapbox://styles/mapbox/light-v9',
  accessToken: '<mapbox_access_token>',
  center: [0.45, 51.47],
  zoom: 11
});

map.once('load', () => {
  const deckOverlay = new MapboxOverlay({
    interleaved: true,
    layers: [
      new ScatterplotLayer({
        id: 'deckgl-circle',
        data: [{position: [0.45, 51.47]}],
        getPosition: d => d.position,
        getFillColor: [255, 0, 0, 100],
        getRadius: 1000,
        beforeId: 'waterway-label' // render beneath this map layer
      })
    ]
  });
  map.addControl(deckOverlay);
});
```

React Mapbox example (`react-map-gl/mapbox`):

```tsx
import React from 'react';
import {Map, useControl} from 'react-map-gl/mapbox';
import {MapboxOverlay} from '@deck.gl/mapbox';
import {DeckProps} from '@deck.gl/core';
import {ScatterplotLayer} from '@deck.gl/layers';
import 'mapbox-gl/dist/mapbox-gl.css';

function DeckGLOverlay(props: DeckProps) {
  const overlay = useControl<MapboxOverlay>(() => new MapboxOverlay(props));
  overlay.setProps(props);
  return null;
}

function App() {
  const layers = [
    new ScatterplotLayer({
      id: 'deckgl-circle',
      data: [{position: [0.45, 51.47]}],
      getPosition: d => d.position,
      getFillColor: [255, 0, 0, 100],
      getRadius: 1000,
      beforeId: 'waterway-label'
    })
  ];

  return (
    <Map
      initialViewState={{
        longitude: 0.45,
        latitude: 51.47,
        zoom: 11
      }}
      mapStyle="mapbox://styles/mapbox/light-v9"
      mapboxAccessToken="<mapbox_access_token>"
    >
      <DeckGLOverlay layers={layers} interleaved />
    </Map>
  );
}
```

MapLibre standalone example:

```ts
import {MapboxOverlay} from '@deck.gl/mapbox';
import {ScatterplotLayer} from '@deck.gl/layers';
import {Map} from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

const map = new Map({
  container: 'map',
  style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
  center: [0.45, 51.47],
  zoom: 11
});

await map.once('load');

const deckOverlay = new MapboxOverlay({
  interleaved: true,
  layers: [
    new ScatterplotLayer({
      id: 'deckgl-circle',
      data: [{position: [0.45, 51.47]}],
      getPosition: d => d.position,
      getFillColor: [255, 0, 0, 100],
      getRadius: 1000,
      beforeId: 'watername_ocean'
    })
  ]
});
map.addControl(deckOverlay);
```

Reverse-controlled React example:

```tsx
import React from 'react';
import {Map} from 'react-map-gl/mapbox';
import {DeckGL} from '@deck.gl/react';
import {ScatterplotLayer} from '@deck.gl/layers';

function App() {
  const layers = [
    new ScatterplotLayer({
      id: 'deckgl-circle',
      data: [{position: [0.45, 51.47]}],
      getPosition: d => d.position,
      getFillColor: [255, 0, 0, 100],
      getRadius: 1000
    })
  ];

  return (
    <DeckGL
      initialViewState={{
        longitude: 0.45,
        latitude: 51.47,
        zoom: 11
      }}
      controller
      layers={layers}
    >
      <Map
        mapStyle="mapbox://styles/mapbox/light-v9"
        mapboxAccessToken="<mapbox_access_token>"
      />
    </DeckGL>
  );
}
```

---

### 2.3 Google Maps (`@deck.gl/google-maps`)

Installation:

```bash
npm install @deck.gl/core @deck.gl/google-maps
# scripting:
# <script src="https://unpkg.com/deck.gl@^9.0.0/dist.min.js"></script>
```

Overlay class:

```ts
import {GoogleMapsOverlay} from '@deck.gl/google-maps';
```

Constructor/methods:

```ts
new GoogleMapsOverlay(props: GoogleMapsOverlayProps);

overlay.setMap(map);          // attach; setMap(null) to detach
overlay.setProps(props);      // update partial props
overlay.finalize();         // remove & release resources
overlay.getCanvas();          // returns base-map canvas when interleaved
overlay.pickObject(...);      // same as Deck.pickObject
overlay.pickObjects(...);     // same as Deck.pickObjects
overlay.pickMultipleObjects(); // same as Deck.pickMultipleObjects
```

Constructor option:

| Prop | Type | Meaning |
|------|------|---------|
| `interleaved` | `boolean` | `true` (default) = render into vector map's WebGL2 context; `false` = overlaid canvas. |

`GoogleMapsOverlay` forwards these `Deck` props: `style`, `layers`, `effects`, `parameters`, `pickingRadius`, `useDevicePixels`, `onWebGLInitialized`, `onBeforeRender`, `onAfterRender`, `onLoad`.

Notes:

- Requires Google Maps JavaScript API loaded with a valid API key.
- Vector map: interleaved WebGL2, 3D tilt/rotation, shared z-buffer.
- Raster map: automatically falls back to overlaid mode; tilt/rotation not supported.
- Not supported: `Views`, `Controller`, React integration directly inside the overlay, gesture callbacks (`onDrag*` etc.).

Standalone example:

```ts
import {Loader} from '@googlemaps/js-api-loader';
import {GoogleMapsOverlay} from '@deck.gl/google-maps';
import {ScatterplotLayer} from '@deck.gl/layers';

const loader = new Loader({apiKey: '<google_maps_api_key>'});
const googlemaps = await loader.importLibrary('maps');

const map = new googlemaps.Map(document.getElementById('map'), {
  center: {lat: 51.47, lng: 0.45},
  zoom: 11,
  mapId: '<google_map_id>'
});

const overlay = new GoogleMapsOverlay({
  interleaved: true,
  layers: [
    new ScatterplotLayer({
      id: 'deckgl-circle',
      data: [{position: [0.45, 51.47]}],
      getPosition: d => d.position,
      getFillColor: [255, 0, 0, 100],
      getRadius: 1000
    })
  ]
});

overlay.setMap(map);
```

React example (`@vis.gl/react-google-maps`):

```tsx
import React, {useMemo, useEffect} from 'react';
import {APIProvider, Map, useMap} from '@vis.gl/react-google-maps';
import {DeckProps} from '@deck.gl/core';
import {ScatterplotLayer} from '@deck.gl/layers';
import {GoogleMapsOverlay} from '@deck.gl/google-maps';

function DeckGLOverlay(props: DeckProps) {
  const map = useMap();
  const overlay = useMemo(() => new GoogleMapsOverlay(props), []);

  useEffect(() => {
    overlay.setMap(map);
    return () => overlay.setMap(null);
  }, [map]);

  overlay.setProps(props);
  return null;
}

function App() {
  const layers = [
    new ScatterplotLayer({
      id: 'deckgl-circle',
      data: [{position: [0.45, 51.47]}],
      getPosition: d => d.position,
      getFillColor: [255, 0, 0, 100],
      getRadius: 1000
    })
  ];

  return (
    <APIProvider apiKey="<google_maps_api_key>">
      <Map
        defaultCenter={{lat: 51.47, lng: 0.45}}
        defaultZoom={11}
        mapId="<google_maps_id>"
      >
        <DeckGLOverlay layers={layers} />
      </Map>
    </APIProvider>
  );
}
```

Reverse-controlled React example:

```tsx
import React from 'react';
import {APIProvider, Map} from '@vis.gl/react-google-maps';
import {DeckGL} from '@deck.gl/react';
import {ScatterplotLayer} from '@deck.gl/layers';

function App() {
  const layers = [
    new ScatterplotLayer({
      id: 'deckgl-circle',
      data: [{position: [0.45, 51.47]}],
      getPosition: d => d.position,
      getFillColor: [255, 0, 0, 100],
      getRadius: 1000
    })
  ];

  return (
    <APIProvider apiKey="<google_maps_api_key>">
      <DeckGL
        initialViewState={{
          longitude: 0.45,
          latitude: 51.47,
          zoom: 11
        }}
        controller
        layers={layers}
      >
        <Map mapId="<google_maps_id>" />
      </DeckGL>
    </APIProvider>
  );
}
```

---

### 2.4 ArcGIS (`@deck.gl/arcgis`)

Installation:

```bash
npm install @deck.gl/core @deck.gl/arcgis @arcgis/core
# or with esri-loader:
npm install @deck.gl/core @deck.gl/arcgis
```

Scripting bundle:

```html
<script src="https://unpkg.com/deck.gl@^9.0.0/dist.min.js"></script>
<script src="https://unpkg.com/@deck.gl/arcgis@^1.0.0/dist.min.js"></script>
<script type="text/javascript">
  deck.loadArcGISModules();
</script>
```

ArcGIS-specific classes:

| Class | Import | Use |
|-------|--------|-----|
| `DeckLayer` | `import {DeckLayer} from '@deck.gl/arcgis';` | 2D `MapView` integration; inherits ArcGIS `Layer` |
| `DeckRenderer` | `import {DeckRenderer} from '@deck.gl/arcgis';` | Experimental 3D `SceneView` integration |
| `loadArcGISModules` | `import {loadArcGISModules} from '@deck.gl/arcgis';` | Async loader for AMD/esri-loader projects |

`DeckLayer` usage:

```js
import {DeckLayer} from '@deck.gl/arcgis';
import {ScatterplotLayer} from '@deck.gl/layers';
import ArcGISMap from '@arcgis/core/Map';
import MapView from '@arcgis/core/views/MapView';

const layer = new DeckLayer({
  'deck.layers': [
    new ScatterplotLayer({
      data: [{position: [0.119, 52.205]}],
      getPosition: d => d.position,
      getColor: [255, 0, 0],
      radiusMinPixels: 20
    })
  ]
});

const mapView = new MapView({
  container: 'viewDiv',
  map: new ArcGISMap({
    basemap: 'dark-gray-vector',
    layers: [layer]
  }),
  center: [0.119, 52.205],
  zoom: 5
});
```

Update props after construction:

```js
layer.deck.layers = [...];
layer.deck.set({
  layers: [...],
  pickingRadius: 5
  // ...
});
```

`DeckLayer` forwarded `Deck` props (all prefixed `deck.`):

- `deck.layers`
- `deck.layerFilter`
- `deck.parameters`
- `deck.effects`
- `deck.pickingRadius`
- `deck.onBeforeRender`
- `deck.onAfterRender`
- `deck.onClick`
- `deck.onHover`
- `deck.onDragStart`
- `deck.onDrag`
- `deck.onDragEnd`
- `deck.onError`
- `deck.debug`
- `deck.drawPickingColors`
- `deck.getCursor`
- `deck.getTooltip`

`DeckRenderer` usage (experimental; `viewingMode: 'local'` required):

```js
import {DeckRenderer} from '@deck.gl/arcgis';
import {ScatterplotLayer} from '@deck.gl/layers';
import ArcGISMap from '@arcgis/core/Map';
import SceneView from '@arcgis/core/views/SceneView';
import * as externalRenderers from '@arcgis/core/views/3d/externalRenderers';

const sceneView = new SceneView({
  container: 'viewDiv',
  map: new ArcGISMap({basemap: 'dark-gray-vector'}),
  camera: {
    position: {x: -74, y: 40.65, z: 5000},
    heading: 180,
    tilt: 30
  },
  viewingMode: 'local'
});

const renderer = new DeckRenderer(sceneView, {
  layers: [
    new ScatterplotLayer({
      data: [{position: [0.119, 52.205]}],
      getPosition: d => d.position,
      getColor: [255, 0, 0],
      radiusMinPixels: 20
    })
  ]
});

externalRenderers.add(sceneView, renderer);

// update later
renderer.deck.layers = [...];
renderer.deck.set({layers: [...], pickingRadius: 5});
```

`loadArcGISModules` for esri-loader/AMD workflows:

```js
import {loadArcGISModules} from '@deck.gl/arcgis';

loadArcGISModules(['esri/Map', 'esri/views/MapView'], {version: '4.21'})
  .then(({DeckLayer, DeckRenderer, modules}) => {
    const [ArcGISMap, MapView] = modules;

    const layer = new DeckLayer({
      'deck.layers': [
        new ScatterplotLayer({
          data: [{position: [0.119, 52.205]}],
          getPosition: d => d.position,
          getColor: [255, 0, 0],
          radiusMinPixels: 20
        })
      ]
    });

    new MapView({
      container: 'viewDiv',
      map: new ArcGISMap({basemap: 'dark-gray-vector', layers: [layer]}),
      center: [0.119, 52.205],
      zoom: 5
    });
  });
```

ArcGIS limitations:

- Multiple views and `Controller` not supported.
- React integration not supported.

---

### 2.5 CARTO (`@deck.gl/carto`)

Installation:

```bash
npm install @deck.gl/core @deck.gl/layers @deck.gl/geo-layers @deck.gl/carto
```

Scripting bundle:

```html
<script src="https://unpkg.com/deck.gl@^9.0.0/dist.min.js"></script>
<script src="https://unpkg.com/@deck.gl/carto@^9.0.0/dist.min.js"></script>
<script type="text/javascript">
  // access via deck.carto.
  const layer = new deck.carto.VectorTileLayer({});
</script>
```

CARTO layers:

| Layer | Import | Data source helpers |
|-------|--------|---------------------|
| `VectorTileLayer` | `import {VectorTileLayer} from '@deck.gl/carto';` | `vectorTableSource`, `vectorQuerySource`, `vectorTilesetSource` |
| `H3TileLayer` | `import {H3TileLayer} from '@deck.gl/carto';` | `h3TableSource`, `h3QuerySource`, `h3TilesetSource` |
| `QuadbinTileLayer` | `import {QuadbinTileLayer} from '@deck.gl/carto';` | `quadbinTableSource`, `quadbinQuerySource`, `quadbinTilesetSource` |
| `RasterTileLayer` | `import {RasterTileLayer} from '@deck.gl/carto';` | `rasterSource` |
| `HeatmapTileLayer` | `import {HeatmapTileLayer} from '@deck.gl/carto';` | — |
| `ClusterTileLayer` | `import {ClusterTileLayer} from '@deck.gl/carto';` | — |
| `PointLabelLayer` | `import {PointLabelLayer} from '@deck.gl/carto';` | — |

Data sources are provided by `@carto/api-client`:

```js
import {
  vectorTableSource,
  vectorQuerySource,
  vectorTilesetSource,
  h3TableSource,
  h3QuerySource,
  h3TilesetSource,
  quadbinTableSource,
  quadbinQuerySource,
  quadbinTilesetSource,
  rasterSource,
  boundaryTableSource,
  boundaryQuerySource
} from '@carto/api-client';
```

Global source options:

```ts
type SourceOptions = {
  accessToken: string;
  connectionName: string;
  apiBaseUrl?: string;
  clientId?: string;
  headers?: Record<string, string>;
  maxLengthURL?: number;
};
```

React VectorTileLayer example:

```tsx
import {DeckGL} from '@deck.gl/react';
import {VectorTileLayer} from '@deck.gl/carto';
import {vectorQuerySource} from '@carto/api-client';

function App() {
  const data = vectorQuerySource({
    accessToken: 'XXX',
    connectionName: 'carto_dw',
    sqlQuery: 'SELECT * FROM cartobq.testtables.points_10k',
  });

  const layer = new VectorTileLayer({
    data,
    pointRadiusMinPixels: 2,
    getLineColor: [0, 0, 0, 200],
    getFillColor: [238, 77, 90],
    lineWidthMinPixels: 1
  });

  return <DeckGL layers={[layer]} />;
}
```

`fetchMap` — load a map configured in CARTO Builder:

```js
import {Deck} from '@deck.gl/core';
import {fetchMap} from '@deck.gl/carto';

const cartoMapId = 'ff6ac53f-741a-49fb-b615-d040bc5a96b8';
fetchMap({cartoMapId}).then(map => new Deck(map));
```

`fetchMap` with MapLibre/CARTO basemap:

```js
import {fetchMap} from '@deck.gl/carto';
import {MapboxOverlay} from '@deck.gl/mapbox';
import maplibregl from 'maplibre-gl';

fetchMap({cartoMapId}).then(({basemap, layers}) => {
  const map = new maplibregl.Map({
    container: 'map',
    ...basemap?.props,
    interactive: true
  });
  const overlay = new MapboxOverlay({layers});
  map.addControl(overlay);
});
```

`fetchMap` options:

| Parameter | Type | Meaning |
|-----------|------|---------|
| `cartoMapId` | `string` | Builder map id (required) |
| `accessToken` | `string` | Required for private maps |
| `apiBaseUrl` | `string` | CARTO Maps API base URL |
| `headers` | `object` | Custom HTTP headers |
| `autoRefresh` | `number` | Auto-refresh interval in seconds |
| `onNewData` | `Function` | Callback when data changes (required if `autoRefresh` set) |

Return value fields: `id`, `title`, `description`, `createdAt`, `updatedAt`, `initialViewState`, `layers`, `basemap`, `stopAutoRefresh`.

`basemap` object contains:

- `type`: `'maplibre'` | `'google-maps'`
- `props`: basemap initialization props
- `rawStyle`: original MapLibre style (if applicable)
- `visibleLayerGroups`: optional layer group filters
- `attribution`: optional attribution HTML

CARTO free basemap styles (`BASEMAP`):

```js
import {BASEMAP} from '@deck.gl/carto';

// with react-map-gl/maplibre
<Map mapStyle={BASEMAP.POSITRON} />
// standalone MapLibre
new maplibregl.Map({style: deck.carto.BASEMAP.POSITRON, ...});
```

Available constants:

- `BASEMAP.POSITRON`
- `BASEMAP.DARK_MATTER`
- `BASEMAP.VOYAGER`
- `BASEMAP.POSITRON_NOLABELS`
- `BASEMAP.DARK_MATTER_NOLABELS`
- `BASEMAP.VOYAGER_NOLABELS`

React CARTO basemap example (deck.gl controls camera):

```jsx
import {DeckGL} from '@deck.gl/react';
import {Map} from 'react-map-gl/maplibre';
import {BASEMAP} from '@deck.gl/carto';

<DeckGL initialViewState={INITIAL_VIEW_STATE} controller={true} layers={layers}>
  <Map mapStyle={BASEMAP.POSITRON} />
</DeckGL>;
```

Standalone CARTO basemap + deck.gl:

```js
const map = new maplibregl.Map({
  container: 'map',
  style: deck.carto.BASEMAP.POSITRON,
  interactive: false
});

const deckgl = new deck.DeckGL({
  canvas: 'deck-canvas',
  initialViewState: {latitude: 0, longitude: 0, zoom: 1},
  onViewStateChange: ({viewState}) => {
    const {longitude, latitude, ...rest} = viewState;
    map.jumpTo({center: [longitude, latitude], ...rest});
  },
  controller: true
});
```

---

## 3. One-page import map

```js
// Core primitives
import {Layer, CompositeLayer, LayerExtension, picking, project32, gouraudMaterial} from '@deck.gl/core';

// Base-map overlays
import {MapboxOverlay} from '@deck.gl/mapbox';
import {GoogleMapsOverlay} from '@deck.gl/google-maps';
import {DeckLayer, DeckRenderer, loadArcGISModules} from '@deck.gl/arcgis';

// CARTO
import {VectorTileLayer, H3TileLayer, QuadbinTileLayer, RasterTileLayer, HeatmapTileLayer, ClusterTileLayer, PointLabelLayer, fetchMap, BASEMAP} from '@deck.gl/carto';
import {vectorQuerySource, vectorTableSource} from '@carto/api-client';

// Common layers
import {ScatterplotLayer, PathLayer, GeoJsonLayer, IconLayer, TextLayer, PointCloudLayer, SolidPolygonLayer} from '@deck.gl/layers';
```
