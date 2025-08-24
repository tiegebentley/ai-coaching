'use client'

import React, { useState } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { useEmailQueue } from '@/hooks/useEmailQueue'
import { EmailQueueItem } from '@/components/emails/EmailQueueItem'
import { EmailPreview } from '@/components/emails/EmailPreview'
import { FamilyContextPanel } from '@/components/emails/FamilyContextPanel'
import { QueueFilters } from '@/components/emails/QueueFilters'
import { BulkActions } from '@/components/emails/BulkActions'
import { Loading, Alert } from '@/components/ui'
import type { EmailMessage } from '@/types'

export default function EmailQueuePage() {
  const [selectedEmail, setSelectedEmail] = useState<EmailMessage | null>(null)
  const [selectedEmails, setSelectedEmails] = useState<string[]>([])
  const [filters, setFilters] = useState({
    priority: 'all',
    category: 'all',
    status: 'pending'
  })

  const { 
    emails, 
    loading, 
    error, 
    approveEmail, 
    editDraft, 
    deferEmail,
    archiveEmail,
    refetch 
  } = useEmailQueue(filters)

  const handleEmailSelect = (emailId: string) => {
    setSelectedEmails(prev => 
      prev.includes(emailId) 
        ? prev.filter(id => id !== emailId)
        : [...prev, emailId]
    )
  }

  const handleEmailClick = (email: EmailMessage) => {
    setSelectedEmail(email)
  }

  const handleApproval = async (emailId: string) => {
    try {
      await approveEmail(emailId)
      // Update UI optimistically
      setSelectedEmail(null)
      refetch()
    } catch (error) {
      console.error('Failed to approve email:', error)
    }
  }

  const handleEdit = async (emailId: string, updatedContent: string) => {
    try {
      await editDraft(emailId, updatedContent)
      refetch()
    } catch (error) {
      console.error('Failed to edit draft:', error)
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loading />
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <Alert 
          variant="error" 
          title="Failed to load email queue"
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
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Email Queue</h1>
            <p className="text-gray-600">
              Review and manage AI-generated email drafts
            </p>
          </div>
          {selectedEmails.length > 0 && (
            <BulkActions 
              selectedIds={selectedEmails}
              onApprove={() => {/* Handle bulk approve */}}
              onDefer={() => {/* Handle bulk defer */}}
              onArchive={() => {/* Handle bulk archive */}}
              onClear={() => setSelectedEmails([])}
            />
          )}
        </div>

        {/* Filters */}
        <QueueFilters 
          filters={filters}
          onFiltersChange={setFilters}
          emailCount={emails.length}
        />

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Email Queue List */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold">
                  Pending Drafts ({emails.length})
                </h2>
              </div>
              <div className="divide-y divide-gray-200">
                {emails.length === 0 ? (
                  <div className="px-6 py-12 text-center">
                    <p className="text-gray-500">No pending email drafts</p>
                  </div>
                ) : (
                  emails.map((email) => (
                    <EmailQueueItem
                      key={email.id}
                      email={email}
                      isSelected={selectedEmails.includes(email.id)}
                      onSelect={() => handleEmailSelect(email.id)}
                      onClick={() => handleEmailClick(email)}
                      onApprove={() => handleApproval(email.id)}
                      onDefer={() => deferEmail(email.id)}
                      onArchive={() => archiveEmail(email.id)}
                    />
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Preview and Context Panel */}
          <div className="space-y-6">
            {selectedEmail && (
              <>
                <EmailPreview
                  email={selectedEmail}
                  onEdit={(content) => handleEdit(selectedEmail.id, content)}
                  onApprove={() => handleApproval(selectedEmail.id)}
                  onClose={() => setSelectedEmail(null)}
                />
                <FamilyContextPanel emailId={selectedEmail.id} />
              </>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}