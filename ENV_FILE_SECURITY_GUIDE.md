# Environment File Security Guide

## 🔒 Where to Store Your API Key (Safely)

### ✅ **Correct Location:**
```
deployment/docker/.env
```
**This file is gitignored** - Your API key will NOT be committed to GitHub.

### ❌ **Wrong Location:**
```
.env.example
```
**This file IS committed to GitHub** - Never put real API keys here!

---

## 📂 File Structure

```
Context/
│
├── .env.example                    ← Template (committed to GitHub)
│   └── GOOGLE_API_KEY=             ← Empty placeholder
│
├── .gitignore                      ← Contains: .env, .env.*
│
└── deployment/docker/
    └── .env                        ← Your actual secrets (gitignored)
        └── GOOGLE_API_KEY=AIza...  ← Your real API key goes here
```

---

## 🚀 Quick Setup

### Option 1: Automated (Recommended)
```powershell
.\scripts\setup_google_embeddings.ps1
```
The script will:
- Create `deployment/docker/.env` if it doesn't exist
- Add your API key securely
- Verify it's gitignored

### Option 2: Manual
```powershell
# 1. Create .env from template (if it doesn't exist)
Copy-Item ".env.example" "deployment/docker/.env"

# 2. Edit deployment/docker/.env and add:
EMBEDDINGS_PROVIDER=google
GOOGLE_API_KEY=AIza_your_actual_key_here
GOOGLE_EMBEDDING_MODEL=text-embedding-004
QDRANT_VECTOR_SIZE=768

# 3. Verify it's gitignored
git status
# Should NOT show deployment/docker/.env
```

---

## 🔍 Verify Security

Run the verification script:
```powershell
.\scripts\verify_env_security.ps1
```

This will check:
- ✅ `.gitignore` is properly configured
- ✅ `.env` files are not tracked by git
- ✅ `.env.example` is tracked (as a template)
- ✅ Your actual `.env` file exists
- ✅ Git status doesn't show `.env` files

---

## 🛡️ Security Best Practices

### ✅ **DO:**
1. Store API keys in `deployment/docker/.env`
2. Keep `.env.example` as a template with empty values
3. Add `.env` to `.gitignore` (already done)
4. Use environment variables for all secrets
5. Share `.env.example` with your team
6. Document required variables in `.env.example`

### ❌ **DON'T:**
1. Never commit `.env` files to git
2. Never put real API keys in `.env.example`
3. Never hardcode API keys in source code
4. Never share `.env` files publicly
5. Never commit files with `AIza...` or other API keys

---

## 🔧 Current Configuration

Your `.gitignore` already has:
```gitignore
.env
.env.*
!.env.example
```

This means:
- ✅ All `.env` files are ignored
- ✅ `.env.example` is tracked (template only)
- ✅ Your API keys are safe

---

## 🚨 If You Accidentally Committed Your API Key

### Step 1: Remove from Git History
```powershell
# Remove the file from git tracking
git rm --cached deployment/docker/.env

# Commit the removal
git commit -m "Remove .env from tracking"

# Push the change
git push
```

### Step 2: Rotate Your API Key
1. Go to: https://makersuite.google.com/app/apikey
2. Delete the old API key
3. Create a new API key
4. Update `deployment/docker/.env` with the new key

### Step 3: Verify
```powershell
.\scripts\verify_env_security.ps1
```

---

## 📋 Checklist

Before committing code:
- [ ] Verified `.env` is in `.gitignore`
- [ ] Ran `git status` - no `.env` files shown
- [ ] Only `.env.example` is tracked
- [ ] `.env.example` has no real API keys
- [ ] Actual API key is in `deployment/docker/.env`
- [ ] Ran `.\scripts\verify_env_security.ps1`

---

## 🎯 Summary

| File | Location | Committed? | Contains |
|------|----------|-----------|----------|
| `.env.example` | Root directory | ✅ Yes | Empty placeholders |
| `.env` | `deployment/docker/` | ❌ No | Your actual API key |

**Remember**: 
- `.env.example` = Template (safe to commit)
- `.env` = Secrets (never commit)

---

## 🆘 Need Help?

Run the verification script:
```powershell
.\scripts\verify_env_security.ps1
```

It will tell you exactly what's configured correctly and what needs fixing.

---

**Your API key is safe as long as it's in `deployment/docker/.env`** ✅

