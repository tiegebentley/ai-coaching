'use client'

import { Metadata } from 'next'
import Link from 'next/link'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { useDashboardStats } from '@/hooks/useSupabase'
import { Loading } from '@/components/ui/Loading'
import { Alert } from '@/components/ui/Alert'
import { Card } from '@/components/ui/Card'

// Note: Move metadata to layout.tsx for client components
export default function DashboardPage() {
  const { stats, loading, error, refetch } = useDashboardStats()

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loading size="lg" />
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <Alert
          variant="error"
          title="Failed to load dashboard"
          description={error}
          action={{
            label: "Retry",
            onClick: refetch
          }}
        />
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="md:flex md:items-center md:justify-between">
          <div className="min-w-0 flex-1">
            <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">
              Dashboard
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Welcome back! Here's an overview of your AI coaching system.
            </p>
          </div>
          <div className="mt-4 flex md:ml-4 md:mt-0">
            <button
              type="button"
              className="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
              onClick={refetch}
            >
              <svg className="-ml-0.5 mr-1.5 h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {/* Email Processing Card */}
          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-coach-500 text-white">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="truncate text-sm font-medium text-gray-500">Total Emails</dt>
                  <dd className="text-lg font-medium text-gray-900">{stats.totalEmails}</dd>
                </dl>
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-gray-500">{stats.pendingEmails} pending</span>
                <span className="ml-auto">
                  <Link href="/dashboard/emails" className="font-medium text-coach-600 hover:text-coach-500">
                    View all →
                  </Link>
                </span>
              </div>
            </div>
          </Card>

          {/* Schedule Management Card */}
          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-success-500 text-white">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="truncate text-sm font-medium text-gray-500">Upcoming Sessions</dt>
                  <dd className="text-lg font-medium text-gray-900">{stats.upcomingSessions}</dd>
                </dl>
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-gray-500">This week</span>
                <span className="ml-auto">
                  <Link href="/dashboard/schedule" className="font-medium text-coach-600 hover:text-coach-500">
                    View schedule →
                  </Link>
                </span>
              </div>
            </div>
          </Card>

          {/* Family Communication Card */}
          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-indigo-500 text-white">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="truncate text-sm font-medium text-gray-500">Active Families</dt>
                  <dd className="text-lg font-medium text-gray-900">{stats.activeFamilies}</dd>
                </dl>
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-gray-500">Registered</span>
                <span className="ml-auto">
                  <Link href="/dashboard/families" className="font-medium text-coach-600 hover:text-coach-500">
                    Manage families →
                  </Link>
                </span>
              </div>
            </div>
          </Card>

          {/* AI Processing Rate Card */}
          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-amber-500 text-white">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="truncate text-sm font-medium text-gray-500">Processing Rate</dt>
                  <dd className="text-lg font-medium text-gray-900">{stats.processingRate}%</dd>
                </dl>
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <div className="flex-1">
                  <div className="h-2 rounded-full bg-gray-200">
                    <div 
                      className="h-2 rounded-full bg-amber-500 transition-all duration-300"
                      style={{ width: `${stats.processingRate}%` }}
                    />
                  </div>
                </div>
                <span className="ml-2 text-gray-500">24h</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <div className="px-6 py-5">
              <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
              <p className="mt-1 text-sm text-gray-500">Latest system events and processing updates</p>
            </div>
            <div className="border-t border-gray-200">
              <div className="divide-y divide-gray-200">
                <div className="px-6 py-4">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 rounded-full bg-coach-100 flex items-center justify-center">
                        <svg className="h-4 w-4 text-coach-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                      </div>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-gray-900">
                        <span className="font-medium">Email Agent</span> processed new parent inquiry
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">2 minutes ago</p>
                    </div>
                  </div>
                </div>
                
                <div className="px-6 py-4">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 rounded-full bg-success-100 flex items-center justify-center">
                        <svg className="h-4 w-4 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-gray-900">
                        <span className="font-medium">Schedule Agent</span> confirmed weekend practice
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">15 minutes ago</p>
                    </div>
                  </div>
                </div>

                <div className="px-6 py-4">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 rounded-full bg-amber-100 flex items-center justify-center">
                        <svg className="h-4 w-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.996-.833-2.764 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                        </svg>
                      </div>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-gray-900">
                        <span className="font-medium">Knowledge Agent</span> detected potential conflict
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">1 hour ago</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Card>

          {/* System Status */}
          <Card>
            <div className="px-6 py-5">
              <h3 className="text-lg font-medium text-gray-900">System Status</h3>
              <p className="mt-1 text-sm text-gray-500">AI agents and service health</p>
            </div>
            <div className="border-t border-gray-200">
              <div className="divide-y divide-gray-200">
                <div className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className="h-2 w-2 bg-success-400 rounded-full mr-3"></div>
                      <span className="text-sm font-medium text-gray-900">Email Processing</span>
                    </div>
                    <span className="text-sm text-gray-500">Operational</span>
                  </div>
                </div>
                
                <div className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className="h-2 w-2 bg-success-400 rounded-full mr-3"></div>
                      <span className="text-sm font-medium text-gray-900">Schedule Management</span>
                    </div>
                    <span className="text-sm text-gray-500">Operational</span>
                  </div>
                </div>

                <div className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className="h-2 w-2 bg-success-400 rounded-full mr-3"></div>
                      <span className="text-sm font-medium text-gray-900">Knowledge Base</span>
                    </div>
                    <span className="text-sm text-gray-500">Operational</span>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}