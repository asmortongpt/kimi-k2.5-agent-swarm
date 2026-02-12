# Git Operations Guide

## Overview

This guide documents the safe git operations library that provides robust git commands with retry logic, verification, and proper error handling. This addresses **High Priority Issue #7: Git Operations Without Verification**.

## Problem Statement

Traditional git operations in scripts often use patterns like:

```bash
git push || true  # ❌ BAD: Silently ignores failures
```

This creates several critical issues:

1. **Silent failures**: Errors are hidden, leading to incomplete deployments
2. **No verification**: No confirmation that remote state matches local
3. **No retry logic**: Transient network issues cause permanent failures
4. **Poor error handling**: Difficult to debug when things go wrong

## Solution

The `scripts/lib/git-operations.sh` library provides:

- ✅ **No silent failures**: All errors are caught and reported
- ✅ **Automatic retry logic**: Configurable retries with exponential backoff
- ✅ **Remote verification**: Confirms remote state after operations
- ✅ **Conflict resolution**: Automatic pull/rebase on push conflicts
- ✅ **Comprehensive logging**: Color-coded output for easy debugging

## Installation

### 1. Copy the Library

```bash
# Create lib directory
mkdir -p scripts/lib

# Copy the library
cp scripts/lib/git-operations.sh /path/to/your/project/scripts/lib/
```

### 2. Make Executable

```bash
chmod +x scripts/lib/git-operations.sh
```

## Usage

### Basic Usage

```bash
#!/bin/bash
set -euo pipefail

# Source the library
source "$(dirname "$0")/lib/git-operations.sh"

# Now you can use all the functions
safe_git_push "main" "Deploy to production"
```

### Available Functions

#### 1. `safe_git_push`

Safe git push with retry and verification.

```bash
safe_git_push "branch-name" "optional commit message"
```

**Example:**

```bash
# Push existing commits
safe_git_push "main"

# Commit changes and push
safe_git_push "main" "fix: Update deployment script"
```

**Features:**
- Commits changes if message provided
- Retries push up to 3 times
- Verifies remote commit after push
- Returns 0 on success, 1 on failure

#### 2. `safe_git_push_with_pull`

Safe git push with automatic pull/rebase on conflicts.

```bash
safe_git_push_with_pull "branch-name" "optional commit message"
```

**Example:**

```bash
safe_git_push_with_pull "feature/new-feature" "feat: Add new feature"
```

**Features:**
- All features of `safe_git_push`
- Automatically pulls and rebases on push conflicts
- Retries after successful rebase
- Ideal for CI/CD environments

#### 3. `safe_git_pull`

Safe git pull with verification.

```bash
safe_git_pull "branch-name"
```

**Example:**

```bash
safe_git_pull "main"
```

**Features:**
- Fetches first to check for changes
- Shows if already up to date
- Retries on transient failures

#### 4. `verify_remote_commit`

Verify local and remote commits match.

```bash
verify_remote_commit "branch-name"
```

**Example:**

```bash
if verify_remote_commit "main"; then
    log_success "Commits match"
else
    log_error "Commits differ"
fi
```

#### 5. `retry_git_operation`

Retry any git operation with exponential backoff.

```bash
retry_git_operation "git command"
```

**Example:**

```bash
retry_git_operation "git fetch origin main"
```

#### 6. Utility Functions

```bash
# Get current branch
branch=$(get_current_branch)

# Check if working directory is clean
ensure_clean_working_directory

# Check if remote branch exists
remote_branch_exists "branch-name"
```

#### 7. Logging Functions

```bash
log_info "Information message"
log_success "Success message"
log_warning "Warning message"
log_error "Error message"
```

## Complete Examples

### Example 1: Simple Deployment Script

