import React from 'react'
import { FunnelIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'

interface QueueFiltersProps {
  filters: {
    priority: string
    category: string
    status: string
  }
  onFiltersChange: (filters: any) => void
  emailCount: number
}

const priorityOptions = [
  { value: 'all', label: 'All Priorities' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
]

const categoryOptions = [
  { value: 'all', label: 'All Categories' },
  { value: 'schedule_request', label: 'Schedule Request' },
  { value: 'payment_inquiry', label: 'Payment Inquiry' },
  { value: 'absence_notice', label: 'Absence Notice' },
  { value: 'general_question', label: 'General Question' },
  { value: 'complaint', label: 'Complaint' },
  { value: 'feedback', label: 'Feedback' },
  { value: 'emergency', label: 'Emergency' },
  { value: 'other', label: 'Other' },
]

const statusOptions = [
  { value: 'pending', label: 'Pending Review' },
  { value: 'draft', label: 'Draft Created' },
  { value: 'approved', label: 'Approved' },
  { value: 'sent', label: 'Sent' },
]

export const QueueFilters: React.FC<QueueFiltersProps> = ({
  filters,
  onFiltersChange,
  emailCount,
}) => {
  const updateFilter = (key: string, value: string) => {
    onFiltersChange({
      ...filters,
      [key]: value,
    })
  }

  const clearFilters = () => {
    onFiltersChange({
      priority: 'all',
      category: 'all',
      status: 'pending',
    })
  }

  const hasActiveFilters = filters.priority !== 'all' || 
                          filters.category !== 'all' || 
                          filters.status !== 'pending'

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-1 text-sm text-gray-600">
          <FunnelIcon className="h-4 w-4" />
          <span>Filters</span>
          <span className="font-medium">({emailCount} emails)</span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Priority Filter */}
          <div className="flex items-center space-x-2">
            <label htmlFor="priority-filter" className="text-sm font-medium text-gray-700">
              Priority:
            </label>
            <select
              id="priority-filter"
              value={filters.priority}
              onChange={(e) => updateFilter('priority', e.target.value)}
              className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:ring-blue-500 focus:border-blue-500"
            >
              {priorityOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Category Filter */}
          <div className="flex items-center space-x-2">
            <label htmlFor="category-filter" className="text-sm font-medium text-gray-700">
              Category:
            </label>
            <select
              id="category-filter"
              value={filters.category}
              onChange={(e) => updateFilter('category', e.target.value)}
              className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:ring-blue-500 focus:border-blue-500"
            >
              {categoryOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex items-center space-x-2">
            <label htmlFor="status-filter" className="text-sm font-medium text-gray-700">
              Status:
            </label>
            <select
              id="status-filter"
              value={filters.status}
              onChange={(e) => updateFilter('status', e.target.value)}
              className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:ring-blue-500 focus:border-blue-500"
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Search Bar */}
      <div className="mt-4 relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <MagnifyingGlassIcon className="h-4 w-4 text-gray-400" />
        </div>
        <input
          type="text"
          placeholder="Search emails by sender, subject, or content..."
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm"
        />
      </div>
    </div>
  )
}