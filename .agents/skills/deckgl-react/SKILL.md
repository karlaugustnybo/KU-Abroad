---
name: deckgl-react
description: |
  Generate React code using @deck.gl/react, including DeckGL component usage, widgets, context menu, hooks like useWidget, and TypeScript integration. Use for any React app that embeds deck.gl layers, controls, or widgets. Also trigger for Next.js, Vite React, or create-react-app deck.gl setup.
compatibility: |
  Requires code-generation tools. No runtime dependency.
---

# deck.gl React skill

You produce idiomatic React code for deck.gl using `@deck.gl/react` and widgets.

## Modern v9 imports

```jsx
import {DeckGL, ZoomWidget, CompassWidget} from '@deck.gl/react';
import {ScatterplotLayer} from '@deck.gl/layers';
import {MapView} from '@deck.gl/core';
```

> In older projects you may see `import DeckGL from '@deck.gl/react'`. That default import still works in v9 but is deprecated; always generate the named import `import {DeckGL}` for new code.

## Typical component

```jsx
function App() {
  const layers = [
    new ScatterplotLayer({
      id: 'points',
      data,
      getPosition: d => d.coordinates,
      getFillColor: [255, 140, 0],
      getRadius: 100,
      pickable: true,
      onHover: info => console.log(info.object)
    })
  ];

  return (
    <DeckGL
      initialViewState={{
        longitude: -122.4,
        latitude: 37.7,
        zoom: 10
      }}
      controller
      layers={layers}
    >
      <MapView id="map" controller />
    </DeckGL>
  );
}
```

## Widgets

- In React, import deck.gl widgets from `@deck.gl/react`: `ZoomWidget`, `CompassWidget`, `FullscreenWidget`, `ScreenshotWidget`, `ScaleWidget`, `PopupWidget`, `LoadingWidget`, `InfoWidget`, etc.
- Pass them as children or via the `widgets` prop:
  ```jsx
  <DeckGL widgets={[new ZoomWidget(), new CompassWidget()]} />
  ```
- Children inside `DeckGL` can use the `useWidget()` hook.

## TypeScript

```tsx
import {DeckGL} from '@deck.gl/react';
import type {DeckGLRef} from '@deck.gl/react';
const deckRef = useRef<DeckGLRef>(null);
```

## Next.js / SSR

- deck.gl requires a browser Canvas/WebGL context; use dynamic import with `ssr: false`.

## Handling interactions

- Use React state for `selected`, `hoverInfo`, and tooltip rendering.
- Remember layer constructors are stateless; create new layer instances when props change.

## Output

- Provide a full React component (function or class) with imports.
- Show where layers are declared and how state drives re-renders.
- Include TypeScript types when relevant.
