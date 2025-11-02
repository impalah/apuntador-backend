# Apuntador Client Integration with OAuth Backend

This guide explains how to modify the Apuntador client to use the centralized OAuth backend.

## OAuth Flow with Backend

```
┌─────────────┐
│   Client    │
│  Apuntador  │
└──────┬──────┘
       │ 1. POST /api/oauth/authorize/googledrive
       │    { code_verifier: "..." }
       ▼
┌─────────────┐
│   Backend   │
│    OAuth    │
└──────┬──────┘
       │ 2. Returns authorization_url + signed state
       ▼
┌─────────────┐
│   Client    │  3. Opens browser with authorization_url
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Google    │  4. User authorizes
└──────┬──────┘
       │ 5. Redirect to backend/api/oauth/callback/googledrive?code=...
       ▼
┌─────────────┐
│   Backend   │  6. Redirect to apuntador://oauth-callback?code=...&state=...
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Client    │  7. POST /api/oauth/token/googledrive
│             │     { code: "...", code_verifier: "...", state: "..." }
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Backend   │  8. Returns access_token + refresh_token
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Client    │  9. Uses access_token for Google Drive API calls
└─────────────┘
```

## Required changes in the client

### 1. Configure backend URL

In `.env`:

```env
VITE_OAUTH_BACKEND_URL=http://localhost:8000
```

### 2. Create service to communicate with backend

Create `src/services/oauthBackend/backendOAuthService.ts`:

```typescript
import { Capacitor } from '@capacitor/core'
import { Browser } from '@capacitor/browser'
import axios from 'axios'

const BACKEND_URL = import.meta.env.VITE_OAUTH_BACKEND_URL || 'http://localhost:8000'

export interface BackendOAuthTokens {
  access_token: string
  refresh_token?: string
  expires_in: number
  token_type: string
}

export class BackendOAuthService {
  /**
   * Starts OAuth flow through the backend
   */
  async authorize(provider: 'googledrive' | 'dropbox', codeVerifier: string): Promise<string> {
    const response = await axios.post(`${BACKEND_URL}/api/oauth/authorize/${provider}`, {
      code_verifier: codeVerifier,
    })

    const { authorization_url, state } = response.data

    // Save code_verifier and state for callback
    localStorage.setItem(`${provider}_code_verifier`, codeVerifier)
    localStorage.setItem(`${provider}_state`, state)

    // Open browser
    if (Capacitor.isNativePlatform()) {
      await Browser.open({ url: authorization_url })
    } else {
      window.location.href = authorization_url
    }

    return state
  }

  /**
   * Exchanges code for tokens
   */
  async exchangeToken(
    provider: 'googledrive' | 'dropbox',
    code: string,
  ): Promise<BackendOAuthTokens> {
    const codeVerifier = localStorage.getItem(`${provider}_code_verifier`)
    const state = localStorage.getItem(`${provider}_state`)

    if (!codeVerifier) {
      throw new Error('Code verifier not found')
    }

    const response = await axios.post(`${BACKEND_URL}/api/oauth/token/${provider}`, {
      code,
      code_verifier: codeVerifier,
      state,
    })

    // Clean localStorage
    localStorage.removeItem(`${provider}_code_verifier`)
    localStorage.removeItem(`${provider}_state`)

    return response.data
  }

  /**
   * Refreshes access token
   */
  async refreshToken(
    provider: 'googledrive' | 'dropbox',
    refreshToken: string,
  ): Promise<BackendOAuthTokens> {
    const response = await axios.post(`${BACKEND_URL}/api/oauth/refresh/${provider}`, {
      refresh_token: refreshToken,
    })

    return response.data
  }

  /**
   * Revokes token
   */
  async revokeToken(provider: 'googledrive' | 'dropbox', token: string): Promise<void> {
    await axios.post(`${BACKEND_URL}/api/oauth/revoke/${provider}`, {
      token,
    })
  }
}
```

### 3. Modify Google Drive service

In `src/services/googledrive/googleDriveService.ts`:

```typescript
import { BackendOAuthService } from '@/services/oauthBackend/backendOAuthService'
import { generateCodeVerifier } from '@/utils/pkce'

export class GoogleDriveService implements CloudService {
  private backendOAuth = new BackendOAuthService()
  private accessToken: string | null = null

  async connect(): Promise<void> {
    // Generate code verifier
    const codeVerifier = generateCodeVerifier()

    // Start OAuth flow through backend
    await this.backendOAuth.authorize('googledrive', codeVerifier)
  }

  async handleOAuthCallback(code: string): Promise<void> {
    // Exchange code for tokens through backend
    const tokens = await this.backendOAuth.exchangeToken('googledrive', code)

    // Save tokens
    this.accessToken = tokens.access_token
    localStorage.setItem('googledrive_access_token', tokens.access_token)

    if (tokens.refresh_token) {
      localStorage.setItem('googledrive_refresh_token', tokens.refresh_token)
    }

    if (tokens.expires_in) {
      const expiresAt = Date.now() + tokens.expires_in * 1000
      localStorage.setItem('googledrive_token_expires_at', expiresAt.toString())
    }
  }

  // ... rest of methods to use Google Drive API
}
```

### 4. Update OAuth callback page

In `src/pages/OAuthCallback.vue`:

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCloudStore } from '@/stores/useCloudStore'

const route = useRoute()
const router = useRouter()
const cloudStore = useCloudStore()

onMounted(async () => {
  const { code, provider, error } = route.query

  if (error) {
    console.error('❌ OAuth error:', error)
    router.push('/settings')
    return
  }

  if (code && provider) {
    try {
      // Store handles code-to-token exchange
      await cloudStore.handleOAuthCallback(provider as string, code as string)
      router.push('/settings?oauth=success')
    } catch (err) {
      console.error('❌ Error handling OAuth callback:', err)
      router.push('/settings?oauth=error')
    }
  }
})
</script>
```

### 5. Configure deep links for Android

The deep link `apuntador://oauth-callback` already works, the backend will redirect there with the correct parameters.

## Advantages of this approach

✅ **Secure client secrets** - Never exposed in the client  
✅ **Unified code** - Same flow for web, Android, iOS, desktop  
✅ **Less complexity** - Backend handles differences between providers  
✅ **Automatic refresh** - Backend can manage token renewal  
✅ **Easier to maintain** - Changes in one place  

## Testing

1. **Backend**:
   ```bash
   cd apuntador-oauth-backend
   make dev
   # http://localhost:8000/docs
   ```

2. **Web client**:
   ```bash
   cd apuntador
   npm run dev
   # http://localhost:3000
   ```

3. **Test flow**:
   - Go to Settings → Cloud Storage
   - Click "Connect Google Drive"
   - Authorize in Google
   - Should redirect back with tokens

## Deployment

For production, deploy the backend on:
- **Railway**: Connect repo, configure .env, automatic deploy
- **Render**: Same process
- **Fly.io**: `fly deploy`
- **VPS**: Docker + nginx reverse proxy

And update in the client:
```env
VITE_OAUTH_BACKEND_URL=https://your-backend.railway.app
```

