---
name: deckgl-basemap
description: |
  Integrate deck.gl with Mapbox GL JS, MapLibre GL JS, Google Maps, ArcGIS, or CARTO. Use when the user wants a basemap under deck.gl layers, wants deck.gl as an overlay on an existing map library, or needs CARTO vector/raster tile layers and styles. Also use for 3D Tiles/I3S content with Google Maps.
compatibility: |
  Requires code-generation tools. No runtime dependency (but real apps need map library API keys and packages).
---

# deck.gl base map integration skill

You generate correct integration code for deck.gl with each supported map library. Reference file: `references/custom-layers-basemaps.md` Section 2.

## MapLibre / Mapbox GL JS — choose the mode

There are three integration modes. Pick the one that matches the user's needs.

### 1. Interleaved (deck.gl renders inside the map WebGL context)

Best for mixing deck.gl layers with map labels/3D and proper occlusion. Requires WebGL2 (`maplibre-gl@>3`).

```jsx
import {Map, useControl} from 'react-map-gl/maplibre';
import {MapboxOverlay} from '@deck.gl/mapbox';
import {ScatterplotLayer} from '@deck.gl/layers';
import 'maplibre-gl/dist/maplibre-gl.css';

function DeckGLOverlay(props) {
  const overlay = useControl(() => new MapboxOverlay(props));
  overlay.setProps(props);
  return null;
}

function App() {
  const layers = [new ScatterplotLayer({id: 'points', data, getPosition: d => d.position})];
  return (
    <Map
      initialViewState={{longitude: 0.45, latitude: 51.47, zoom: 11}}
      mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
    >
      <DeckGLOverlay layers={layers} interleaved />
    </Map>
  );
}
```

### 2. Overlaid (separate deck.gl canvas on top)

Like interleaved, but `MapboxOverlay` with `interleaved: false`.

### 3. Reverse-controlled (DeckGL is the root component)

Use this when you need your own pointer controllers, multiple views, or widgets instead of native map controls.

```jsx
import {DeckGL} from '@deck.gl/react';
import {Map} from 'react-map-gl/maplibre';
import {GeoJsonLayer} from '@deck.gl/layers';
import 'maplibre-gl/dist/maplibre-gl.css';

function App() {
  const layers = [new GeoJsonLayer({id: 'geojson', data})];
  return (
    <DeckGL
      layers={layers}
      initialViewState={{longitude: -122.4, latitude: 37.7, zoom: 10}}
      controller
    >
      <Map mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json" />
    </DeckGL>
  );
}
```

> For Mapbox GL JS, replace `react-map-gl/maplibre` with `react-map-gl/mapbox` and `maplibre-gl` with `mapbox-gl`.

## Google Maps

```jsx
import {GoogleMapsOverlay} from '@deck.gl/google-maps';

const overlay = new GoogleMapsOverlay({layers});
overlay.setMap(map); // google.maps.Map instance
```

- Package: `@deck.gl/google-maps`.
- Requires Google Maps JS API loaded.
- Set `interleaved: true` if you need depth/occlusion.

## ArcGIS

```js
import {DeckLayer} from '@deck.gl/arcgis';
import {loadArcGISModules} from '@deck.gl/arcgis';

const {DeckLayer} = await loadArcGISModules();
const layer = new DeckLayer({layers: [new ScatterplotLayer({...})]});
map.layers.add(layer);
```

- Package: `@deck.gl/arcgis`.

## CARTO (default)

```js
import {VectorTileLayer, fetchMap} from '@deck.gl/carto';
import {setDefaultCredentials} from '@deck.gl/carto';

setDefaultCredentials({accessToken: '...', apiBaseUrl: 'https://gcp-us-east1.api.carto.com'});
const layers = await fetchMap({cartoMapId: '...'});
```

- Use `VectorTileLayer`, `RasterTileLayer`, `H3TileLayer`, `QuadbinTileLayer`, etc.

## Output

- State the required npm packages.
- Provide a complete integration snippet for the chosen map library and integration mode.
- Note API-key/token requirements and any important constructor options.
