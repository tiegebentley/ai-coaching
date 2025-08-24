import { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'AI Coaching Management System',
  description: 'Welcome to the AI-powered coaching management system',
}

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b bg-white">
        <div className="container mx-auto px-4 py-4">
          <nav className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-bold text-coach-600">
                AI Coaching System
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                href="/login"
                className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900"
              >
                Sign In
              </Link>
              <Link
                href="/dashboard"
                className="rounded-md bg-coach-600 px-4 py-2 text-sm font-medium text-white hover:bg-coach-700"
              >
                Dashboard
              </Link>
            </div>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <section className="py-24">
          <div className="container mx-auto px-4 text-center">
            <h1 className="mb-6 text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
              AI-Powered Coaching Management
            </h1>
            <p className="mx-auto mb-8 max-w-2xl text-lg text-gray-600">
              Streamline your coaching operations with intelligent email processing,
              automated scheduling, and smart family communication tools.
            </p>
            <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
              <Link
                href="/dashboard"
                className="rounded-md bg-coach-600 px-8 py-3 text-lg font-semibold text-white shadow-sm hover:bg-coach-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-coach-600"
              >
                Get Started
              </Link>
              <Link
                href="/about"
                className="rounded-md bg-white px-8 py-3 text-lg font-semibold text-coach-600 shadow-sm ring-1 ring-inset ring-coach-300 hover:bg-gray-50"
              >
                Learn More
              </Link>
            </div>
          </div>
        </section>

        <section className="bg-gray-50 py-16">
          <div className="container mx-auto px-4">
            <div className="grid gap-8 md:grid-cols-3">
              <div className="text-center">
                <div className="mb-4 flex justify-center">
                  <div className="rounded-full bg-coach-100 p-3">
                    <svg className="h-6 w-6 text-coach-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  </div>
                </div>
                <h3 className="mb-2 text-lg font-semibold">Smart Email Processing</h3>
                <p className="text-gray-600">
                  Automatically process and categorize coaching emails with AI-powered analysis.
                </p>
              </div>
              
              <div className="text-center">
                <div className="mb-4 flex justify-center">
                  <div className="rounded-full bg-coach-100 p-3">
                    <svg className="h-6 w-6 text-coach-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                </div>
                <h3 className="mb-2 text-lg font-semibold">Automated Scheduling</h3>
                <p className="text-gray-600">
                  Intelligent schedule management with conflict detection and optimization.
                </p>
              </div>
              
              <div className="text-center">
                <div className="mb-4 flex justify-center">
                  <div className="rounded-full bg-coach-100 p-3">
                    <svg className="h-6 w-6 text-coach-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z" />
                    </svg>
                  </div>
                </div>
                <h3 className="mb-2 text-lg font-semibold">Family Communication</h3>
                <p className="text-gray-600">
                  Streamlined communication tools for families and coaching staff.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t bg-white">
        <div className="container mx-auto px-4 py-8">
          <div className="text-center text-sm text-gray-600">
            © 2024 AI Coaching Management System. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  )
}