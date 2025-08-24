import React, { useState } from 'react'
import { XMarkIcon, PencilIcon, CheckIcon, ArrowTopRightOnSquareIcon } from '@heroicons/react/24/outline'
import Button from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import type { EmailMessage } from '@/types'

interface EmailPreviewProps {
  email: EmailMessage
  onEdit: (content: string) => void
  onApprove: () => void
  onClose: () => void
}

export const EmailPreview: React.FC<EmailPreviewProps> = ({
  email,
  onEdit,
  onApprove,
  onClose,
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [draftContent, setDraftContent] = useState(email.body)
  const [originalContent] = useState(email.body)

  const handleSaveEdit = () => {
    if (draftContent !== originalContent) {
      onEdit(draftContent)
    }
    setIsEditing(false)
  }

  const handleCancelEdit = () => {
    setDraftContent(originalContent)
    setIsEditing(false)
  }

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  return (
    <Card className="h-fit">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Email Preview</CardTitle>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Original Email Info */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-semibold text-sm text-gray-900 mb-2">Original Email</h4>
          <div className="space-y-1 text-sm text-gray-600">
            <p><span className="font-medium">Subject:</span> {email.subject}</p>
            <p><span className="font-medium">From:</span> {email.sender} ({email.senderEmail})</p>
            <p><span className="font-medium">Received:</span> {formatTime(email.receivedAt)}</p>
            <p><span className="font-medium">Priority:</span> 
              <span className={`ml-1 px-2 py-1 rounded text-xs ${
                email.priority === 'urgent' ? 'bg-red-100 text-red-800' :
                email.priority === 'high' ? 'bg-orange-100 text-orange-800' :
                email.priority === 'medium' ? 'bg-blue-100 text-blue-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {email.priority}
              </span>
            </p>
          </div>
        </div>

        {/* AI Summary */}
        {email.aiSummary && (
          <div className="bg-blue-50 rounded-lg p-4">
            <h4 className="font-semibold text-sm text-blue-900 mb-2">AI Summary</h4>
            <p className="text-sm text-blue-800">{email.aiSummary}</p>
          </div>
        )}

        {/* Extracted Information */}
        {email.extractedInfo && Object.keys(email.extractedInfo).length > 0 && (
          <div className="bg-green-50 rounded-lg p-4">
            <h4 className="font-semibold text-sm text-green-900 mb-2">Extracted Information</h4>
            <div className="grid grid-cols-1 gap-2 text-sm">
              {email.extractedInfo.childName && (
                <p><span className="font-medium">Child Name:</span> {email.extractedInfo.childName}</p>
              )}
              {email.extractedInfo.sessionDate && (
                <p><span className="font-medium">Session Date:</span> {email.extractedInfo.sessionDate}</p>
              )}
              {email.extractedInfo.requestType && (
                <p><span className="font-medium">Request Type:</span> {email.extractedInfo.requestType}</p>
              )}
              {email.extractedInfo.paymentAmount && (
                <p><span className="font-medium">Payment Amount:</span> ${email.extractedInfo.paymentAmount}</p>
              )}
              {email.extractedInfo.urgencyLevel && (
                <p><span className="font-medium">Urgency:</span> {email.extractedInfo.urgencyLevel}</p>
              )}
              {email.extractedInfo.actionRequired && (
                <div>
                  <p className="font-medium">Actions Required:</p>
                  <ul className="list-disc list-inside ml-2">
                    {email.extractedInfo.actionRequired.map((action, index) => (
                      <li key={index} className="text-sm">{action}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* AI Generated Draft */}
        <div className="border rounded-lg">
          <div className="flex items-center justify-between p-4 border-b bg-gray-50">
            <h4 className="font-semibold text-sm text-gray-900">AI Generated Response</h4>
            {!isEditing && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsEditing(true)}
              >
                <PencilIcon className="h-4 w-4 mr-1" />
                Edit
              </Button>
            )}
          </div>
          
          <div className="p-4">
            {isEditing ? (
              <div className="space-y-4">
                <textarea
                  value={draftContent}
                  onChange={(e) => setDraftContent(e.target.value)}
                  className="w-full h-40 p-3 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 resize-none"
                  placeholder="Edit the draft response..."
                />
                <div className="flex justify-end space-x-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleCancelEdit}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleSaveEdit}
                  >
                    <CheckIcon className="h-4 w-4 mr-1" />
                    Save Changes
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="prose prose-sm max-w-none">
                  <div className="whitespace-pre-wrap text-sm text-gray-700">
                    {draftContent}
                  </div>
                </div>
                
                {/* Character/Word Count */}
                <div className="text-xs text-gray-500 border-t pt-2">
                  {draftContent.length} characters • {draftContent.split(/\s+/).length} words
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        {!isEditing && (
          <div className="flex space-x-3 pt-4 border-t">
            <Button
              onClick={onApprove}
              className="flex-1"
            >
              <CheckIcon className="h-4 w-4 mr-2" />
              Approve & Send
            </Button>
            
            <Button
              variant="outline"
              onClick={() => window.open(`mailto:${email.senderEmail}`, '_blank')}
              title="Open in Email Client"
            >
              <ArrowTopRightOnSquareIcon className="h-4 w-4" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}