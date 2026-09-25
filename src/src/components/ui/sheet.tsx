import * as React from 'react'
import { Dialog as SheetPrimitive } from 'radix-ui'
import { X } from 'lucide-react'
import { cn } from '~/lib/utils'

export const Sheet = SheetPrimitive.Root
export const SheetTrigger = SheetPrimitive.Trigger
export const SheetClose = SheetPrimitive.Close

export function SheetContent({ className, children, side = 'right', instant = false, ...props }: React.ComponentProps<typeof SheetPrimitive.Content> & { side?: 'right' | 'bottom'; instant?: boolean }) {
  return <SheetPrimitive.Portal>
    <SheetPrimitive.Overlay className={cn('fixed inset-0 z-50 bg-slate-950/25', instant ? 'animate-none' : 'backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out')} />
    <SheetPrimitive.Content className={cn(
      'fixed z-50 flex flex-col bg-background shadow-2xl outline-none',
      instant ? 'animate-none' : 'data-[state=open]:animate-in data-[state=closed]:animate-out',
      side === 'right' ? 'inset-y-0 right-0 w-[min(92vw,30rem)] overflow-hidden border-l' : 'inset-x-0 bottom-0 h-auto max-h-[92vh] flex-col overflow-hidden rounded-t-xl border-t', className,
    )} {...props}>
      {children}
      <SheetPrimitive.Close className="absolute right-4 top-4 rounded-md p-1 text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <X className="size-5" /><span className="sr-only">Close</span>
      </SheetPrimitive.Close>
    </SheetPrimitive.Content>
  </SheetPrimitive.Portal>
}

export function SheetHeader(props: React.ComponentProps<'div'>) { return <div {...props} className={cn('border-b px-5 py-5 pr-12', props.className)} /> }
export function SheetTitle(props: React.ComponentProps<typeof SheetPrimitive.Title>) { return <SheetPrimitive.Title {...props} className={cn('text-lg font-semibold tracking-tight', props.className)} /> }
export function SheetDescription(props: React.ComponentProps<typeof SheetPrimitive.Description>) { return <SheetPrimitive.Description {...props} className={cn('mt-1 text-sm text-muted-foreground', props.className)} /> }
