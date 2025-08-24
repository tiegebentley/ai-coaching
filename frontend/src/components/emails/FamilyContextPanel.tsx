import React from 'react'
import { UserGroupIcon, CreditCardIcon, CalendarIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Loading, Alert } from '@/components/ui'
import { useFamilyContext } from '@/hooks/useFamilyContext'

interface FamilyContextPanelProps {
  emailId: string
}

export const FamilyContextPanel: React.FC<FamilyContextPanelProps> = ({ emailId }) => {
  const { family, sessions, loading, error } = useFamilyContext(emailId)

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loading />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Alert 
        variant="error"
        title="Failed to load family context"
        description={error}
      />
    )
  }

  if (!family) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center text-lg">
            <UserGroupIcon className="h-5 w-5 mr-2" />
            Family Context
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">No family information available</p>
        </CardContent>
      </Card>
    )
  }

  const getPaymentStatusColor = (status: string) => {
    switch (status) {
      case 'current':
        return 'bg-green-100 text-green-800'
      case 'overdue':
        return 'bg-red-100 text-red-800'
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const upcomingSessions = sessions.filter(session => 
    new Date(session.startTime) > new Date()
  )

  const recentSessions = sessions.filter(session => 
    new Date(session.startTime) <= new Date()
  ).slice(0, 3)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center text-lg">
          <UserGroupIcon className="h-5 w-5 mr-2" />
          Family Context
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Family Overview */}
        <div className="pb-4 border-b">
          <h4 className="font-semibold text-sm text-gray-900 mb-2">{family.familyName} Family</h4>
          
          {/* Primary Contact */}
          <div className="space-y-1 text-sm">
            <p className="font-medium text-gray-700">Primary Contact</p>
            <p className="text-gray-600">{family.primaryContact.name}</p>
            <p className="text-gray-600">{family.primaryContact.email}</p>
            <p className="text-gray-600">{family.primaryContact.phone}</p>
          </div>
          
          {/* Secondary Contact */}
          {family.secondaryContact && (
            <div className="space-y-1 text-sm mt-3">
              <p className="font-medium text-gray-700">Secondary Contact</p>
              <p className="text-gray-600">{family.secondaryContact.name}</p>
              <p className="text-gray-600">{family.secondaryContact.email}</p>
            </div>
          )}
        </div>

        {/* Payment Status */}
        <div className="pb-4 border-b">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-semibold text-sm text-gray-900 flex items-center">
              <CreditCardIcon className="h-4 w-4 mr-1" />
              Payment Status
            </h4>
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPaymentStatusColor(family.paymentStatus)}`}>
              {family.paymentStatus}
            </span>
          </div>
          {family.paymentStatus === 'overdue' && (
            <div className="flex items-start space-x-2 p-2 bg-red-50 rounded">
              <ExclamationTriangleIcon className="h-4 w-4 text-red-600 mt-0.5" />
              <p className="text-xs text-red-800">Payment is overdue. Handle with care.</p>
            </div>
          )}
        </div>

        {/* Children */}
        <div className="pb-4 border-b">
          <h4 className="font-semibold text-sm text-gray-900 mb-2">Children ({family.children.length})</h4>
          <div className="space-y-2">
            {family.children.map((child) => (
              <div key={child.id} className="text-sm">
                <div className="flex justify-between items-center">
                  <span className="font-medium">{child.name}</span>
                  <span className="text-xs text-gray-500 capitalize">{child.skillLevel}</span>
                </div>
                <p className="text-xs text-gray-600">
                  Age: {new Date().getFullYear() - new Date(child.dateOfBirth).getFullYear()}
                  {child.grade && ` • Grade: ${child.grade}`}
                </p>
                {child.medicalNotes && (
                  <div className="flex items-start space-x-1 mt-1 p-1 bg-yellow-50 rounded">
                    <ExclamationTriangleIcon className="h-3 w-3 text-yellow-600 mt-0.5" />
                    <p className="text-xs text-yellow-800">{child.medicalNotes}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Upcoming Sessions */}
        {upcomingSessions.length > 0 && (
          <div className="pb-4 border-b">
            <h4 className="font-semibold text-sm text-gray-900 mb-2 flex items-center">
              <CalendarIcon className="h-4 w-4 mr-1" />
              Upcoming Sessions ({upcomingSessions.length})
            </h4>
            <div className="space-y-2">
              {upcomingSessions.slice(0, 3).map((session) => (
                <div key={session.id} className="text-sm">
                  <p className="font-medium">{session.title}</p>
                  <p className="text-xs text-gray-600">
                    {new Date(session.startTime).toLocaleDateString()} at{' '}
                    {new Date(session.startTime).toLocaleTimeString([], { 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </p>
                  <p className="text-xs text-gray-500">
                    {session.venue.name} • Coach: {session.coach.name}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Sessions */}
        {recentSessions.length > 0 && (
          <div>
            <h4 className="font-semibold text-sm text-gray-900 mb-2">Recent Sessions</h4>
            <div className="space-y-2">
              {recentSessions.map((session) => (
                <div key={session.id} className="text-sm">
                  <p className="font-medium">{session.title}</p>
                  <p className="text-xs text-gray-600">
                    {new Date(session.startTime).toLocaleDateString()}
                    <span className={`ml-2 px-1 py-0.5 rounded text-xs ${
                      session.status === 'completed' ? 'bg-green-100 text-green-700' :
                      session.status === 'cancelled' ? 'bg-red-100 text-red-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {session.status}
                    </span>
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Special Notes */}
        {family.specialNotes && (
          <div className="pt-4 border-t">
            <h4 className="font-semibold text-sm text-gray-900 mb-2">Special Notes</h4>
            <div className="p-2 bg-blue-50 rounded">
              <p className="text-xs text-blue-800">{family.specialNotes}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}