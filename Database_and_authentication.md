# Database and Authentication - Complete Reference

## 📚 Table of Contents
1. [Implementation Files](#implementation-files)
2. [Database Schema](#database-schema)
3. [Environment Variables](#environment-variables)
4. [Quick Integration Guide](#quick-integration-guide)
5. [Authentication Patterns](#authentication-patterns)
6. [Database Operations](#database-operations)
7. [Protected API Routes](#protected-api-routes)

---

## 🗂️ Implementation Files

### 1. Client-Side Supabase Client
**File:** `src/lib/supabase/client.ts`

```typescript
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
    return createBrowserClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )
}
```

**Usage:** Import in client components for browser-side authentication and data operations.

---

### 2. Server-Side Supabase Client
**File:** `src/lib/supabase/server.ts`

```typescript
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createClient() {
    const cookieStore = await cookies()

    return createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() {
                    return cookieStore.getAll()
                },
                setAll(cookiesToSet) {
                    try {
                        cookiesToSet.forEach(({ name, value, options }) =>
                            cookieStore.set(name, value, options)
                        )
                    } catch {
                        // The `setAll` method was called from a Server Component.
                        // This can be ignored if you have middleware refreshing
                        // user sessions.
                    }
                },
            },
        }
    )
}
```

**Usage:** Import in server components, API routes, and server actions.

---

### 3. Middleware for Session Management
**File:** `src/lib/supabase/middleware.ts`

```typescript
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function updateSession(request: NextRequest) {
    let response = NextResponse.next({
        request: {
            headers: request.headers,
        },
    })

    const supabase = createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() {
                    return request.cookies.getAll()
                },
                setAll(cookiesToSet) {
                    cookiesToSet.forEach(({ name, value, options }) =>
                        request.cookies.set(name, value)
                    )
                    response = NextResponse.next({
                        request: {
                            headers: request.headers,
                        },
                    })
                    cookiesToSet.forEach(({ name, value, options }) =>
                        response.cookies.set(name, value, options)
                    )
                },
            },
        }
    )

    await supabase.auth.getUser()

    return response
}
```

**Usage:** Call from `middleware.ts` at project root to refresh authentication sessions.

---

## 🗄️ Database Schema

### User API Keys Table
**File:** `supabase_schema.sql`

Run this SQL in your Supabase dashboard SQL Editor:

```sql
-- Create table for storing user API keys
create table if not exists public.user_api_keys (
  user_id uuid primary key references auth.users(id) on delete cascade,
  openai_api_key text,
  openrouter_api_key text,
  serper_api_key text,
  tavily_api_key text,
  openai_provider text check (openai_provider in ('openai', 'openrouter')),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Index on user_id
create index if not exists idx_user_api_keys_user_id on public.user_api_keys(user_id);

-- Enable Row Level Security
alter table public.user_api_keys enable row level security;

-- RLS Policies
create policy "Users can view own keys"
  on public.user_api_keys
  for select
  using (auth.uid() = user_id);

create policy "Users can upsert own keys"
  on public.user_api_keys
  for insert
  with check (auth.uid() = user_id);

create policy "Users can update own keys"
  on public.user_api_keys
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
```

---

## 🔐 Environment Variables

**File:** `.env.local`

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=your-project-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

**How to get these values:**
1. Go to your Supabase project dashboard
2. Navigate to Settings → API
3. Copy the values from the API settings page

---

## 🚀 Quick Integration Guide

### Import the Correct Client

#### In Client Components:
```typescript
'use client'
import { createClient } from '@/lib/supabase/client'

const supabase = createClient()
```

#### In Server Components & API Routes:
```typescript
import { createClient } from '@/lib/supabase/server'

const supabase = await createClient()
```

---

## 🔐 Authentication Patterns

### 1. Protect a Server Component Page

```typescript
// app/dashboard/page.tsx
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

export default async function DashboardPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    redirect('/login')
  }
  
  return (
    <div>
      <h1>Welcome {user.email}</h1>
      {/* Your protected content */}
    </div>
  )
}
```

### 2. Get Current User in Client Component

```typescript
'use client'
import { createClient } from '@/lib/supabase/client'
import { useEffect, useState } from 'react'

export default function UserProfile() {
  const [user, setUser] = useState(null)
  const supabase = createClient()
  
  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      setUser(user)
    }
    getUser()
  }, [])
  
  if (!user) return <div>Loading...</div>
  
  return <div>Email: {user.email}</div>
}
```

### 3. Sign In with Email/Password

```typescript
const supabase = createClient()

const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password123'
})

if (error) {
  console.error('Login failed:', error.message)
} else {
  console.log('Logged in:', data.user)
}
```

### 4. Sign Up New User

```typescript
const supabase = createClient()

const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password123'
})

if (error) {
  console.error('Signup failed:', error.message)
} else {
  console.log('User created:', data.user)
}
```

### 5. Sign Out

```typescript
const supabase = createClient()

await supabase.auth.signOut()
// Then redirect to home page
router.push('/')
```

### 6. Listen to Auth State Changes

```typescript
'use client'
import { createClient } from '@/lib/supabase/client'
import { useEffect } from 'react'

export default function AuthListener() {
  const supabase = createClient()
  
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        console.log('Auth event:', event)
        console.log('Session:', session)
        
        if (event === 'SIGNED_IN') {
          // User signed in
        } else if (event === 'SIGNED_OUT') {
          // User signed out
        }
      }
    )
    
    return () => subscription.unsubscribe()
  }, [])
  
  return null
}
```

---

## 💾 Database Operations

### 1. Fetch User's API Keys (Server-Side)

```typescript
// app/api/keys/route.ts
import { createClient } from '@/lib/supabase/server'

export async function GET() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 })
  }
  
  const { data, error } = await supabase
    .from('user_api_keys')
    .select('*')
    .eq('user_id', user.id)
    .single()
  
  if (error) {
    return Response.json({ error: error.message }, { status: 500 })
  }
  
  // Return presence flags only, not actual keys
  return Response.json({
    has_openai_key: !!data?.openai_api_key,
    has_openrouter_key: !!data?.openrouter_api_key,
    has_serper_key: !!data?.serper_api_key,
    has_tavily_key: !!data?.tavily_api_key,
    openai_provider: data?.openai_provider || 'openai'
  })
}
```

### 2. Save/Update API Keys

```typescript
// app/api/keys/route.ts
export async function POST(request: Request) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 })
  }
  
  const body = await request.json()
  
  const { error } = await supabase
    .from('user_api_keys')
    .upsert({
      user_id: user.id,
      openai_api_key: body.openai_api_key,
      openrouter_api_key: body.openrouter_api_key,
      serper_api_key: body.serper_api_key,
      tavily_api_key: body.tavily_api_key,
      openai_provider: body.openai_provider,
      updated_at: new Date().toISOString()
    })
  
  if (error) {
    return Response.json({ error: error.message }, { status: 500 })
  }
  
  return Response.json({ success: true })
}
```

### 3. Select Data with Filters

```typescript
const { data, error } = await supabase
  .from('table_name')
  .select('*')
  .eq('user_id', userId)
  .order('created_at', { ascending: false })
  .limit(10)
```

### 4. Insert New Record

```typescript
const { data, error } = await supabase
  .from('table_name')
  .insert({
    column1: 'value1',
    column2: 'value2'
  })
```

### 5. Update Existing Record

```typescript
const { data, error } = await supabase
  .from('table_name')
  .update({ column1: 'new_value' })
  .eq('id', recordId)
```

### 6. Delete Record

```typescript
const { data, error } = await supabase
  .from('table_name')
  .delete()
  .eq('id', recordId)
```

---

## 🛡️ Protected API Routes Pattern

Standard pattern for protecting API routes:

```typescript
// app/api/protected-endpoint/route.ts
import { createClient } from '@/lib/supabase/server'

export async function POST(request: Request) {
  // 1. Authenticate user
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  // 2. Guard clause
  if (!user) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 })
  }
  
  // 3. Get user's data/keys if needed
  const { data: keys } = await supabase
    .from('user_api_keys')
    .select('*')
    .eq('user_id', user.id)
    .single()
  
  // 4. Validate required data
  if (!keys?.openai_api_key) {
    return Response.json(
      { error: 'API keys not configured' }, 
      { status: 400 }
    )
  }
  
  // 5. Process request with user's data
  const requestBody = await request.json()
  const result = await yourBusinessLogic(keys, requestBody)
  
  // 6. Return response
  return Response.json(result)
}
```

---

## 🎯 Common Use Cases

### Use Case 1: Fetch User-Specific Data in Server Component

```typescript
// app/settings/page.tsx
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

export default async function SettingsPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) redirect('/login')
  
  const { data: apiKeys } = await supabase
    .from('user_api_keys')
    .select('*')
    .eq('user_id', user.id)
    .single()
  
  return (
    <div>
      <h1>Settings for {user.email}</h1>
      <p>OpenAI Provider: {apiKeys?.openai_provider}</p>
    </div>
  )
}
```

### Use Case 2: Real-Time Data Subscription (Client Component)

```typescript
'use client'
import { createClient } from '@/lib/supabase/client'
import { useEffect, useState } from 'react'

export default function RealtimeData() {
  const [data, setData] = useState([])
  const supabase = createClient()
  
  useEffect(() => {
    // Subscribe to real-time changes
    const channel = supabase
      .channel('table_changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'your_table' },
        (payload) => {
          console.log('Change received:', payload)
          // Update state based on payload
        }
      )
      .subscribe()
    
    return () => {
      supabase.removeChannel(channel)
    }
  }, [])
  
  return <div>Realtime Data Display</div>
}
```

### Use Case 3: Call Protected API from Client Component

```typescript
'use client'
import { useState } from 'react'

export default function SearchForm() {
  const [results, setResults] = useState(null)
  
  const handleSearch = async (query: string) => {
    const response = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    })
    
    if (response.ok) {
      const data = await response.json()
      setResults(data)
    } else {
      console.error('Search failed')
    }
  }
  
  return (
    <form onSubmit={(e) => {
      e.preventDefault()
      handleSearch(e.target.query.value)
    }}>
      <input name="query" placeholder="Search..." />
      <button type="submit">Search</button>
    </form>
  )
}
```

---

## ⚠️ Important Security Notes

1. **Never expose API keys to the client** - Always fetch and use them server-side only
2. **Enable Row Level Security (RLS)** - Always enable RLS on your Supabase tables
3. **Use environment variables** - Store sensitive credentials in `.env.local`
4. **Validate user input** - Always validate and sanitize user input before database operations
5. **Use HTTPS in production** - Ensure your production environment uses HTTPS
6. **Handle errors gracefully** - Never expose detailed error messages to clients
7. **Implement rate limiting** - Add rate limiting to protect against abuse

---

## 📋 Integration Checklist

When adding database/auth to a new file:

- [ ] Import the correct Supabase client (`client.ts` for client, `server.ts` for server)
- [ ] Get the authenticated user with `supabase.auth.getUser()`
- [ ] Add authentication guard (redirect/return error if not authenticated)
- [ ] Perform database operations with proper error handling
- [ ] Return appropriate responses (200, 401, 500, etc.)
- [ ] Test with both authenticated and unauthenticated states
- [ ] Ensure no sensitive data is exposed to the client

---

## 🔗 Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Next.js App Router + Supabase](https://supabase.com/docs/guides/auth/server-side/nextjs)
- [Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)
- [Supabase JavaScript Client](https://supabase.com/docs/reference/javascript/introduction)
