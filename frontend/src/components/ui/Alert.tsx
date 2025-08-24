import React from 'react'
import { cn } from '@/lib/utils'

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'success' | 'warning' | 'error'
  title?: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
  children?: React.ReactNode
}

interface AlertTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode
}

interface AlertDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode
}

const alertVariants = {
  default: 'bg-gray-50 text-gray-900 border-gray-200',
  success: 'bg-success-50 text-success-900 border-success-200',
  warning: 'bg-warning-50 text-warning-900 border-warning-200',
  error: 'bg-red-50 text-red-900 border-red-200'
}

const iconVariants = {
  default: 'text-gray-500',
  success: 'text-success-500',
  warning: 'text-warning-500',
  error: 'text-red-500'
}

function InfoIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
    </svg>
  )
}

function CheckCircleIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  )
}

function ExclamationTriangleIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
    </svg>
  )
}

function XCircleIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="m9.75 9.75 4.5 4.5m0-4.5-4.5 4.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  )
}

const icons = {
  default: InfoIcon,
  success: CheckCircleIcon,
  warning: ExclamationTriangleIcon,
  error: XCircleIcon
}

export function Alert({ className, variant = 'default', title, description, action, children, ...props }: AlertProps) {
  const Icon = icons[variant]

  return (
    <div
      className={cn(
        'relative w-full rounded-lg border p-4',
        alertVariants[variant],
        className
      )}
      {...props}
    >
      <div className="flex">
        <div className="flex-shrink-0">
          <Icon className={cn('h-5 w-5', iconVariants[variant])} aria-hidden="true" />
        </div>
        <div className="ml-3 flex-1">
          {title && (
            <AlertTitle>{title}</AlertTitle>
          )}
          {description && (
            <AlertDescription>{description}</AlertDescription>
          )}
          {children}
          {action && (
            <div className="mt-4">
              <button
                type="button"
                onClick={action.onClick}
                className={cn(
                  'inline-flex items-center rounded-md px-2.5 py-1.5 text-sm font-semibold shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2',
                  variant === 'error' && 'bg-red-600 text-white hover:bg-red-500 focus-visible:outline-red-600',
                  variant === 'warning' && 'bg-warning-600 text-white hover:bg-warning-500 focus-visible:outline-warning-600',
                  variant === 'success' && 'bg-success-600 text-white hover:bg-success-500 focus-visible:outline-success-600',
                  variant === 'default' && 'bg-gray-600 text-white hover:bg-gray-500 focus-visible:outline-gray-600'
                )}
              >
                {action.label}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function AlertTitle({ className, children, ...props }: AlertTitleProps) {
  return (
    <h3
      className={cn('text-sm font-medium', className)}
      {...props}
    >
      {children}
    </h3>
  )
}

export function AlertDescription({ className, children, ...props }: AlertDescriptionProps) {
  return (
    <div
      className={cn('mt-2 text-sm opacity-90', className)}
      {...props}
    >
      {children}
    </div>
  )
}