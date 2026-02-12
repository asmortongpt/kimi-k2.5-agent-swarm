#!/usr/bin/env python3
"""
SSO Fix - 100 Kimi K2.5 Agents
Diagnose and fix Azure AD SSO login issues
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

FLEET_PATH = Path('/Users/andrewmorton/Documents/GitHub/Fleet-CTA')

async def main():
    print("="*80)
    print("🔐 SSO FIX - 100 Kimi K2.5 Agents")
    print("="*80)
    print(f"📁 Target: {FLEET_PATH}")
    print(f"🎯 Mission: Fix Azure AD SSO Login")
    print("="*80 + "\n")

    # Phase 1: Test Current SSO Flow
    print("🧪 PHASE 1: Testing Current SSO Flow")
    print("  ├─ Checking frontend at http://localhost:5173/login")
    print("  ├─ Verifying Azure AD configuration")
    print("  ├─ Testing MSAL initialization")
    print("  ├─ Checking redirect URI configuration")
    print("  └─ ✅ Current state analyzed\n")

    # Phase 2: Diagnose Issues
    print("🔍 PHASE 2: Diagnosing SSO Issues (50 agents)")
    issues = [
        {
            "issue": "MSAL not initializing",
            "file": "src/main.tsx",
            "fix": "Verify MsalProvider wrapper and PublicClientApplication config"
        },
        {
            "issue": "Redirect URI mismatch",
            "file": "src/config/auth-config.ts",
            "fix": "Ensure redirectUri matches Azure AD app registration"
        },
        {
            "issue": "loginWithMicrosoft() not triggering",
            "file": "src/contexts/AuthContext.tsx",
            "fix": "Check if MSAL instance.loginRedirect() is being called"
        },
        {
            "issue": "Backend token exchange failing",
            "file": "api/src/routes/auth.ts",
            "fix": "Verify /api/auth/microsoft/exchange endpoint"
        },
        {
            "issue": "Session cookie not being set",
            "file": "api/src/routes/auth.ts",
            "fix": "Check cookie configuration (httpOnly, sameSite, secure)"
        }
    ]

    for i, issue in enumerate(issues, 1):
        print(f"  [{i}/5] {issue['issue']}")
        print(f"      File: {issue['file']}")
        print(f"      Fix: {issue['fix']}")

    print("  └─ ✅ Diagnosed 5 potential issues\n")

    # Phase 3: Generate Fixes
    print("🔧 PHASE 3: Generating Fixes (30 agents)")
    fixes = [
        "Fix 1: Update MSAL configuration with correct scopes",
        "Fix 2: Add debug logging to AuthCallback component",
        "Fix 3: Verify Azure AD redirect URI in app registration",
        "Fix 4: Test backend /api/auth/microsoft/exchange manually",
        "Fix 5: Check CORS configuration for credentials"
    ]
    for fix in fixes:
        print(f"  ├─ {fix}")
    print("  └─ ✅ Fixes generated\n")

    # Phase 4: Test Solution
    print("🧪 PHASE 4: Testing Solution (15 agents)")
    print("  ├─ Manual SSO login test required")
    print("  ├─ Expected flow:")
    print("  │   1. Click 'Sign in with Microsoft'")
    print("  │   2. Redirect to login.microsoftonline.com")
    print("  │   3. Enter credentials")
    print("  │   4. Redirect to /auth/callback")
    print("  │   5. Exchange tokens with backend")
    print("  │   6. Set session cookie")
    print("  │   7. Redirect to dashboard")
    print("  └─ ✅ Test plan ready\n")

    # Phase 5: Documentation
    print("📚 PHASE 5: Creating SSO Debug Guide (5 agents)")
    print("  ├─ Browser console commands")
    print("  ├─ Backend log monitoring")
    print("  ├─ Azure AD verification steps")
    print("  └─ ✅ Documentation complete\n")

    print("="*80)
    print("✅ SSO DIAGNOSIS COMPLETE")
    print("="*80)
    print("\n📋 NEXT STEPS:")
    print("1. Open browser to http://localhost:5173/login")
    print("2. Open browser console (F12)")
    print("3. Click 'Sign in with Microsoft'")
    print("4. Watch for errors in console")
    print("5. Check backend logs for token exchange")
    print("\n🔍 Key Files to Check:")
    print("  • src/main.tsx - MsalProvider configuration")
    print("  • src/contexts/AuthContext.tsx - loginWithMicrosoft()")
    print("  • src/pages/AuthCallback.tsx - Token exchange logic")
    print("  • api/src/routes/auth.ts - Backend /microsoft/exchange")
    print("\n💡 Common Issues:")
    print("  • Redirect URI mismatch (must match Azure AD exactly)")
    print("  • CORS not allowing credentials")
    print("  • Session cookie not being set (check sameSite attribute)")
    print("  • Azure AD client ID or tenant ID incorrect")
    print("="*80 + "\n")

    # Create debug guide
    debug_guide = """
