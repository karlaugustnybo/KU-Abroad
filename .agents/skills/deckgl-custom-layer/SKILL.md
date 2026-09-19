---
name: deckgl-custom-layer
description: |
  Write custom deck.gl layers, layer subclasses, composite layers, primitive layers, layer extensions, or custom shaders. Use when the user asks for a custom DeckGL layer, custom shaders/GLSL, extending an existing layer, attribute management, or implementing picking in a custom layer. Also use for custom draw calls, color/data loaders, or extending deck.gl with new behavior.
compatibility: |
  Requires code-generation tools. No runtime dependency. Knowledge of WebGL/WebGPU is assumed for shader work.
---

# deck.gl custom layers skill

You guide users in creating valid custom deck.gl layers. Your source of truth is `references/custom-layers-basemaps.md` Section 1.

## Types of customization

1. **Subclassed layers** — easiest. Extend a built-in layer and override accessors/props.
2. **Composite layers** — compose multiple built-in layers in `renderLayers()`.
3. **Primitive layers** — full custom WebGL layer with custom geometry, attributes, shaders, and picking.
4. **Layer extensions** — modify an existing layer's shaders/behavior via `LayerExtension`.

## Key lifecycle methods

- `initializeState(context)` — register attributes and models.
- `updateState(params)` — react to prop/data changes.
- `draw(opts)` — issue draw calls.
- `getPickingInfo(pickParams)` — customize picking info.
- `renderLayers()` — composite layers return an array of layers.

## Shader conventions (WebGL primitive layers)

- Extend `vs:` / `fs:` from `@deck.gl/core` shader modules.
- Use `project_vertex` and `project_position_to_clipspace` helpers from `project` module.
- Vertex attributes declared with `attribute ... location=0`, etc.
- Use `picking` module for highlight/selection.
- Keep shaders GLSL ES 3.0 / WebGL2 compatible.

## Prop types

Use `propTypes` object when defining custom layers:

```javascript
const defaultProps = {
  radius: {type: 'number', min: 0, value: 1},
  color: {type: 'color', value: [255, 0, 0]},
};
```

## Attribute management

- Use this.state.attributeManager with `add`/`addInstanced`.
- Instanced attributes for repeated geometry (e.g. scatter points).
- Update attributes in `updateState` when data or accessors change.

## Composite layer pattern

```javascript
import {CompositeLayer} from '@deck.gl/core';
import {ScatterplotLayer, TextLayer} from '@deck.gl/layers';

class LabeledPointsLayer extends CompositeLayer {
  renderLayers() {
    return [
      new ScatterplotLayer({
        id: `${this.props.id}-points`,
        data: this.props.data,
        getPosition: this.props.getPosition,
        getRadius: this.props.getRadius,
        getFillColor: this.props.getFillColor
      }),
      new TextLayer({
        id: `${this.props.id}-labels`,
        data: this.props.data,
        getPosition: this.props.getPosition,
        getText: this.props.getText
      })
    ];
  }
}
LabeledPointsLayer.layerName = 'LabeledPointsLayer';
```

## Output

- Recommend the simplest customization path.
- Provide full custom layer class(es), `defaultProps`, shaders if primitive, and a usage example.
- Note any registration (`DeckGL` or JSON) needed.
