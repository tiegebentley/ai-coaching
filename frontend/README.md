# AI Coaching Management System - Frontend

This is the Next.js frontend for the AI Coaching Management System, built with TypeScript, Tailwind CSS, and modern React patterns.

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS with custom AI Coaching theme
- **State Management**: Zustand
- **API Client**: Custom fetch-based client with error handling
- **Authentication**: JWT-based with Supabase integration
- **Testing**: Jest with Testing Library
- **Code Quality**: ESLint, Prettier, TypeScript strict mode

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── dashboard/         # Dashboard and authenticated pages
│   ├── login/            # Authentication pages
│   ├── globals.css       # Global styles and Tailwind imports
│   ├── layout.tsx        # Root layout with error boundary
│   └── page.tsx          # Landing page
├── components/           # Reusable React components
│   ├── layout/          # Layout components (DashboardLayout)
│   ├── ui/              # Base UI components (Button, Card, etc.)
│   └── ErrorBoundary.tsx # Error handling component
├── hooks/               # Custom React hooks
│   ├── useAuth.ts       # Authentication state and actions
│   └── useApi.ts        # API request handling
├── lib/                # Utility libraries
│   ├── api.ts          # API client with typed responses
│   └── utils.ts        # General utility functions
├── stores/             # Zustand state stores
│   ├── auth.ts         # Authentication store
│   └── dashboard.ts    # Dashboard data store
├── types/              # TypeScript type definitions
│   └── index.ts        # Shared types for API responses, entities
└── styles/             # Additional styling (if needed)
```

## Key Features

### Authentication System
- JWT-based authentication with persistent login
- Role-based access control (Admin, Coach, Assistant)
- Protected routes and components
- Automatic token refresh handling

### Dashboard Interface
- Responsive dashboard with sidebar navigation
- Real-time stats and activity feed
- AI agent activity monitoring
- Email processing status
- Schedule management interface

### API Integration
- Type-safe API client with error handling
- Automatic retry logic for failed requests
- Loading states and error boundaries
- Optimistic updates for better UX

### UI Components
- Consistent design system with AI Coaching branding
- Accessible components following WCAG guidelines
- Loading states and skeleton screens
- Error handling with user-friendly messages

## Development

### Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env.local
   ```
   
   Configure:
   - `NEXT_PUBLIC_API_BASE_URL`: Backend API URL
   - `NEXT_PUBLIC_SUPABASE_URL`: Supabase project URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Supabase public key

3. Start development server:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000)

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript compiler
- `npm run test` - Run Jest tests
- `npm run test:watch` - Run tests in watch mode

### Code Quality

The project enforces code quality through:

- **TypeScript**: Strict type checking with no implicit any
- **ESLint**: Code linting with Next.js and TypeScript rules
- **Prettier**: Automatic code formatting
- **Tailwind**: Consistent utility-first styling
- **Component Patterns**: Consistent prop interfaces and error handling

### Testing

- **Unit Tests**: Component and utility function tests
- **Integration Tests**: API client and store integration
- **E2E Tests**: Critical user journey testing (planned)

## Architecture Decisions

### State Management
- **Zustand** for global state (auth, dashboard data)
- **React State** for component-local state
- **Persistent Storage** for authentication state

### API Design
- **Type-safe responses** with consistent error handling
- **Loading states** for better user experience
- **Error boundaries** to prevent app crashes
- **Retry logic** for network resilience

### Styling Strategy
- **Tailwind CSS** for consistent design system
- **Custom color palette** for AI Coaching branding
- **Responsive design** mobile-first approach
- **Component variants** for reusable patterns

### Security
- **JWT authentication** with secure storage
- **CORS configuration** for API communication
- **Input validation** on all forms
- **XSS protection** through proper escaping

## Deployment

The frontend is configured for deployment on Vercel with:

- **Static generation** for marketing pages
- **Server-side rendering** for authenticated pages
- **API routes** for authentication callbacks
- **Edge functions** for optimal performance

## Contributing

1. Follow the established code patterns
2. Write tests for new components
3. Update types when adding new API endpoints
4. Use semantic commit messages
5. Ensure all lints and tests pass