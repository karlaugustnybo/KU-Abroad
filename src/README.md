# KU Abroad

A TanStack Start app for exploring KU's partner institutions, mobility agreements, and global cooperation network.

## Getting Started

From this directory, install dependencies and run the development server with Bun:

```bash
bun install
bun run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the result.

### Fast Retina basemap

Copy `.env.example` to `.env.local` and set `VITE_BASEMAP_URL` to a keyed CARTO raster URL. The app converts the `{ratio}` placeholder to `@2x`, matching the basemap setup in DIKUs-Ark. Without this variable, it falls back to CARTO's public vector style.

## Building

```bash
bun run build
```

After building, you can start the production server with:

```bash
bun run start
```

## Data pipeline

Regenerate the partner dataset:

```bash
bun run build:data
```

## Learn More

- [TanStack Start](https://tanstack.com/start/latest)
- [TanStack Router](https://tanstack.com/router/latest)
- [Vite](https://vite.dev/)