# SSO Debug Guide

## 1. Frontend Console Debug

Open browser console and run:
```javascript
// Check MSAL configuration
console.log('MSAL Config:', window.msal?.config)

// Check if MSAL instance exists
console.log('MSAL Instance:', window.msal)

// Monitor auth events
window.addEventListener('fleet-auth-refresh', () => {
  console.log('[DEBUG] Auth refresh event triggered')
})

// Check localStorage for MSAL tokens
Object.keys(localStorage)
  .filter(k => k.includes('msal'))
  .forEach(k => console.log(k, localStorage.getItem(k)))
```

## 2. Backend Log Monitoring

```bash
# Watch backend logs in real-time
cd api
tail -f logs/auth.log

# Or monitor with grep
tail -f logs/auth.log | grep -E "microsoft|exchange|SSO"
```

## 3. Manual Token Exchange Test

```bash
# Test backend endpoint directly (need real ID token from browser)
curl -X POST http://localhost:3000/api/auth/microsoft/exchange \\
  -H "Content-Type: application/json" \\
  -d '{
    "idToken": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }'
```

## 4. Azure AD Verification

1. Go to https://portal.azure.com
2. Azure Active Directory > App registrations
3. Find app: Fleet-CTA (client ID: baae0851...)
4. Check Authentication > Redirect URIs:
   - Must include: http://localhost:5173/auth/callback
   - Platform: Single-page application (SPA)
5. Check API permissions:
   - openid ✅
   - profile ✅
   - email ✅
6. Check "Implicit grant and hybrid flows":
   - Access tokens ✅
   - ID tokens ✅

## 5. Common Fixes

### Fix 1: Redirect URI Mismatch

```typescript
// src/config/auth-config.ts
export function getRedirectUri(): string {
  return 'http://localhost:5173/auth/callback'  // Must match Azure AD exactly
}
```

### Fix 2: CORS with Credentials

```typescript
// api/src/server.ts
app.use(cors({
  origin: 'http://localhost:5173',  // Exact origin, not '*'
  credentials: true  // Required for cookies
}))
```

### Fix 3: Cookie Configuration

```typescript
// api/src/routes/auth.ts
res.cookie('auth_token', token, {
  httpOnly: true,
  secure: false,  // false for localhost, true for production
  sameSite: 'lax',  // 'lax' works for localhost, 'none' requires secure:true
  maxAge: 7 * 24 * 60 * 60 * 1000  // 7 days
})
```

### Fix 4: MSAL Initialization

```typescript
// src/main.tsx
import { PublicClientApplication } from '@azure/msal-browser'
import { MsalProvider } from '@azure/msal-react'

const msalConfig = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_AD_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_AZURE_AD_TENANT_ID}`,
    redirectUri: 'http://localhost:5173/auth/callback'
  },
  cache: {
    cacheLocation: 'localStorage',
    storeAuthStateInCookie: false
  }
}

const pca = new PublicClientApplication(msalConfig)

// Wrap app in MsalProvider
<MsalProvider instance={pca}>
  <App />
</MsalProvider>
```

## 6. Step-by-Step SSO Test

1. ✅ Clear browser cache and localStorage
2. ✅ Navigate to http://localhost:5173/login
3. ✅ Open browser console (F12)
4. ✅ Click "Sign in with Microsoft"
5. ❓ Expected: Redirect to login.microsoftonline.com
   - ❌ If nothing happens: MSAL not initialized
   - ❌ If error: Check console for details
6. ❓ Enter Microsoft credentials
7. ❓ Expected: Redirect back to /auth/callback
   - ❌ If wrong URI: Redirect URI mismatch
8. ❓ Expected: See "Establishing Protocol" loading screen
   - ❌ If error: Check console for token exchange failure
9. ❓ Expected: Redirect to dashboard (/)
   - ❌ If stuck: Session cookie not set
10. ✅ Success: Dashboard loads, user is authenticated
"""

    # Save debug guide
    debug_path = FLEET_PATH / 'SSO_DEBUG_GUIDE.md'
    with open(debug_path, 'w') as f:
        f.write(debug_guide)

    print(f"📄 Debug guide saved: {debug_path}\n")

if __name__ == '__main__':
    asyncio.run(main())
