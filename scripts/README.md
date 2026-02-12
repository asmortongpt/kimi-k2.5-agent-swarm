# Scripts Directory

This directory contains utility scripts for the Kimi K2.5 Agent Swarm project, including robust git operations and deployment automation.

## High Priority Fix: Issue #7

This implementation addresses **High Priority Issue #7: Git Operations Without Verification**.

### What Was Fixed

**Before:**
- Git commands used `|| true` to silence errors
- No verification of remote state after push
- No retry logic for transient failures
- Difficult to debug deployment issues

**After:**
- ✅ Proper error handling (no silent failures)
- ✅ Automatic retry with exponential backoff
- ✅ Remote state verification after every push
- ✅ Conflict resolution with automatic pull/rebase
- ✅ Comprehensive logging for debugging

## Directory Structure

```
scripts/
├── README.md                      # This file
├── lib/
│   └── git-operations.sh          # Reusable git operations library
├── azure-agent-deployment.sh      # Azure deployment script
├── test-git-operations.sh         # Test suite for git operations
└── quickstart.sh                  # Quick start script
```

## Quick Start

### 1. Use Git Operations in Your Script

```bash
#!/bin/bash
set -euo pipefail

# Load the library
source "$(dirname "$0")/lib/git-operations.sh"

# Use safe git operations
safe_git_pull "main"
safe_git_push_with_pull "main" "Deploy to production"
```

### 2. Run Deployment Script

```bash
# Deploy to Azure
./scripts/azure-agent-deployment.sh

# With environment variables
DEPLOYMENT_ENV=staging GIT_BRANCH=main ./scripts/azure-agent-deployment.sh
```

### 3. Run Tests

```bash
# Run test suite
./scripts/test-git-operations.sh

# Run in CI mode (skips push/pull tests)
CI=1 ./scripts/test-git-operations.sh
```

## Available Scripts

### `lib/git-operations.sh`

**Purpose:** Reusable library for safe git operations

**Key Functions:**
- `safe_git_push` - Push with verification
- `safe_git_push_with_pull` - Push with automatic conflict resolution
- `safe_git_pull` - Pull with retry logic
- `verify_remote_commit` - Verify local/remote match
- `retry_git_operation` - Retry any git command

**Usage:**
```bash
source scripts/lib/git-operations.sh
safe_git_push "main" "Deploy"
```

**Documentation:** See [docs/GIT_OPERATIONS_GUIDE.md](../docs/GIT_OPERATIONS_GUIDE.md)

### `azure-agent-deployment.sh`

**Purpose:** Automated Azure deployment with safe git operations

**Features:**
- Prerequisites checking
- Automated testing before deployment
- Safe git push with verification
- Azure-specific deployment steps
- Comprehensive error handling

**Usage:**
```bash
# Standard deployment
./scripts/azure-agent-deployment.sh

# Custom environment
DEPLOYMENT_ENV=production GIT_BRANCH=main ./scripts/azure-agent-deployment.sh
```

**Environment Variables:**
- `GIT_BRANCH` - Target branch (default: feature/feb-2026-enterprise-enhancements)
- `DEPLOYMENT_ENV` - Environment (default: production)
- `AZURE_RESOURCE_GROUP` - Azure resource group (default: CTAFleet-RG)

### `test-git-operations.sh`

**Purpose:** Test suite for git operations library

**Features:**
- Tests all library functions
- Simulates conflicts and retries
- CI-friendly (skips remote operations in CI)
- Automatic cleanup

**Usage:**
```bash
# Run full test suite
./scripts/test-git-operations.sh

# Run in CI mode
CI=1 ./scripts/test-git-operations.sh
```

**Test Cases:**
- ✅ Get current branch
- ✅ Ensure clean working directory
- ✅ Safe git push (local only)
- ✅ Safe git pull (local only)
- ✅ Retry mechanism
- ✅ Conflict resolution (local only)

### `quickstart.sh`

**Purpose:** Quick start script for Kimi K2.5 setup

**Features:**
- Docker environment setup
- Model installation
- Database migrations
- Health checks

**Usage:**
```bash
./scripts/quickstart.sh
```

## Configuration

### Retry Settings

Edit `lib/git-operations.sh` to configure retry behavior:

```bash
readonly MAX_RETRY_ATTEMPTS=3      # Number of retries
readonly INITIAL_RETRY_DELAY=2     # Initial delay (seconds)
```

Delay increases with each attempt (exponential backoff):
- Attempt 1: 2 seconds
- Attempt 2: 4 seconds
- Attempt 3: 6 seconds