```bash
#!/bin/bash
set -euo pipefail

# Load library
source "$(dirname "$0")/lib/git-operations.sh"

BRANCH="main"

# Pull latest
log_info "Pulling latest changes..."
safe_git_pull "$BRANCH"

# Run tests
log_info "Running tests..."
npm test || {
    log_error "Tests failed"
    exit 1
}

# Build
log_info "Building..."
npm run build || {
    log_error "Build failed"
    exit 1
}

# Commit and push
log_info "Deploying..."
safe_git_push_with_pull "$BRANCH" "deploy: Production deployment $(date -u +"%Y-%m-%d")"

log_success "Deployment completed!"
```

### Example 2: CI/CD Pipeline

```bash
#!/bin/bash
set -euo pipefail

source "$(dirname "$0")/lib/git-operations.sh"

BRANCH=$(get_current_branch)

# Ensure clean state
if ! ensure_clean_working_directory; then
    log_error "Working directory is dirty"
    exit 1
fi

# Pull latest
safe_git_pull "$BRANCH"

# Run linting
npm run lint || exit 1

# Run tests
npm test || exit 1

# Build
npm run build || exit 1

# Add build artifacts
git add dist/
git commit -m "build: Add build artifacts [skip ci]" || true

# Push with verification
safe_git_push_with_pull "$BRANCH"

# Verify deployment
verify_remote_commit "$BRANCH" || exit 1

log_success "CI/CD pipeline completed successfully"
```

### Example 3: Azure Deployment

See `scripts/azure-agent-deployment.sh` for a complete Azure deployment example.

## GitHub Actions Integration

### Example Workflow

```yaml
name: Safe Deployment

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Configure Git
        run: |
          git config --global user.name "GitHub Actions"
          git config --global user.email "actions@github.com"

      - name: Deploy with safe git operations
        run: |
          source scripts/lib/git-operations.sh
          BRANCH=$(get_current_branch)
          safe_git_push_with_pull "$BRANCH"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

See `.github/workflows/safe-deployment.yml` for a complete example.

## Configuration

### Retry Settings

Edit these constants in `git-operations.sh`:

```bash
readonly MAX_RETRY_ATTEMPTS=3      # Number of retry attempts
readonly INITIAL_RETRY_DELAY=2     # Initial delay in seconds
```

### Exponential Backoff

The retry delay increases with each attempt:
- Attempt 1: 2 seconds
- Attempt 2: 4 seconds
- Attempt 3: 6 seconds

## Testing

### Run Test Suite

```bash
# Run all tests
./scripts/test-git-operations.sh

# Run in CI mode (skips push/pull tests)
CI=1 ./scripts/test-git-operations.sh
```

### Test Cases

The test suite includes:

1. ✅ Get current branch
2. ✅ Ensure clean working directory
3. ✅ Safe git push
4. ✅ Safe git pull
5. ✅ Retry mechanism
6. ✅ Conflict resolution

### Manual Testing with Conflicts

```bash
# Terminal 1: Create a test branch
git checkout -b test/conflict
echo "version 1" > test.txt
git add test.txt
git commit -m "test: Initial commit"
git push -u origin test/conflict

# Terminal 2: Make conflicting changes
git checkout test/conflict
git pull
echo "version 2 - remote" > test.txt
git add test.txt
git commit -m "test: Remote change"
git push

# Terminal 1: Make local changes and test
echo "version 2 - local" > test.txt
git add test.txt
git commit -m "test: Local change"

# Use safe push with pull (should auto-resolve)
source scripts/lib/git-operations.sh
safe_git_push_with_pull test/conflict
```

## Best Practices

### 1. Always Source the Library

```bash
# ✅ Good
source "$(dirname "$0")/lib/git-operations.sh"

# ❌ Bad
./scripts/lib/git-operations.sh  # Won't work - functions won't be available
```

### 2. Use `set -euo pipefail`

```bash
#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures
```

### 3. Check Return Codes

```bash
# ✅ Good
if safe_git_push "main"; then
    log_success "Push successful"
else
    log_error "Push failed"
    exit 1
fi

# ❌ Bad
safe_git_push "main"  # Doesn't check if it succeeded
```

### 4. Use Appropriate Push Function

```bash
# For simple pushes (no conflicts expected)
safe_git_push "main"

