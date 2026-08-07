"use client"

import { Toast as ToastPrimitive } from "@base-ui/react/toast"
import { CheckCircle2Icon, XCircleIcon, XIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

function ToastProvider({ ...props }: ToastPrimitive.Provider.Props) {
  return <ToastPrimitive.Provider data-slot="toast-provider" {...props} />
}

function ToastPortal({ ...props }: ToastPrimitive.Portal.Props) {
  return <ToastPrimitive.Portal data-slot="toast-portal" {...props} />
}

function ToastViewport({ className, ...props }: ToastPrimitive.Viewport.Props) {
  return (
    <ToastPrimitive.Viewport
      data-slot="toast-viewport"
      className={cn(
        "fixed top-20 left-1/2 -translate-x-1/2 z-50 flex w-full max-w-[calc(100%-2rem)] flex-col gap-2 sm:max-w-sm",
        className
      )}
      {...props}
    />
  )
}

function ToastRoot({ className, ...props }: ToastPrimitive.Root.Props) {
  return (
    <ToastPrimitive.Root
      data-slot="toast"
      className={cn(
        "relative flex items-start gap-2 rounded-xl bg-popover p-3 pr-8 text-sm text-popover-foreground shadow-lg ring-1 ring-black/5 duration-200 data-starting-style:translate-y-2 data-starting-style:opacity-0 data-ending-style:opacity-0 data-[type=success]:bg-emerald-600 data-[type=success]:text-white data-[type=error]:bg-red-600 data-[type=error]:text-white",
        className
      )}
      {...props}
    />
  )
}

function ToastIcon({ type }: { type: string | undefined }) {
  if (type === "success" || type === "error") {
    const Icon = type === "success" ? CheckCircle2Icon : XCircleIcon
    return <Icon className="mt-0.5 size-4 shrink-0 text-white" />
  }
  return null
}

function ToastTitle({ className, ...props }: ToastPrimitive.Title.Props) {
  return (
    <ToastPrimitive.Title
      data-slot="toast-title"
      className={cn("font-heading text-sm leading-none font-medium", className)}
      {...props}
    />
  )
}

function ToastDescription({ className, ...props }: ToastPrimitive.Description.Props) {
  return (
    <ToastPrimitive.Description
      data-slot="toast-description"
      className={cn("text-sm", className)}
      {...props}
    />
  )
}

function ToastClose({ className, ...props }: ToastPrimitive.Close.Props) {
  return (
    <ToastPrimitive.Close
      data-slot="toast-close"
      render={
        <Button
          variant="ghost"
          size="icon-sm"
          className={cn("absolute top-1.5 right-1.5 text-current hover:bg-black/10 hover:text-current", className)}
        />
      }
      {...props}
    >
      <XIcon />
      <span className="sr-only">Close</span>
    </ToastPrimitive.Close>
  )
}

function Toaster() {
  const { toasts } = ToastPrimitive.useToastManager()

  return (
    <ToastPortal>
      <ToastViewport>
        {toasts.map((toast) => (
          <ToastRoot key={toast.id} toast={toast}>
            <ToastIcon type={toast.type} />
            <div className="flex flex-1 flex-col gap-0.5">
              <ToastTitle />
              <ToastDescription />
            </div>
            <ToastClose />
          </ToastRoot>
        ))}
      </ToastViewport>
    </ToastPortal>
  )
}

export {
  ToastProvider,
  ToastPortal,
  ToastViewport,
  ToastRoot,
  ToastTitle,
  ToastDescription,
  ToastClose,
  Toaster,
}