### Logging

The library provides color-coded logging:

```bash
log_info "Information message"      # Blue
log_success "Success message"       # Green
log_warning "Warning message"       # Yellow
log_error "Error message"           # Red
```

## Integration Examples

### GitHub Actions

```yaml
- name: Deploy with safe git operations
  run: |
    source scripts/lib/git-operations.sh
    safe_git_push_with_pull "main" "Deploy"
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

See [.github/workflows/safe-deployment.yml](../.github/workflows/safe-deployment.yml) for complete example.

### CI/CD Pipeline

```bash
#!/bin/bash
set -euo pipefail

source scripts/lib/git-operations.sh

# Pull latest
safe_git_pull "main"

# Run tests
npm test || exit 1

# Build
npm run build || exit 1

# Deploy
safe_git_push_with_pull "main" "Automated deployment"

# Verify
verify_remote_commit "main" || exit 1
```

### Local Development

```bash
#!/bin/bash
source scripts/lib/git-operations.sh

# Check if working directory is clean
ensure_clean_working_directory || {
    log_error "Please commit your changes first"
    exit 1
}

# Pull latest
safe_git_pull "main"

# Do your work...
```

## Best Practices

### 1. Always Use `set -euo pipefail`

```bash
#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures
```

### 2. Source the Library Correctly

```bash
# ✅ Good - works from any directory
source "$(dirname "$0")/lib/git-operations.sh"

# ❌ Bad - only works if run from specific directory
source lib/git-operations.sh
```

### 3. Check Return Codes

```bash
# ✅ Good
if safe_git_push "main"; then
    log_success "Success"
else
    log_error "Failed"
    exit 1
fi

# ❌ Bad
safe_git_push "main"  # No error handling
```

### 4. Use Appropriate Push Function

```bash
# For simple pushes (single developer)
safe_git_push "main"

# For CI/CD or teams (handles conflicts)
safe_git_push_with_pull "main"
```

### 5. Always Verify Critical Operations

```bash
safe_git_push "main"
verify_remote_commit "main" || exit 1
```

## Troubleshooting

### Issue: "git-operations.sh library not found"

**Solution:**
```bash
# Check path
ls scripts/lib/git-operations.sh

# Make executable
chmod +x scripts/lib/git-operations.sh

# Use correct path in your script
source "$(dirname "$0")/lib/git-operations.sh"
```

### Issue: Push fails with "rejected"

**Solution:** Use `safe_git_push_with_pull` which automatically handles conflicts:
```bash
safe_git_push_with_pull "main"
```

### Issue: Tests fail in CI

**Solution:** Use CI mode to skip remote operations:
```bash
CI=1 ./scripts/test-git-operations.sh
```

### Issue: "Working directory is not clean"

**Solution:**
```bash
# See what's changed
git status

# Commit or stash
git stash
# or
git add -A && git commit -m "WIP"
```

## Security

### Never Hardcode Credentials

```bash
# ❌ Bad
git clone https://user:password@github.com/repo.git

# ✅ Good
git clone https://github.com/repo.git
# Use SSH keys or tokens via environment variables
```

### Validate User Input

```bash
BRANCH="${1:-main}"
if [[ ! "$BRANCH" =~ ^[a-zA-Z0-9/_-]+$ ]]; then
    log_error "Invalid branch name"
    exit 1
fi
```

### Use Signed Commits in Production

```bash
git config --global commit.gpgsign true
git config --global user.signingkey YOUR_GPG_KEY
```

## Documentation

- **Full Guide:** [docs/GIT_OPERATIONS_GUIDE.md](../docs/GIT_OPERATIONS_GUIDE.md)
- **GitHub Actions:** [.github/workflows/safe-deployment.yml](../.github/workflows/safe-deployment.yml)
- **Issue Tracking:** High Priority Issue #7

## Support

For issues or questions:

1. Check the [full documentation](../docs/GIT_OPERATIONS_GUIDE.md)
2. Review test suite examples
3. Check GitHub Issues
4. Contact the development team

## Changelog

### 2026-02-08 - v1.0.0

- ✅ Initial release addressing Issue #7
- ✅ Safe git operations library
- ✅ Azure deployment script
- ✅ Comprehensive test suite
- ✅ Full documentation
- ✅ GitHub Actions integration

---

**Last Updated:** 2026-02-08
**Maintainer:** CTAFleet Development Team
**Issue:** High Priority Issue #7: Git Operations Without Verification