# For CI/CD or multi-developer environments
safe_git_push_with_pull "main"
```

### 5. Always Verify After Critical Operations

```bash
safe_git_push "main"
verify_remote_commit "main" || exit 1
```

## Troubleshooting

### Issue: Push fails with "rejected"

**Cause:** Remote has changes you don't have locally.

**Solution:** Use `safe_git_push_with_pull` instead:

```bash
safe_git_push_with_pull "main"
```

### Issue: Verification fails

**Cause:** Remote and local commits don't match.

**Solution:**

```bash
# Check status
git status
git log -1
git log origin/main -1

# Pull latest
safe_git_pull "main"

# Try push again
safe_git_push "main"
```

### Issue: Working directory not clean

**Cause:** Uncommitted changes.

**Solution:**

```bash
# Check what's changed
git status

# Commit or stash
git stash
# or
git add -A && git commit -m "WIP"
```

### Issue: All retries fail

**Cause:** Network issues or invalid credentials.

**Solution:**

```bash
# Test network connectivity
curl -I https://github.com

# Verify credentials
git fetch origin

# Check remote URL
git remote -v
```

## Migration Guide

### Migrating from Unsafe Scripts

**Before:**

```bash
#!/bin/bash
git pull origin main || true
git add -A
git commit -m "Deploy" || true
git push origin main || true
```

**After:**

```bash
#!/bin/bash
set -euo pipefail

source "$(dirname "$0")/lib/git-operations.sh"

safe_git_pull "main"
safe_git_push_with_pull "main" "Deploy"
```

### Migrating CI/CD Pipelines

**Before:**

```yaml
- name: Deploy
  run: |
    git config user.name "Bot"
    git config user.email "bot@example.com"
    git add .
    git commit -m "Deploy" || true
    git push || true
```

**After:**

```yaml
- name: Deploy
  run: |
    git config user.name "Bot"
    git config user.email "bot@example.com"
    source scripts/lib/git-operations.sh
    safe_git_push_with_pull "main" "Deploy"
```

## Security Considerations

### 1. Never Hardcode Credentials

```bash
# ❌ Bad
git clone https://user:password@github.com/repo.git

# ✅ Good
git clone https://github.com/repo.git  # Use SSH or token via env
```

### 2. Validate Branch Names

```bash
# ✅ Good
BRANCH="${1:-main}"
if [[ ! "$BRANCH" =~ ^[a-zA-Z0-9/_-]+$ ]]; then
    log_error "Invalid branch name"
    exit 1
fi
```

### 3. Use Signed Commits in Production

```bash
git config --global commit.gpgsign true
git config --global user.signingkey YOUR_KEY
```

## Performance

### Benchmarks

Typical operation times (on good network):

- `safe_git_push`: 2-5 seconds
- `safe_git_pull`: 1-3 seconds
- `verify_remote_commit`: 1-2 seconds
- `safe_git_push_with_pull`: 3-8 seconds (with conflicts)

### Optimization Tips

1. **Use shallow clones in CI:**

   ```bash
   git clone --depth=1 https://github.com/repo.git
   ```

2. **Cache dependencies:**

   ```bash
   # In GitHub Actions
   - uses: actions/cache@v4
   ```

3. **Parallel operations:**

   ```bash
   npm test &
   npm run lint &
   wait
   ```

## Contributing

To contribute improvements:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run the test suite
5. Submit a pull request

## License

This library is part of the CTAFleet project and follows the same license.

## Support

For issues or questions:

1. Check this documentation
2. Review the test suite examples
3. Check GitHub Issues
4. Contact the development team

## Changelog

### Version 1.0.0 (2026-02-08)

- ✅ Initial release
- ✅ Safe push/pull operations
- ✅ Retry logic with exponential backoff
- ✅ Remote verification
- ✅ Conflict resolution
- ✅ Comprehensive test suite
- ✅ GitHub Actions integration
- ✅ Full documentation

---

**Last Updated:** 2026-02-08
**Author:** CTAFleet Development Team
**Issue:** High Priority Issue #7: Git Operations Without Verification
