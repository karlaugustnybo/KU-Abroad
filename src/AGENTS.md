# Agent Notes

This project is a TanStack Start app built on top of TanStack Router and Vite.

- Routes live in `src/routes/` and use file-based routing conventions from TanStack Router.
- The root layout is `src/routes/__root.tsx` and the home page is `src/routes/index.tsx`.
- Server-only work lives inside `createServerFn` handlers or server routes.
- Shared components live in `src/components/`; styling uses Tailwind CSS v4 with shadcn/radix components.
- Path aliases are configured for `~/*` pointing to `./src/*`.
