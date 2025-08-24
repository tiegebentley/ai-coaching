import React from 'react'
import { CheckIcon, ClockIcon, ArchiveBoxIcon, XMarkIcon } from '@heroicons/react/24/outline'
import Button from '@/components/ui/Button'

interface BulkActionsProps {
  selectedIds: string[]
  onApprove: () => void
  onDefer: () => void
  onArchive: () => void
  onClear: () => void
}

export const BulkActions: React.FC<BulkActionsProps> = ({
  selectedIds,
  onApprove,
  onDefer,
  onArchive,
  onClear,
}) => {
  const count = selectedIds.length

  return (
    <div className="flex items-center space-x-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2">
      <span className="text-sm font-medium text-blue-900">
        {count} email{count !== 1 ? 's' : ''} selected
      </span>
      
      <div className="flex items-center space-x-2">
        <Button
          size="sm"
          onClick={onApprove}
          title={`Approve ${count} email${count !== 1 ? 's' : ''}`}
        >
          <CheckIcon className="h-4 w-4 mr-1" />
          Approve All
        </Button>
        
        <Button
          size="sm"
          variant="outline"
          onClick={onDefer}
          title={`Defer ${count} email${count !== 1 ? 's' : ''}`}
        >
          <ClockIcon className="h-4 w-4 mr-1" />
          Defer
        </Button>
        
        <Button
          size="sm"
          variant="outline"
          onClick={onArchive}
          title={`Archive ${count} email${count !== 1 ? 's' : ''}`}
        >
          <ArchiveBoxIcon className="h-4 w-4 mr-1" />
          Archive
        </Button>
        
        <button
          onClick={onClear}
          className="text-blue-600 hover:text-blue-800 p-1"
          title="Clear selection"
        >
          <XMarkIcon className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}