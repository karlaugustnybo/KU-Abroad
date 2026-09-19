# deck.gl Layer Reference (codegen skill)

Auto-generated structured reference for the deck.gl 9.x layer catalog.
All layers inherit from [`Layer`](https://deck.gl/docs/api-reference/core/layer) (and from [`CompositeLayer`](https://deck.gl/docs/api-reference/core/composite-layer) where noted), so base-props such as `id`, `data`, `visible`, `opacity`, `pickable`, `autoHighlight`, `highlightColor`, `onHover`, `onClick`, `onDrag`, `onDrop`, `modelMatrix`, `coordinateSystem`, `coordinateOrigin`, `positionFormat`, `colorFormat`, `parameters`, `extensions`, `transitions`, `updateTriggers`, `loaders`, `loadOptions`, etc. are assumed available and are not repeated unless they are documented layer-specific.

Color type is `[r,g,b,[a]]` 0-255, alpha defaults to 255. `Accessor<T>` means a constant value or `d => T`. Position is typically `[x,y]` or `[x,y,z]`. Unit strings are `'meters' | 'common' | 'pixels'` unless otherwise stated. Transitions are enabled on many accessors/number props when `transitions` is configured.

---

## Core Layers (`@deck.gl/layers`)

### ArcLayer
- **Class:** `ArcLayer<DataT>`
- **Import:** `import {ArcLayer} from '@deck.gl/layers';`
- **Description:** Raised arcs between source/target positions.
- **Render props:**
  - `greatCircle` boolean default `false` — shortest path on earth surface in LNGLAT mode.
  - `numSegments` number default `50`.
  - `widthUnits` string default `'pixels'`.
  - `widthScale` number default `1`.
  - `widthMinPixels` number default `0`.
  - `widthMaxPixels` number default `Number.MAX_SAFE_INTEGER`.
  - `getHeight` Accessor<number> default `1` — multiplier of arc height, `0` = flat.
  - `getTilt` Accessor<number> default `0` (degrees, -90..90).
- **Accessors:**
  - `getSourcePosition` Accessor<Position> default `d => d.sourcePosition`.
  - `getTargetPosition` Accessor<Position> default `d => d.targetPosition`.
  - `getSourceColor` Accessor<Color> default `[0,0,0,255]`.
  - `getTargetColor` Accessor<Color> default `[0,0,0,255]`.
  - `getWidth` Accessor<number> default `1`.
- **Events:** Standard `onHover`/`onClick` via `PickingInfo<DataT>`, `object` is the data row.
- **Limitations:** With `GlobeView`/MapLibre globe back-face culling may hide arcs; add `parameters: {cullMode: 'none'}`.
- **Snippet:**
  ```js
  new ArcLayer({
    id: 'ArcLayer',
    data: '//raw.githubusercontent.com/visgl/deck.gl-data/master/website/bart-segments.json',
    getSourcePosition: d => d.from.coordinates,
    getTargetPosition: d => d.to.coordinates,
    getSourceColor: d => [Math.sqrt(d.inbound), 140, 0],
    getTargetColor: d => [Math.sqrt(d.outbound), 140, 0],
    getWidth: 12,
    pickable: true
  });
  ```

### BitmapLayer
- **Class:** `BitmapLayer`
- **Import:** `import {BitmapLayer, BitmapLayerPickingInfo} from '@deck.gl/layers';`
- **Description:** Static image textured onto a bounding box.
- **Data/Render props:**
  - `image` string | Texture | Image | ImageData | Canvas | Video | ImageBitmap | Promise | object — default `null`. URL/Data URL accepted.
  - `bounds` number[4] | Position[4] — `[left,bottom,right,top]` or four corners `[[lb],[lt],[rt],[rb]]`, optional z's.
  - `loadOptions` object.
  - `textureParameters` object; default `{minFilter:'linear',magFilter:'linear',mipmapFilter:'linear',addressModeU:'clamp-to-edge',addressModeV:'clamp-to-edge'}`.
  - `_imageCoordinateSystem` `'default' | 'lnglat' | 'cartesian'` default `'default'` (experimental).
  - `desaturate` number default `0` (0..1).
  - `transparentColor` Color default `[0,0,0,0]`.
  - `tintColor` Color default `[255,255,255]`.
- **Accessors:** none by data object (image-driven).
- **Picking:** `PickingInfo.bitmap` contains `{pixel, size:{width,height}, uv}`; may be `null` on mouse leave or before load.
- **Limitations:** Pick pixel color via `layer.context.device.readPixelsToArrayWebGL` if needed.
- **Snippet:**
  ```js
  new BitmapLayer({
    id: 'BitmapLayer',
    bounds: [-122.519, 37.7045, -122.355, 37.829],
    image: 'https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/sf-districts.png',
    pickable: true
  });
  ```

### ColumnLayer
- **Class:** `ColumnLayer<DataT>`
- **Import:** `import {ColumnLayer} from '@deck.gl/layers';`
- **Description:** Extruded regular-polygon columns at positions.
- **Render props:**
  - `diskResolution` number default `20` — sides of polygon.
  - `radius` number default `1000` meters.
  - `angle` number default `0` degrees CCW.
  - `vertices` Position[] default regular polygon; custom vertices relative to radius.
  - `offset` number[2] default `[0,0]` — relative to radius.
  - `coverage` number default `1` (0..1).
  - `elevationScale` number default `1`.
  - `filled` boolean default `true`.
  - `stroked` boolean default `false` (only when `extruded: false`).
  - `extruded` boolean default `true`.
  - `wireframe` boolean default `false`.
  - `flatShading` boolean default `false`.
  - `radiusUnits` string default `'meters'`.
  - `lineWidthUnits` string default `'meters'`.
  - `lineWidthScale` number default `1`.
  - `lineWidthMinPixels` number default `0`.
  - `lineWidthMaxPixels` number default `Number.MAX_SAFE_INTEGER`.
  - `material` Material default `true`.
- **Accessors:**
  - `getPosition` Accessor<Position> default `d => d.position`.
  - `getFillColor` Accessor<Color> default `[0,0,0,255]`; falls back to `getColor`.
  - `getLineColor` Accessor<Color> default `[0,0,0,255]`; outline.
  - `getElevation` Accessor<number> default `1000` meters.
  - `getLineWidth` Accessor<number> default `1`.
- **Events:** `PickingInfo<DataT>`, `object` is the original row.
- **Limitations:** none documented.
- **Snippet:**
  ```js
  new ColumnLayer({
    id: 'ColumnLayer',
    data: 'https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/hexagons.json',
    diskResolution: 12,
    radius: 250,
    extruded: true,
    elevationScale: 5000,
    getPosition: d => d.centroid,
    getElevation: d => d.value,
    getFillColor: d => [48, 128, d.value * 255, 255],
    pickable: true
  });
  ```

### GeoJsonLayer
- **Class:** `GeoJsonLayer<FeaturePropertiesT>`
- **Import:** `import {GeoJsonLayer} from '@deck.gl/layers';`
- **Description:** Composite layer rendering GeoJSON as polygons, lines, points.
- **Sub-layers:** `polygons-fill` (SolidPolygonLayer), `polygons-stroke` (PathLayer), `linestrings` (PathLayer), `points-circle` (ScatterplotLayer), `points-icon` (IconLayer), `points-text` (TextLayer).
- **Data prop:** GeoJSON `FeatureCollection | Feature | Geometry | GeometryCollection`, array of `Feature`, URL/Promise, or loaders.gl flat GeoJSON binary.
- **Render props:**
  - `pointType` `'circle' | 'icon' | 'text'`, combinable with `+`, default `'circle'`.
  - Fill: `filled` default `true`; `getFillColor` default `[0,0,0,255]`.
  - Stroke: `stroked` default `true`; `getLineColor` default `[0,0,0,255]`; `getLineWidth` default `1`; `lineWidthUnits` default `'meters'`; `lineWidthScale` default `1`; `lineWidthMinPixels` default `0`; `lineWidthMaxPixels` default `Number.MAX_SAFE_INTEGER`; `lineCapRounded` default `false`; `lineJointRounded` default `false`; `lineMiterLimit` default `4`; `lineBillboard` default `false`.
  - 3D: `extruded` default `false`; `wireframe` default `false`; `getElevation` default `1000`; `elevationScale` default `1`; `material` default `true`; `_full3d` default `false` (experimental).
  - forwarded point props: `getPointRadius`, `pointRadiusUnits`, `pointRadiusScale`, `pointRadiusMinPixels`, `pointRadiusMaxPixels`, `pointAntialiasing`, `pointBillboard`; icon/text variants prefixed `icon*` and `text*` mapping to IconLayer/TextLayer props (see docs).
- **Accessors:** as above plus `getPosition` is not used directly ( geometry comes from GeoJSON).
- **Events:** `PickingInfo<Feature<Geometry, FeaturePropertiesT>>`, `object` is the picked GeoJSON feature.
- **Limitations:** Input data must be valid RFC7946 GeoJSON. Binary attributes pass per-geometry via `data.{points,lines,polygons}.attributes`. Geometry transition via `transitions: {geometry}`.
- **Snippet:**
  ```js
  new GeoJsonLayer({
    id: 'GeoJsonLayer',
    data: 'https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/bart.geo.json',
    stroked: false,
    filled: true,
    pointType: 'circle+text',
    getFillColor: [160, 160, 180, 200],
    getLineColor: f => (f.properties.color ? parseColor(f.properties.color) : [0,0,0]),
    getLineWidth: 20,
    getPointRadius: 4,
    getText: f => f.properties.name,
    getTextSize: 12,
    pickable: true
  });
  ```

### GridCellLayer
- **Class:** `GridCellLayer<DataT>`
- **Import:** `import {GridCellLayer} from '@deck.gl/layers';`
- **Description:** Primitive layer for grid-cell extrusions; one cell per data row.
- **Render props:**
  - `cellSize` number default `1000` meters.
  - `coverage` number default `1`.
  - `elevationScale` number default `1`.
  - `extruded` boolean default `true`.
  - `material` Material default `true`.
- **Accessors:**
  - `getPosition` Accessor<Position> default `d => d.position` — bottom-left `[minX,minY]`.
  - `getColor` Accessor<Color> default `[255,0,255,255]`.
  - `getElevation` Accessor<number> default `1000`.
- **Events:** `PickingInfo<DataT>`.
- **Limitations:** none documented.
- **Snippet:**
  ```js
  new GridCellLayer({
    id: 'GridCellLayer',
    data: 'https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/hexagons.json',
    cellSize: 200,
    extruded: true,
    elevationScale: 5000,
    getPosition: d => d.centroid,
    getElevation: d => d.value,
    getFillColor: d => [48, 128, d.value * 255, 255],
    pickable: true
  });
  ```

### IconLayer
- **Class:** `IconLayer<DataT>`
- **Import:** `import {IconLayer} from '@deck.gl/layers';`
- **Description:** Raster icons at positions; supports pre-packed atlas or auto-packing.
- **Render props:**
  - `iconAtlas` string | Texture | image... | object — pre-packed atlas; required for pre-packed.
  - `iconMapping` object | string — `{name:{x,y,width,height,anchorX?,anchorY?,mask?}}`; required for pre-packed.
  - `sizeScale` number default `1`.
  - `sizeBasis` `'height' | 'width'` default `'height'`.
  - `sizeUnits` string default `'pixels'`.
  - `sizeMinPixels` number default `0`.
  - `sizeMaxPixels` number default `Number.MAX_SAFE_INTEGER`.
  - `billboard` boolean default `true`.
  - `alphaCutoff` number default `0.05`.
  - `loadOptions`, `textureParameters`.
- **Accessors:**
  - `getIcon` Accessor<string | object> default `d => d.icon`.
    - Pre-packed: string name from `iconMapping`.
    - Auto-packing: object `{url,width,height,id?,anchorX?,anchorY?,mask?}`.
  - `getPosition` Accessor<Position> default `d => d.position`.
  - `getSize` Accessor<number> default `1`.
  - `getColor` Accessor<Color> default `[0,0,0,255]`; if `mask:false` only alpha used.
  - `getAngle` Accessor<number> default `0`.
  - `getPixelOffset` Accessor<number[2]> default `[0,0]`.
- **Callbacks:** `onIconError` default `null` — called for failed auto-packing fetches.
- **Events:** `PickingInfo<DataT>`.
- **Limitations:** Auto-packing is less efficient. For binary `data.attributes.getIcon`, `iconMapping` keys must be integers.
- **Snippet:**
  ```js
  new IconLayer({
    id: 'IconLayer',
    data: 'https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/bart-stations.json',
    iconAtlas: 'https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/icon-atlas.png',
    iconMapping: 'https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/icon-atlas.json',
    getPosition: d => d.coordinates,
    getIcon: d => 'marker',
    getSize: 40,
    getColor: d => [Math.sqrt(d.exits), 140, 0],
    pickable: true
  });
  ```

### LineLayer
- **Class:** `LineLayer<DataT>`
- **Import:** `import {LineLayer} from '@deck.gl/layers';`
- **Description:** Straight lines joining source/target positions.
- **Render props:**
  - `widthUnits` string default `'pixels'`.
  - `widthScale` number default `1`.
  - `widthMinPixels` number default `0`.
  - `widthMaxPixels` number default `Number.MAX_SAFE_INTEGER`.
- **Accessors:**
  - `getSourcePosition` Accessor<Position> default `d => d.sourcePosition`.
  - `getTargetPosition` Accessor<Position> default `d => d.targetPosition`.
  - `getColor` Accessor<Color> default `[0,0,0,255]`.
  - `getWidth` Accessor<number> default `1`.
- **Events:** `PickingInfo<DataT>`.
- **Limitations:** With `GlobeView`/`MapLibre` globe use `parameters: {cullMode: 'none'}`.
- **Snippet:**
  ```js
  new LineLayer({
    id: 'LineLayer',
    data: 'https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/bart-segments.json',
    getSourcePosition: d => d.from.coordinates,
    getTargetPosition: d => d.to.coordinates,
    getColor: d => [Math.sqrt(d.inbound + d.outbound), 140, 0],
    getWidth: 12,
    pickable: true
  });
  ```

### PathLayer
- **Class:** `PathLayer<DataT>`
- **Import:** `import {PathLayer} from '@deck.gl/layers';`
- **Description:** Extruded polylines / paths with mitering.
- **Render props:**
  - `widthUnits` string default `'meters'`.
  - `widthScale` number default `1`.
  - `widthMinPixels` number default `0`.
  - `widthMaxPixels` number default `Number.MAX_SAFE_INTEGER`.
  - `capRounded` boolean default `false`.
  - `jointRounded` boolean default `false`.
  - `billboard` boolean default `false`.
  - `miterLimit` number default `4`.
  - `_pathType` `null | 'loop' | 'open'` default `null` (experimental, skip normalization).
- **Accessors:**
  - `getPath` Accessor<PathGeometry> default `d => d.path` — array of `[x,y,z]` or flat array (use `positionFormat:'XY'` for xy-only).
  - `getColor` Accessor<Color> default `[0,0,0,255]`.
  - `getWidth` Accessor<number> default `1`.
- **Events:** `PickingInfo<DataT>`.
- **Limitations:** With `GlobeView`/`MapLibre` globe use `parameters: {cullMode: 'none'}`. For binary attributes supply `data.startIndices`.
- **Snippet:**
  ```js
  new PathLayer({
    id: 'PathLayer',
    data: 'https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/bart-lines.json',
    getPath: d => d.path,
    getColor: d => parseColor(d.color),
    getWidth: 100,
    pickable: true
  });
  ```

### PointCloudLayer
- **Class:** `PointCloudLayer<DataT>`
- **Import:** `import {PointCloudLayer} from '@deck.gl/layers';`
- **Description:** 3D point cloud with positions/normals/colors.
- **Render props:**
  - `sizeUnits` string default `'pixels'` (also `'meters' | 'common'`).
  - `pointSize` number default `10`.
  - `material` Material default `true`.
- **Accessors:**
  - `getPosition` Accessor<Position> default `d => d.position`.
  - `getNormal` Accessor<number[3]> default `[0,0,1]`.
  - `getColor` Accessor<Color> default `[0,0,0,255]`.
- **Events:** `PickingInfo<DataT>`.
- **Limitations:** none documented.
- **Snippet:**
  ```js
  new PointCloudLayer({
    id: 'PointCloudLayer',
    data: 'https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/pointcloud.json',
    getPosition: d => d.position,
    getColor: d => d.color,
    getNormal: d => d.normal,
    pointSize: 2,
    coordinateSystem: 'meter-offsets',
    coordinateOrigin: [-122.4, 37.74],
    pickable: true
  });
  ```

### PolygonLayer
- **Class:** `PolygonLayer<DataT>`
- **Import:** `import {PolygonLayer} from '@deck.gl/layers';`
- **Description:** Composite layer over SolidPolygonLayer + PathLayer.
- **Sub-layers:** `fill`, `stroke`.
- **Render props:**
  - `filled` boolean default `true`.
  - `stroked` boolean default `true`.
  - `extruded` boolean default `false`.
  - `wireframe` boolean default `false`.
  - `elevationScale` number default `1`.
  - `lineWidthUnits` string default `'meters'`.
  - `lineWidthScale` number default `1`.
  - `lineWidthMinPixels` number default `0`.
  - `lineWidthMaxPixels` number default `Number.MAX_SAFE_INTEGER`.
  - `lineJointRounded` boolean default `false`.
  - `lineMiterLimit` number default `4`.
  - `material` Material default `true`.
  - `_normalize` boolean default `true` (experimental).
  - `_windingOrder` `'CW'|'CCW'` default `'CW'` (experimental).
- **Accessors:**
  - `getPolygon` Accessor<PolygonGeometry> default `d => d.polygon`.
  - `getFillColor` Accessor<Color> default `[0,0,0,255]`.
  - `getLineColor` Accessor<Color> default `[0,0,0,255]`.
  - `getLineWidth` Accessor<number> default `1`.
  - `getElevation` Accessor<number> default `1000`.
- **Events:** `PickingInfo<DataT>`.
- **Limitations:** 3D polygon vertices add altitude via `z`. Wireframe is `GL.LINE` 1px. Wireframe and solid extrusion are exclusive; create two layers for combined look.
- **Snippet:**
  ```js
  new PolygonLayer({
    id: 'PolygonLayer',
    data: 'https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/sf-zipcodes.json',
    getPolygon: d => d.contour,
    getElevation: d => d.population / d.area / 10,
    getFillColor: d => [d.population / d.area / 60, 140, 0],
    getLineColor: [255, 255, 255],
    getLineWidth: 20,
    lineWidthMinPixels: 1,
    pickable: true
  });
  ```

### ScatterplotLayer
- **Class:** `ScatterplotLayer<DataT>`
- **Import:** `import {ScatterplotLayer} from '@deck.gl/layers';`
- **Description:** Circles at positions.
- **Render props:**
  - `radiusUnits` string default `'meters'`.
  - `radiusScale` number default `1`.
  - `lineWidthUnits` string default `'meters'`.
  - `lineWidthScale` number default `1`.
  - `stroked` boolean default `false`.
  - `filled` boolean default `true`.
  - `radiusMinPixels` number default `0`.
  - `radiusMaxPixels` number default `Number.MAX_SAFE_INTEGER`.
  - `lineWidthMinPixels` number default `0`.
  - `lineWidthMaxPixels` number default `Number.MAX_SAFE_INTEGER`.
  - `billboard` boolean default `false`.
  - `antialiasing` boolean default `true`.
- **Accessors:**
  - `getPosition` Accessor<Position> default `d => d.position`.
  - `getRadius` Accessor<number> default `1`.
  - `getColor` Accessor<Color> default `[0,0,0,255]` (overridden by `getFillColor`/`getLineColor`).
  - `getFillColor` Accessor<Color> default `[0,0,0,255]`; fallback to `getColor`.
  - `getLineColor` Accessor<Color> default `[0,0,0,255]`; fallback to `getColor`.
  - `getLineWidth` Accessor<number> default `1`.
  - `getPixelOffset` Accessor<number[2]> default `[0,0]`.
- **Events:** `PickingInfo<DataT>`.
- **Limitations:** antialiasing can cause artifacts at overlapping edges and not supported in `FirstPersonView`.
- **Snippet:**
  ```js
  new ScatterplotLayer({
    id: 'ScatterplotLayer',
    data: 'https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/bart-stations.json',
    getPosition: d => d.coordinates,
    getRadius: d => Math.sqrt(d.exits),
    getFillColor: [255, 140, 0],
    getLineColor: [0, 0, 0],
    getLineWidth: 10,
    radiusScale: 6,
    pickable: true
  });
  ```

### SolidPolygonLayer
- **Class:** `SolidPolygonLayer<DataT>`
- **Import:** `import {SolidPolygonLayer} from '@deck.gl/layers';`
- **Description:** Primitive filled/extruded polygon layer.
- **Render props:**
  - `filled` boolean default `true`.
  - `extruded` boolean default `false`.
  - `wireframe` boolean default `false`.
  - `elevationScale` number default `1`.
  - `material` Material default `true`.
  - `_normalize` boolean default `true` (experimental).
  - `_windingOrder` `'CW'|'CCW'` default `'CW'` (experimental).
  - `_full3d` boolean default `false` (experimental).
- **Accessors:**
  - `getPolygon` Accessor<PolygonGeometry> default `d => d.polygon`.
  - `getFillColor` Accessor<Color> default `[0,0,0,255]`.
  - `getLineColor` Accessor<Color> default `[0,0,0,255]` (only when `extruded: true`).
  - `getElevation` Accessor<number> default `1000`.
- **Events:** `PickingInfo<DataT>`.
- **Limitations:** Does not render outlines; use PathLayer. Closed polygons; follows GeoJSON holes convention. For binary attributes supply `data.startIndices` and `data.attributes.vertexValid` for polygons with holes.
- **Snippet:**
  ```js
  new SolidPolygonLayer({
    id: 'SolidPolygonLayer',
    data: 'https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/sf-zipcodes.json',
    extruded: true,
    wireframe: true,
    getPolygon: d => d.contour,
    getElevation: d => d.population / d.area / 10,
    getFillColor: d => [d.population / d.area / 60, 140, 0],
    getLineColor: [80, 80, 80],
    pickable: true
  });
  ```

### TextLayer
- **Class:** `TextLayer<DataT>`
- **Import:** `import {TextLayer} from '@deck.gl/layers';`
- **Description:** Composite layer wrapping IconLayer for text labels.
- **Sub-layers:** `characters` (IconLayer), `background`.
- **Render props:**
  - `sizeScale` number default `1`.
  - `sizeUnits` string default `'pixels'`.
  - `sizeMinPixels` number default `0`.
  - `sizeMaxPixels` number default `Number.MAX_SAFE_INTEGER`.
  - `billboard` boolean default `true`.
  - `background` boolean default `false`.
  - `backgroundBorderRadius` number | number[4] default `0`.
  - `backgroundPadding` number[4] default `[0,0,0,0]`.
  - `fontFamily` string default `'Monaco, monospace'`.
  - `characterSet` string[] | Set<string> | string default ASCII 32-128; `'auto'` supported.
  - `fontWeight` number | string default `'normal'`.
  - `lineHeight` number default `1`.
  - `fontSettings` object `{fontSize?,buffer?,sdf?,radius?,cutoff?,smoothing?}`.
  - `_getFontRenderer` function (experimental).
  - `wordBreak` `'break-all'|'break-word'` default `'break-word'`.
  - `maxWidth` number default `-1`.
  - `contentCutoffPixels` number[2] default `[0,0]`.
  - `contentAlignHorizontal` `'none'|'start'|'center'|'end'` default `'none'`.
  - `contentAlignVertical` `'none'|'start'|'center'|'end'` default `'none'`.
  - `outlineWidth` number default `0` (SDF only).
  - `outlineColor` Color default `[0,0,0,255]`.
- **Accessors:**
  - `getText` Accessor<string> default `d => d.text`.
  - `getPosition` Accessor<Position> default `d => d.position`.
  - `getSize` Accessor<number> default `32`.
  - `getColor` Accessor<Color> default `[0,0,0,255]`.
  - `getAngle` Accessor<number> default `0`.
  - `getTextAnchor` `'start'|'middle'|'end'` default `'middle'`.
  - `getAlignmentBaseline` `'top'|'center'|'bottom'` default `'center'`.
  - `getPixelOffset` Accessor<number[2]> default `[0,0]`.
  - `getContentBox` Accessor<number[4]> default `[0,0,-1,-1]` — `[x,y,width,height]` world-space offsets.
  - `getBackgroundColor` Accessor<Color> default `[255,255,255,255]` (needs `background: true`).
  - `getBorderColor` Accessor<Color> default `[0,0,0,255]`.
  - `getBorderWidth` Accessor<number> default `0`.
- **Events:** `PickingInfo<DataT>`.
- **Limitations:** Web fonts require preloading or `FontFace` API, otherwise fallback font used. No multi-color emoji. `fontAtlasCacheLimit` defaults to 3; increase for many fonts. For binary `data.attributes.getText` supply `data.startIndices`.
- **Snippet:**
  ```js
  new TextLayer({
    id: 'TextLayer',
    data: 'https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/bart-stations.json',
    getPosition: d => d.coordinates,
    getText: d => d.name,
    getColor: [255, 128, 0],
    getSize: 16,
    getTextAnchor: 'middle',
    getAlignmentBaseline: 'center',
    pickable: true
  });
  ```

---

## Geo Layers (`@deck.gl/geo-layers`)

### A5Layer
- **Class:** `A5Layer<DataT>`
- **Import:** `import {A5Layer} from '@deck.gl/geo-layers';`
- **Inherits:** Base + Composite + PolygonLayer.
- **Description:** Polygons from A5 geospatial indexing.
- **Accessor:** `getPentagon` Accessor<bigint | string> default `d => d.pentagon`.
- **Sub-layer:** `cell` (PolygonLayer).
- **Snippet:**
  ```js
  new A5Layer({
    id: 'A5Layer',
    data: '.../sf.bike.parking.a5.json',
    getPentagon: f => f.pentagon,
    getFillColor: f => [(1-f.count/211)*235, 255-85*f.count/211, 255-170*f.count/211],
    getElevation: f => f.count,
    elevationScale: 10,
    extruded: true, pickable: true
  });
  ```

### GeohashLayer
- **Class:** `GeohashLayer<DataT>`
- **Import:** `import {GeohashLayer} from '@deck.gl/geo-layers';`
- **Inherits:** Base + Composite + PolygonLayer.
- **Description:** Polygons from Geohash string identifiers.
- **Accessor:** `getGeohash` Accessor<string> default `d => d.geohash`.
- **Sub-layer:** `cell` (PolygonLayer).
- **Snippet:**
  ```js
  new GeohashLayer({
    id: 'GeohashLayer',
    data: '.../sf.geohashes.json',
    getGeohash: d => d.geohash,
    getElevation: d => d.value,
    getFillColor: d => [d.value*255, (1-d.value)*128, (1-d.value)*255],
    elevationScale: 1000,
    extruded: true, pickable: true
  });
  ```

### GreatCircleLayer
- **Class:** `GreatCircleLayer<DataT>`
- **Import:** `import {GreatCircleLayer} from '@deck.gl/geo-layers';`
- **Inherits:** ArcLayer.
- **Description:** Flat great-circle arcs. Equivalent to `ArcLayer` with `greatCircle: true, getHeight: 0`.
- **Limitations:** With globe use `parameters: {cullMode: 'none'}`.
- **Snippet:**
  ```js
  new GreatCircleLayer({
    id: 'GreatCircleLayer',
    data: '.../flights.json',
    getSourcePosition: d => d.from.coordinates,
    getTargetPosition: d => d.to.coordinates,
    getSourceColor: [64, 255, 0],
    getTargetColor: [0, 128, 200],
    getWidth: 5,
    pickable: true
  });
  ```

### H3ClusterLayer
- **Class:** `H3ClusterLayer<DataT>`
- **Import:** `import {H3ClusterLayer} from '@deck.gl/geo-layers';`
- **Inherits:** Base + Composite + PolygonLayer.
- **Description:** Union of H3 hexagons as polygons.
- **Accessor:** `getHexagons` Accessor<string[]> default `d => d.hexIds`.
- **Sub-layer:** `cell` (PolygonLayer).
- **Limitations:** Requires `h3-js` before deck.gl when using UMD.
- **Snippet:**
  ```js
  new H3ClusterLayer({
    id: 'H3ClusterLayer',
    data: '.../sf.h3clusters.json',
    getHexagons: d => d.hexIds,
    getFillColor: d => [255, (1-d.mean/500)*255, 0],
    getLineColor: [255, 255, 255],
    lineWidthMinPixels: 2,
    pickable: true
  });
  ```

### H3HexagonLayer
- **Class:** `H3HexagonLayer<DataT>`
- **Import:** `import {H3HexagonLayer} from '@deck.gl/geo-layers';`
- **Inherits:** Base + Composite + PolygonLayer.
- **Description:** Hexagons from H3 indexes.
- **Render props:**
  - `highPrecision` `'auto' | boolean` default `'auto'`.
  - `coverage` number default `1`.
- **Accessor:** `getHexagon` Accessor<string> default `d => d.hexagon`.
- **Sub-layers:** `hexagon-cell-hifi` (SolidPolygonLayer) or `hexagon-cell` (ColumnLayer).
- **Limitations:** All hexagons must share same H3 resolution. Requires `h3-js` before deck.gl with UMD.
- **Snippet:**
  ```js
  new H3HexagonLayer({
    id: 'H3HexagonLayer',
    data: '.../sf.h3cells.json',
    getHexagon: d => d.hex,
    getFillColor: d => [255, (1-d.count/500)*255, 0],
    getElevation: d => d.count,
    elevationScale: 20,
    extruded: true, pickable: true
  });
  ```

### MVTLayer
- **Class:** `MVTLayer<FeaturePropertiesT>`
- **Import:** `import {MVTLayer, MVTLayerPickingInfo} from '@deck.gl/geo-layers';`
- **Inherits:** TileLayer + Base (uses GeoJsonLayer sub-layers by default).
- **Description:** Renders Mapbox/MapLibre vector tiles.
- **Render props:**
  - `data` string | string[] | TileJSON object — URL template or TileJSON URL.
  - `uniqueIdProperty` string — property used as unique feature id across tiles.
  - `highlightedFeatureId` number | string default `null`.
  - `loadOptions` object — MVTLoader options.
  - `binary` boolean default `true`.
- **Callbacks:** `onDataLoad(tileJSON)`.
- **Method:** `getRenderedFeatures(maxFeatures?)` returns GeoJSON features; requires `pickable`.
- **Tile extra:** `tile.dataInWGS84` (Feature[]).
- **Events:** `MVTLayerPickingInfo<FeaturePropertiesT>`, `object` is GeoJSON feature.
- **Limitations:** `getTileData` is not called. Default workers load code from unpkg; configure for custom worker.
- **Snippet:**
  ```js
  new MVTLayer({
    id: 'MVTLayer',
    data: 'https://tiles-a.basemaps.cartocdn.com/vectortiles/carto.streets/v1/{z}/{x}/{y}.mvt',
    minZoom: 0,
    maxZoom: 14,
    getFillColor: f => colorByLayerName(f.properties.layerName),
    getLineWidth: f => widthByClass(f.properties.class),
    getPointRadius: 2,
    pointRadiusUnits: 'pixels',
    pickable: true
  });
  ```

### QuadkeyLayer
- **Class:** `QuadkeyLayer<DataT>`
- **Import:** `import {QuadkeyLayer} from '@deck.gl/geo-layers';`
- **Inherits:** Base + Composite + PolygonLayer.
- **Description:** Polygons from Quadkey indexing.
- **Accessor:** `getQuadkey` Accessor<string> default `d => d.quadkey`.
- **Sub-layer:** `cell` (PolygonLayer).
- **Snippet:**
  ```js
  new QuadkeyLayer({
    id: 'QuadkeyLayer',
    data: '.../sf.quadkeys.json',
    getQuadkey: d => d.quadkey,
    getFillColor: d => [d.value*128, (1-d.value)*255, (1-d.value)*255, 180],
    getElevation: d => d.value,
    elevationScale: 1000,
    extruded: true, pickable: true
  });
  ```

### S2Layer
- **Class:** `S2Layer<DataT>`
- **Import:** `import {S2Layer} from '@deck.gl/geo-layers';`
- **Inherits:** Base + Composite + PolygonLayer.
- **Description:** Polygons from S2 cell indexing.
- **Accessor:** `getS2Token` Accessor<string> default `d => d.token`. Accepts hex token, Hilbert quad key (`/`), or `Long` object.
- **Sub-layer:** `cell` (PolygonLayer).
- **Snippet:**
  ```js
  new S2Layer({
    id: 'S2Layer',
    data: '.../sf.s2cells.json',
    getS2Token: d => d.token,
    getFillColor: d => [d.value*255, (1-d.value)*255, (1-d.value)*128],
    getElevation: d => d.value,
    elevationScale: 1000,
    extruded: true, pickable: true
  });
  ```

### TerrainLayer
- **Class:** `TerrainLayer`
- **Import:** `import {TerrainLayer} from '@deck.gl/geo-layers';`
- **Inherits:** TileLayer when tiled.
- **Description:** Reconstructs terrain mesh from height-map images.
- **Data/Render props:**
  - `elevationData` string | string[] (required) — image URL or tile template `{x}/{y}/{z}`.
  - `texture` string | null default `null` — surface texture tile template.
  - `meshMaxError` number default `4` meters (Martini error tolerance).
  - `elevationDecoder` object default `{rScaler:1,gScaler:0,bScaler:0,offset:0}`.
  - `bounds` number[4] default `null` — required for non-tiled `elevationData`.
  - `color` Color default `[255,255,255]` — forwarded to SimpleMeshLayer `getColor`.
  - `wireframe` boolean default `false`.
  - `material` Material default `true`.
- **Sub-layers:** `tiles` (TileLayer) if tiled, `mesh` (SimpleMeshLayer).
- **Events:** Standard `PickingInfo`; picking off by default.
- **Limitations:** none documented.
- **Snippet:**
  ```js
  new TerrainLayer({
    id: 'TerrainLayer',
    elevationData: '.../terrain.png',
    texture: '.../terrain-mask.png',
    bounds: [-122.5233, 37.6493, -122.3566, 37.8159],
    elevationDecoder: {rScaler:2, gScaler:0, bScaler:0, offset:0}
  });
  ```

### Tile3DLayer
- **Class:** `Tile3DLayer<TileDataT>`
- **Import:** `import {Tile3DLayer} from '@deck.gl/geo-layers';`
- **Inherits:** Base + Composite.
- **Description:** Renders 3D Tiles / I3S tilesets.
- **Render props:**
  - `data` string — tileset entry point URL.
  - `loader` Loader default `Tiles3DLoader`. Options: `CesiumIonLoader`, `I3SLoader`.
  - `loadOptions` object — `{ 'cesium-ion': {...}, '3d-tiles': {...}, 'i3s': {...}, tileset: {...} }`.
  - `pointSize` number default `1` (for `pnts` tiles).
- **Accessors:**
  - `getPointColor` Accessor<Color> default `[0,0,0,255]` (used for `pnts` without embedded colors).
  - `_getMeshColor` Function default `() => [255,255,255]` (debug for I3S `mesh`).
- **Callbacks:** `onTilesetLoad(tileset)`, `onTileLoad(tileHeader)`, `onTileUnload(tileHeader)`, `onTileError(tileHeader, url, message)`.
- **Sub-layers:** `scenegraph` (ScenegraphLayer for `b3dm`/`i3dm`); `pointcloud` (PointCloudLayer for `pnts`); `mesh` (SimpleMeshLayer for ESRI MeshPyramids).
- **Events:** `info.object` is `Tile3DHeader` when `pickable`.
- **Limitations:** none documented.
- **Snippet:**
  ```js
  import {CesiumIonLoader} from '@loaders.gl/3d-tiles';
  new Tile3DLayer({
    id: 'tile-3d-layer',
    data: 'https://assets.cesium.com/43978/tileset.json',
    loader: CesiumIonLoader,
    loadOptions: { 'cesium-ion': {accessToken: 'TOKEN'} },
    pointSize: 2
  });
  ```

### TileLayer
- **Class:** `TileLayer<TileDataT>`
- **Import:** `import {TileLayer, TileLayerPickingInfo} from '@deck.gl/geo-layers';`
- **Inherits:** Base.
- **Description:** Loads and renders tiled data on demand.
- **Data options:**
  - `data` string | string[] default `[]` — URL template, supports `{x} {y} {z}` and `{-y}` for TMS.
  - `getTileData` Function default `tile => load(tile.url)`.
  - `TilesetClass` class default `Tileset2D`.
  - `tileSize` number default `512`.
  - `zoomOffset` number default `0`.
  - `maxZoom` number | null default `null`.
  - `minZoom` number default `0`.
  - `visibleMinZoom` number | null default `null`.
  - `visibleMaxZoom` number | null default `null`.
  - `extent` number[4] default `null`.
  - `maxCacheSize` number default calculated as `5 * viewport tiles`.
  - `maxCacheByteSize` number default `null` (requires `byteLength` on tile data).
  - `refinementStrategy` `'best-available' | 'no-overlap' | 'never' | Function` default `'best-available'`.
  - `maxRequests` number default `6`; `-1` for unthrottled.
  - `debounceTime` number default `0`.
- **Render options:**
  - `renderSubLayers` Function default `props => new GeoJsonLayer(props)`.
  - `zRange` number[2] default `null`.
  - `modelMatrix` Matrix4 default `null`.
- **Callbacks:** `onViewportLoad(tiles)`, `onTileLoad(tile)`, `onTileError(error)`, `onTileUnload(tile)`.
- **Tile object:** `{index:{x,y,z}, id, boundingBox, content, data, parent, children, isSelected, isVisible, isLoaded}`.
- **Events:** `TileLayerPickingInfo`; `tile` field present.
- **Limitations:** none documented.
- **Snippet:**
  ```js
  import {BitmapLayer} from '@deck.gl/layers';
  new TileLayer({
    id: 'TileLayer',
    data: 'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
    minZoom: 0, maxZoom: 19,
    renderSubLayers: props => {
      const {boundingBox} = props.tile;
      return new BitmapLayer(props, {
        data: null,
        image: props.data,
        bounds: [boundingBox[0][0], boundingBox[0][1], boundingBox[1][0], boundingBox[1][1]]
      });
    },
    pickable: true
  });
  ```

### TripsLayer
- **Class:** `TripsLayer<DataT>`
- **Import:** `import {TripsLayer} from '@deck.gl/geo-layers';`
- **Inherits:** Base + PathLayer.
- **Description:** Animated vehicle trips with timestamps.
- **Render props:**
  - `currentTime` number default `0`.
  - `fadeTrail` boolean default `true`.
  - `trailLength` number default `120`.
- **Accessors:**
  - `getPath` Accessor<PathGeometry> default `d => d.path`.
  - `getTimestamps` Accessor<number[]> default `d => d.timestamps` — per-vertex timestamps. Stored as float32; avoid loss of precision (subtract epoch base).
- **Events:** `PickingInfo<DataT>`.
- **Limitations:** With globe use `parameters: {cullMode: 'none'}`.
- **Snippet:**
  ```js
  new TripsLayer({
    id: 'TripsLayer',
    data: '.../sf.trips.json',
    getPath: d => d.waypoints.map(p => p.coordinates),
    getTimestamps: d => d.waypoints.map(p => p.timestamp - 1554772579000),
    getColor: [253, 128, 93],
    currentTime: 500,
    trailLength: 600,
    widthMinPixels: 8
  });
  ```

### WMSLayer
- **Class:** `WMSLayer`
- **Import:** `import {_WMSLayer as WMSLayer, WMSLayerProps} from '@deck.gl/geo-layers';`
- **Inherits:** Base.
- **Description:** (experimental) Viewport-sized image from OGC WMS or custom image services.
- **Data options:**
  - `data` string — base service URL or template with `{east} {north} {west} {south} {width} {height} {layers}`.
  - `serviceType` `'auto'|'wms'|'template'` default `'auto'`.
  - `layers` string[] default `[]`.
  - `srs` `'EPSG:4326'|'EPSG:3857'|'auto'` default `'auto'`.
- **Callbacks:** `onMetadataLoad(metadata)`, `onMetadataLoadError(error)`, `onImageLoadStart(requestId)`, `onImageLoad(requestId)`, `onImageLoadError(requestId, error)`.
- **Method:** `getFeatureInfoText(x,y): Promise<string>`.
- **Events:** Standard; picking relies on `getFeatureInfoText`.
- **Limitations:** Experimental. Supports only one view per instance. Poor with pitch > 0. Not for `OrthographicView`/`OrbitView`.
- **Snippet:**
  ```js
  new WMSLayer({
    data: 'https://ows.terrestris.de/osm/service',
    serviceType: 'wms',
    layers: ['OSM-WMS']
  });
  ```

---

## Aggregation Layers (`@deck.gl/aggregation-layers`)

Common patterns: `getPosition`/`getWeight` accessors; `gpuAggregation` default `true`; CPU fallback occurs when custom aggregators (`getColorValue`/`getElevationValue`/`gridAggregator`/`hexagonAggregator`) are used. Color/elevation scales have `color/elevationScaleType`, `Domain`, `Range`, `*UpperPercentile`, `*LowerPercentile`.

### ContourLayer
- **Class:** `ContourLayer<DataT>`
- **Import:** `import {ContourLayer, ContourLayerPickingInfo} from '@deck.gl/aggregation-layers';`
- **Inherits:** Base.
- **Description:** Isolines / isobands from aggregated scalar field via Marching Squares.
- **Aggregation props:**
  - `cellSize` number default `1000` meters.
  - `gpuAggregation` boolean default `true`.
  - `aggregation` `'SUM'|'MEAN'|'MIN'|'MAX'|'COUNT'` default `'SUM'`.
- **Render props:**
  - `contours` object[] default `[{threshold:1}]` — each `{threshold: number|[number,number], color?: Color, strokeWidth?:number, zIndex?:number}`.
  - `zOffset` number default `0.005`.
- **Accessors:**
  - `getPosition` Accessor<Position> default `d => d.position`.
  - `getWeight` Accessor<number> default `1`.
- **Picking:** `PickingInfo.object.contour` holds the matching contour config. `lines` → PathLayer, `bands` → SolidPolygonLayer.
- **Limitations:** none documented.
- **Snippet:**
  ```js
  new ContourLayer({
    id: 'ContourLayer',
    data: '.../sf-bike-parking.json',
    cellSize: 200,
    getPosition: d => d.COORDINATES,
    getWeight: d => d.SPACES,
    contours: [
      {threshold: 1, color: [255,0,0], strokeWidth: 2, zIndex: 1},
      {threshold: [3,10], color: [55,0,55], zIndex: 0}
    ],
    pickable: true
  });
  ```

### GridLayer
- **Class:** `GridLayer<DataT>`
- **Import:** `import {GridLayer, GridLayerPickingInfo} from '@deck.gl/aggregation-layers';`
- **Inherits:** Base + Composite.
- **Description:** Aggregates points into grid cells as columns.
- **Aggregation props:**
  - `gpuAggregation` boolean default `true`.
  - `cellSize` number default `1000` meters.
  - `colorAggregation` `'SUM'|...` default `'SUM'`; overridden by `getColorValue`.
  - `elevationAggregation` `'SUM'|...` default `'SUM'`; overridden by `getElevationValue`.
  - `gridAggregator` Function default `null` — custom cell ID function, disables GPU.
- **Render props:**
  - `coverage` number default `1`.
  - `extruded` boolean default `true`.
  - `colorScaleType` `'linear'|'quantize'|'quantile'|'ordinal'` default `'quantize'`.
  - `colorDomain` number[2] default `null` (auto).
  - `colorRange` Color[] default 6-class YlOrRd.
  - `elevationScaleType` `'linear'|'quantile'` default `'linear'`.
  - `elevationDomain` number[2] default `null`.
  - `elevationRange` number[2] default `[0,1000]`.
  - `elevationScale` number default `1`.
  - `upperPercentile`/`lowerPercentile` number defaults `100`/`0`.
  - `elevationUpperPercentile`/`elevationLowerPercentile` number defaults `100`/`0`.
  - `material` Material default `true`.
- **Accessors:**
  - `getPosition` Accessor<Position> default `d => d.position`.
  - `getColorWeight` Accessor<number> default `1`.
  - `getColorValue` Function default `null` — `(objects, {indices, data}) => number`, disables GPU.
  - `getElevationWeight` Accessor<number> default `1`.
  - `getElevationValue` Function default `null` — `(objects, {indices, data}) => number`, disables GPU.
- **Callbacks:** `onSetColorDomain([min,max])`, `onSetElevationDomain([min,max])`.
- **Picking:** `GridLayerPickingInfo<DataT>`, `object` contains `{col,row,colorValue,elevationValue,count,pointIndices?,points?}`; last two only CPU.
- **Sub-layers:** `cells` (custom ColumnLayer).
- **Limitations:** GPU aggregation loses per-cell point lists. `quantile`/`ordinal`/percentile force CPU readback once.
- **Snippet:**
  ```js
  new GridLayer({
    id: 'GridLayer',
    data: '.../sf-bike-parking.json',
    getPosition: d => d.COORDINATES,
    getColorWeight: d => d.SPACES,
    getElevationWeight: d => d.SPACES,
    cellSize: 200,
    elevationScale: 4,
    extruded: true,
    pickable: true
  });
  ```

### HeatmapLayer
- **Class:** `HeatmapLayer<DataT>`
- **Import:** `import {HeatmapLayer} from '@deck.gl/aggregation-layers';`
- **Inherits:** Base + Composite.
- **Description:** Gaussian kernel-density heatmap.
- **Render props:**
  - `radiusPixels` number default `30`.
  - `colorRange` Color[] default 6-class YlOrRd.
  - `intensity` number default `1`.
  - `threshold` number default `0.05` (ignored if `colorDomain` set).
  - `colorDomain` number[2] default `null` — stable value mapping.
  - `aggregation` `'SUM'|'MEAN'` default `'SUM'`.
  - `weightsTextureSize` number default `2048`.
  - `debounceTimeout` number default `500` ms.
- **Accessors:**
  - `getPosition` Accessor<Position> default `d => d.position`.
  - `getWeight` Accessor<number> default `1`.
- **Picking:** not documented as a picked-object layer (renders as image).
- **Limitations:** iOS Safari falls back to 8-bit precision; weights must be integers and per-pixel sum <=255. May block on large viewport/radius; tune `debounceTimeout`/`weightsTextureSize`.
- **Snippet:**
  ```js
  new HeatmapLayer({
    id: 'HeatmapLayer',
    data: '.../sf-bike-parking.json',
    getPosition: d => d.COORDINATES,
    getWeight: d => d.SPACES,
    radiusPixels: 25,
    aggregation: 'SUM'
  });
  ```

### HexagonLayer
- **Class:** `HexagonLayer<DataT>`
- **Import:** `import {HexagonLayer, HexagonLayerPickingInfo} from '@deck.gl/aggregation-layers';`
- **Inherits:** Base + Composite.
- **Description:** Hexagonal binning into columns.
- **Aggregation props:**
  - `gpuAggregation` boolean default `true`.
  - `radius` number default `1000` meters.
  - `colorAggregation`/`elevationAggregation` default `'SUM'`.
  - `hexagonAggregator` Function default `null` — custom hex binning, disables GPU.
- **Render props:** same idea as GridLayer (`coverage`, `extruded` default `false`, color/elevation scale props, percentiles, `material`, etc.).
- **Accessors:** `getPosition`, `getColorWeight`, `getColorValue`, `getElevationWeight`, `getElevationValue` (same semantics as GridLayer).
- **Callbacks:** `onSetColorDomain`, `onSetElevationDomain`.
- **Picking:** `HexagonLayerPickingInfo<DataT>`, `object` has `{col,row,colorValue,elevationValue,count,pointIndices?,points?}`.
- **Sub-layers:** `cells` (ColumnLayer).
- **Limitations:** same GPU/CPU caveats as GridLayer. Default aggregator uses d3-hexbin.
- **Snippet:**
  ```js
  new HexagonLayer({
    id: 'HexagonLayer',
    data: '.../sf-bike-parking.json',
    getPosition: d => d.COORDINATES,
    getColorWeight: d => d.SPACES,
    getElevationWeight: d => d.SPACES,
    radius: 200,
    elevationScale: 4,
    extruded: true,
    pickable: true
  });
  ```

### ScreenGridLayer
- **Class:** `ScreenGridLayer<DataT>`
- **Import:** `import {ScreenGridLayer, ScreenGridLayerPickingInfo} from '@deck.gl/aggregation-layers';`
- **Inherits:** Base.
- **Description:** Screen-space grid histogram overlay.
- **Aggregation props:**
  - `gpuAggregation` boolean default `true`.
  - `cellSizePixels` number default `100`.
  - `aggregation` `'SUM'|...` default `'SUM'`.
- **Render props:**
  - `cellMarginPixels` number default `2`, clamped 0-5.
  - `colorScaleType` `'linear'|'quantize'` default `'linear'`.
  - `colorDomain` number[2] default `null`.
  - `colorRange` Color[6] default 6-class YlOrRd.
- **Accessors:**
  - `getPosition` Accessor<Position> default `d => d.position`.
  - `getWeight` Accessor<number> default `1`.
- **Picking:** `ScreenGridLayerPickingInfo<DataT>`, `object` has `{col,row,value,count,pointIndices?,points?}`.
- **Limitations:** Re-aggregates on every pan/zoom; best for small datasets.
- **Snippet:**
  ```js
  new ScreenGridLayer({
    id: 'ScreenGridLayer',
    data: '.../sf-bike-parking.json',
    getPosition: d => d.COORDINATES,
    getWeight: d => d.SPACES,
    cellSizePixels: 50,
    colorRange: [[0,25,0,25], ..., [0,255,0,255]],
    opacity: 0.8
  });
  ```

---

## Mesh Layers (`@deck.gl/mesh-layers`)

### ScenegraphLayer
- **Class:** `ScenegraphLayer<DataT>`
- **Import:** `import {ScenegraphLayer} from '@deck.gl/mesh-layers';`
- **Inherits:** Base.
- **Description:** Instanced complete glTF scenegraphs.
- **Mesh props:**
  - `scenegraph` string | object | Promise — URL, ScenegraphNode, or Promise.
  - `loadOptions` object — GLTFLoader options.
  - `sizeScale` number default `1`.
  - `_animations` object default undefined — `{indexOrNameOrStar: {playing,speed,startTime}}`.
  - `getScene` Function default picks first scene.
  - `getAnimator` Function default `scenegraph => scenegraph.animator`; return `null` to disable.
  - `_lighting` `'flat'|'pbr'` default `'flat'`.
  - `_imageBasedLightingEnvironment` Function | GLTFEnvironment default `null`.
  - `sizeMinPixels` number default `0`.
  - `sizeMaxPixels` number default `Number.MAX_SAFE_INTEGER`.
- **Accessors:**
  - `getPosition` Accessor<Position> default `d => d.position`.
  - `getColor` Accessor<Color> default `[0,0,0,255]` (used if no texture).
  - `getOrientation` Accessor<number[3]> default `[0,0,0]` — `[pitch,yaw,roll]` degrees.
  - `getScale` Accessor<number[3]> default `[1,1,1]`.
  - `getTranslation` Accessor<number[3]> default `[0,0,0]` meters offset.
  - `getTransformMatrix` Accessor<number[16]> default `null` — overrides orientation/scale/translation.
- **Events:** `PickingInfo<DataT>`.
- **Limitations:** none documented.
- **Snippet:**
  ```js
  new ScenegraphLayer({
    id: 'ScenegraphLayer',
    data: '.../bart-stations.json',
    scenegraph: '.../BoxAnimated.glb',
    getPosition: d => d.coordinates,
    getOrientation: d => [0, Math.random()*180, 90],
    sizeScale: 500,
    _animations: {'*': {speed: 5}},
    _lighting: 'pbr',
    pickable: true
  });
  ```

### SimpleMeshLayer
- **Class:** `SimpleMeshLayer<DataT>`
- **Import:** `import {SimpleMeshLayer} from '@deck.gl/mesh-layers';`
- **Inherits:** Base.
- **Description:** Instanced arbitrary 3D meshes.
- **Mesh props:**
  - `mesh` string | object (required) — URL, luma.gl Geometry, or `{positions, normals, texCoords}`.
  - `texture` string | Texture | image... default `null`.
  - `textureParameters` object default linear/clamp-to-edge samplers.
  - `sizeScale` number default `1`.
  - `wireframe` boolean default `false`.
  - `material` Material default `true`.
- **Accessors:**
  - `getPosition` Accessor<Position> default `d => d.position`.
  - `getColor` Accessor<Color> default `[0,0,0,255]` (mixes with mesh vertex colors; use `[255,255,255]` to keep original).
  - `getOrientation` Accessor<number[3]> default `[0,0,0]`.
  - `getScale` Accessor<number[3]> default `[1,1,1]`.
  - `getTranslation` Accessor<number[3]> default `[0,0,0]`.
  - `getTransformMatrix` Accessor<number[16]> default `null`.
- **Events:** `PickingInfo<DataT>`.
- **Limitations:** none documented.
- **Snippet:**
  ```js
  import {OBJLoader} from '@loaders.gl/obj';
  new SimpleMeshLayer({
    id: 'SimpleMeshLayer',
    data: '.../bart-stations.json',
    mesh: '.../humanoid_quad.obj',
    loaders: [OBJLoader],
    getPosition: d => d.coordinates,
    getColor: d => [Math.sqrt(d.exits), 140, 0],
    getOrientation: d => [0, Math.random()*180, 0],
    sizeScale: 30,
    pickable: true
  });
  ```

---

## Notes for Code Generation

1. Default import module:
   - Core layers: `@deck.gl/layers`
   - Geo layers: `@deck.gl/geo-layers`
   - Aggregation layers: `@deck.gl/aggregation-layers`
   - Mesh layers: `@deck.gl/mesh-layers`
2. Composite layers that wrap others (GeoJsonLayer, PolygonLayer, TextLayer, aggregation layers, most geo layers) allow `parameters`, `_subLayerProps`, `transitions` to pass to sub-layers.
3. In geospatial mode positions are `[longitude, latitude]` (or `[lng, lat, z]`); meters when using `COORDINATE_SYSTEM.METER_OFFSETS`.
4. For picking, remember `pickable: true` and use the typed `PickingInfo` / layer-specific `PickingInfo` exports where available.
5. Aggregations: prefer `getColorWeight`/`getElevationWeight` + `*Aggregation` for GPU path; use `getColorValue`/`getElevationValue`/`gridAggregator`/`hexagonAggregator` only when custom logic is needed.
