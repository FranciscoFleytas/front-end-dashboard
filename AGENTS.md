# AGENTS.md

This document provides guidelines for agentic coding agents operating in this repository.

## Build, Lint, and Test Commands

```bash
# Development server with hot reload
pnpm dev

# Build for production
pnpm build

# Preview production build locally
pnpm preview

# Generate Nuxt types and prepare project
pnpm postinstall

# Run ESLint on entire codebase
pnpm lint

# Run TypeScript type checking
pnpm typecheck

# Auto-fix ESLint issues
pnpm lint --fix
```

### Testing

This project currently has no test files configured. To add testing:

```bash
# Install testing dependencies (when needed)
pnpm add -D vitest @nuxt/test-utils

# Run tests (when configured)
pnpm test

# Run single test file (when configured)
pnpm test path/to/test.spec.ts
```

## Code Style Guidelines

### TypeScript

- Use strict TypeScript mode (Nuxt 4 default)
- Prefer explicit types for function parameters and return values
- Use interfaces for object shapes, types for unions/primitives
- Avoid `any` type; use `unknown` when type is uncertain
- Use Zod for runtime validation (already included as dependency)

### Vue Components

- Use `<script setup lang="ts">` syntax for all components
- Components should be auto-imported from `~/components` directory
- Organize props with `defineProps` using TypeScript generics
- Use computed properties for derived state
- Avoid mutating props directly; emit events instead

### API Endpoints

- Server API endpoints in `server/api/` directory
- Use `$fetch` for API calls with proper error handling
- Return consistent error responses with status codes
- Use Zod schemas for request/response validation

### Component Patterns

- Use `<script setup>` with explicit imports
- Define page meta with `definePageMeta` for layout/middleware
- Use `<template>` with semantic HTML structure
- Use `<style>` with scoped CSS when needed

### Performance

- Use `import.meta.client` for client-side only code
- Lazy load components with `defineAsyncComponent` when needed
- Use `onMounted` for DOM-dependent operations
- Optimize images with `@nuxt/image` module

## Project-Specific Guidelines

### Authentication Flow

```typescript
// Correct auth pattern
const { login, logout, isAuthenticated } = useAuth()

// Login with error handling
const result = await login(email, password)
if (!result.success) {
  // Handle error
}
```

### Dashboard Pages

```typescript
// Dashboard page pattern
definePageMeta({
  layout: 'dashboard'
  // No middleware needed - handled by auth.global.ts
})
```

### API Response Format

```typescript
// Standard API response
{
  user: User,
  token: string
}

// Error response
{
  statusCode: 401,
  statusMessage: 'Invalid credentials'
}
```

## Dependencies

### Core Dependencies
- `@nuxt/ui` - UI component library
- `@vueuse/nuxt` - Vue composables
- `zod` - Runtime validation
- `date-fns` - Date utilities

### Dev Dependencies
- `@nuxt/eslint` - ESLint configuration
- `typescript` - TypeScript compiler
- `vue-tsc` - Vue TypeScript checking

## Environment

- **Node.js**: Use pnpm as package manager
- **Browser**: Modern browsers with ES2020+ support
- **Development**: Use `pnpm dev` for local development
- **Production**: Use `pnpm build` for production builds

## Security

- Never commit secrets or API keys
- Use environment variables for sensitive data
- Validate all user inputs with Zod schemas
- Use HTTPS for all API endpoints in production
- Implement proper authentication middleware

## Testing Strategy

When adding tests:
- Use Vitest for unit testing
- Use @nuxt/test-utils for component testing
- Test composables independently
- Test API endpoints with mock data
- Test authentication flows end-to-end

## Common Issues

### Middleware Errors
- Use `auth.global.ts` for global middleware
- Don't declare `middleware: 'auth'` in pages
- Check `isAuthenticated` state in middleware

### TypeScript Errors
- Run `pnpm typecheck` to verify types
- Use explicit types for API responses
- Import types from `~/types/` directory

### ESLint Issues
- Run `pnpm lint --fix` for auto-formatting
- Check for unused variables and imports
- Follow Vue 3 composition API patterns