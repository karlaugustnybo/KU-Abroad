import type { ReactNode } from 'react'
import {
  Outlet,
  createRootRoute,
  HeadContent,
  Scripts,
} from '@tanstack/react-router'
import appCss from '~/styles/globals.css?url'
import { seo } from '~/utils/seo'
import { TooltipProvider } from '~/components/ui/tooltip'

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { title: 'KU Abroad · Partner Institutions' },
      { charSet: 'utf-8' },
      {
        name: 'viewport',
        content: 'width=device-width, initial-scale=1',
      },
      ...seo({
        title: 'KU Abroad · Partner Institutions',
        description:
          "Explore KU's partner institutions, mobility agreements and global cooperation network.",
      }),
    ],
    links: [
      { rel: 'stylesheet', href: appCss },
      { rel: 'preconnect', href: 'https://basemaps.cartocdn.com' },
      { rel: 'preconnect', href: 'https://tiles.basemaps.cartocdn.com' },
      { rel: 'preconnect', href: 'https://tiles-a.basemaps.cartocdn.com' },
    ],
  }),
  component: RootComponent,
})

function RootComponent() {
  return (
    <RootDocument>
      <Outlet />
    </RootDocument>
  )
}

function RootDocument({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <head>
        <HeadContent />
      </head>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <TooltipProvider>{children}</TooltipProvider>
        <Scripts />
      </body>
    </html>
  )
}
