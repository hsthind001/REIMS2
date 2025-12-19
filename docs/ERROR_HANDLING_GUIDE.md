# Error Handling Guide - Preventing React Rendering Errors

## Overview

This guide ensures the REIMS2 system is intelligent enough to prevent "Objects are not valid as a React child" errors from occurring in the future.

## The Problem

React cannot render objects directly. When error objects are passed to React components, you get:
```
Error: Objects are not valid as a React child (found: object with keys {error, ...})
```

## The Solution

We've implemented a comprehensive error handling system with multiple layers of protection:

### 1. Error Extraction Utilities (`src/utils/errorHandling.ts`)

**Always use `extractErrorMessage()` to convert any error to a safe string:**

```typescript
import { extractErrorMessage } from '../utils/errorHandling';

// ✅ CORRECT - Always safe
const errorMsg = extractErrorMessage(error);
<div>{errorMsg}</div>

// ❌ WRONG - Can crash if error is an object
<div>{error.message}</div>
```

**Features:**
- Handles strings, Error objects, API errors, nested objects
- Always returns a safe string
- Intelligent extraction from various error formats
- Never throws - always returns a fallback string

### 2. Safe Error Display Component (`src/components/SafeErrorDisplay.tsx`)

**Use this component to display errors safely:**

```tsx
import { SafeErrorDisplay } from '../components/SafeErrorDisplay';

// ✅ CORRECT - Handles any error format
<SafeErrorDisplay error={apiError} alert variant="error" />

// ❌ WRONG - Can crash
<div className="alert">{error}</div>
```

### 3. Runtime Validation (`assertSafeForRender()`)

**Use in development to catch unsafe values early:**

```typescript
import { assertSafeForRender } from '../utils/errorHandling';

function MyComponent({ data }) {
  // In development, this will throw if data is an object
  assertSafeForRender(data, 'MyComponent render');
  return <div>{data}</div>;
}
```

## Best Practices

### ✅ DO:

1. **Always use `extractErrorMessage()` for error handling:**
   ```typescript
   catch (err) {
     setError(extractErrorMessage(err, 'Operation failed'));
   }
   ```

2. **Use `SafeErrorDisplay` component:**
   ```tsx
   {error && <SafeErrorDisplay error={error} alert variant="error" />}
   ```

3. **Validate before rendering:**
   ```typescript
   const safeValue = toSafeString(value, 'N/A');
   return <div>{safeValue}</div>;
   ```

4. **Use type guards:**
   ```typescript
   if (isApiError(error)) {
     // TypeScript knows error is ApiError
     handleApiError(error);
   }
   ```

### ❌ DON'T:

1. **Never render error objects directly:**
   ```tsx
   // ❌ WRONG
   <div>{error}</div>
   <div>{error.message}</div>  // If message is an object, this crashes
   ```

2. **Don't assume error structure:**
   ```typescript
   // ❌ WRONG - Assumes error.message exists and is a string
   const msg = error.message;
   ```

3. **Don't use JSON.stringify in JSX:**
   ```tsx
   // ❌ WRONG - Can still cause issues
   <div>{JSON.stringify(error)}</div>
   ```

## Migration Guide

### Updating Existing Components

**Before:**
```tsx
catch (err: any) {
  setError(err.message || 'Failed');
}
// ...
{error && <div className="alert">{error}</div>}
```

**After:**
```tsx
import { extractErrorMessage } from '../utils/errorHandling';
import { SafeErrorDisplay } from '../components/SafeErrorDisplay';

catch (err: any) {
  setError(extractErrorMessage(err, 'Failed'));
}
// ...
{error && <SafeErrorDisplay error={error} alert variant="error" />}
```

## API Error Handling

The API client (`src/lib/api.ts`) now uses intelligent error extraction. All API errors are automatically converted to safe strings.

**Error formats handled:**
- FastAPI: `{ detail: string | object }`
- Custom: `{ message: string, error: string, detail: object }`
- Nested objects with message properties
- Plain strings and Error objects

## TypeScript Types

Use the provided types for better type safety:

```typescript
import type { ErrorLike, ApiError } from '../utils/errorHandling';

function handleError(error: ErrorLike) {
  const message = extractErrorMessage(error);
  // ...
}
```

## ESLint Rules

We've added ESLint rules to catch potential issues:
- Warns about `any` types
- Warns about useless fragments

## Testing

All error handling utilities are designed to:
- Never throw exceptions
- Always return a string
- Handle edge cases gracefully
- Work in both development and production

## Examples

### Example 1: API Error Handling

```tsx
import { extractErrorMessage } from '../utils/errorHandling';

try {
  await api.post('/endpoint', data);
} catch (err) {
  // Safe - handles any error format
  const message = extractErrorMessage(err, 'Request failed');
  showNotification(message);
}
```

### Example 2: Form Error Display

```tsx
import { SafeErrorDisplay } from '../components/SafeErrorDisplay';

function MyForm() {
  const [error, setError] = useState<ErrorLike>(null);
  
  return (
    <form>
      {error && (
        <SafeErrorDisplay 
          error={error} 
          alert 
          variant="error" 
        />
      )}
      {/* form fields */}
    </form>
  );
}
```

### Example 3: Error Boundary

The `ErrorBoundary` component now uses `extractErrorMessage()` to safely display errors.

## Future-Proofing

This system prevents the entire class of "object rendering" errors by:

1. **Type Safety:** TypeScript types guide correct usage
2. **Runtime Safety:** Utilities ensure safe conversion
3. **Component Safety:** SafeErrorDisplay handles all cases
4. **Development Warnings:** assertSafeForRender catches issues early
5. **ESLint Rules:** Static analysis catches potential problems

## Summary

**Always remember:**
- ✅ Use `extractErrorMessage()` for error handling
- ✅ Use `SafeErrorDisplay` for error display
- ✅ Never render objects directly in JSX
- ✅ Validate values before rendering

This ensures the system is intelligent enough to prevent React rendering errors from occurring in the future.

