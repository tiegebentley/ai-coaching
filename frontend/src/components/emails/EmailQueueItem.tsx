import React from 'react'
import { CheckIcon, ClockIcon, ArchiveBoxIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import Button from '@/components/ui/Button'
import type { EmailMessage } from '@/types'

interface EmailQueueItemProps {
  email: EmailMessage
  isSelected: boolean
  onSelect: () => void
  onClick: () => void
  onApprove: () => void
  onDefer: () => void
  onArchive: () => void
}

const priorityColors = {
  low: 'bg-gray-100 text-gray-800',
  medium: 'bg-blue-100 text-blue-800',
  high: 'bg-orange-100 text-orange-800',
  urgent: 'bg-red-100 text-red-800',
}

const categoryLabels = {
  schedule_request: 'Schedule',
  payment_inquiry: 'Payment',
  absence_notice: 'Absence',
  general_question: 'Question',
  complaint: 'Complaint',
  feedback: 'Feedback',
  emergency: 'Emergency',
  other: 'Other',
}

export const EmailQueueItem: React.FC<EmailQueueItemProps> = ({
  email,
  isSelected,
  onSelect,
  onClick,
  onApprove,
  onDefer,
  onArchive,
}) => {
  const handleClick = (e: React.MouseEvent) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLButtonElement) {
      return // Don't trigger click when interacting with controls
    }
    onClick()
  }

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const getConfidenceColor = (aiSummary?: string) => {
    // This would typically come from AI confidence score
    // For now, use a simple heuristic based on content length
    if (!aiSummary) return 'bg-gray-400'
    if (aiSummary.length > 100) return 'bg-green-400'
    if (aiSummary.length > 50) return 'bg-yellow-400'
    return 'bg-red-400'
  }

  return (
    <div 
      className={`px-6 py-4 hover:bg-gray-50 cursor-pointer transition-colors ${
        isSelected ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
      }`}
      onClick={handleClick}
    >
      <div className="flex items-start space-x-4">
        {/* Selection Checkbox */}
        <div className="flex items-center pt-1">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onSelect}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
        </div>

        {/* Email Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-3">
              <h3 className="text-sm font-medium text-gray-900 truncate">
                {email.subject}
              </h3>
              <div className="flex items-center space-x-2">
                {/* Priority Badge */}
                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${priorityColors[email.priority]}`}>
                  {email.priority}
                </span>
                
                {/* Category Badge */}
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                  {categoryLabels[email.category]}
                </span>

                {/* Confidence Indicator */}
                <div className="flex items-center space-x-1">
                  <div className={`w-2 h-2 rounded-full ${getConfidenceColor(email.aiSummary)}`} />
                  <span className="text-xs text-gray-500">AI</span>
                </div>
              </div>
            </div>
            <ChevronRightIcon className="h-5 w-5 text-gray-400" />
          </div>

          <div className="mb-2">
            <p className="text-sm text-gray-600">
              <span className="font-medium">From:</span> {email.sender} ({email.senderEmail})
            </p>
            <p className="text-xs text-gray-500">
              Received: {formatTime(email.receivedAt)}
            </p>
          </div>

          {/* AI Summary Preview */}
          {email.aiSummary && (
            <div className="mb-3">
              <p className="text-sm text-gray-700 line-clamp-2">
                <span className="font-medium text-blue-600">AI Summary:</span> {email.aiSummary}
              </p>
            </div>
          )}

          {/* Extracted Info */}
          {email.extractedInfo && (
            <div className="mb-3 text-xs text-gray-600">
              {email.extractedInfo.childName && (
                <span className="inline-block mr-4">
                  <span className="font-medium">Child:</span> {email.extractedInfo.childName}
                </span>
              )}
              {email.extractedInfo.sessionDate && (
                <span className="inline-block mr-4">
                  <span className="font-medium">Date:</span> {email.extractedInfo.sessionDate}
                </span>
              )}
              {email.extractedInfo.requestType && (
                <span className="inline-block">
                  <span className="font-medium">Type:</span> {email.extractedInfo.requestType}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-2">
          <Button
            size="sm"
            variant="outline"
            onClick={(e: React.MouseEvent) => {
              e.stopPropagation()
              onDefer()
            }}
            title="Defer"
          >
            <ClockIcon className="h-4 w-4" />
          </Button>
          
          <Button
            size="sm"
            variant="outline"
            onClick={(e: React.MouseEvent) => {
              e.stopPropagation()
              onArchive()
            }}
            title="Archive"
          >
            <ArchiveBoxIcon className="h-4 w-4" />
          </Button>
          
          <Button
            size="sm"
            onClick={(e: React.MouseEvent) => {
              e.stopPropagation()
              onApprove()
            }}
            title="Approve & Send"
          >
            <CheckIcon className="h-4 w-4 mr-1" />
            Approve
          </Button>
        </div>
      </div>
    </div>
  )
}