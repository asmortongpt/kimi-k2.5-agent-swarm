#!/bin/bash
# ============================================================================
# Git Operations Library with Verification and Retry Logic
# ============================================================================
# This library provides robust git operations that follow security best practices:
# - No silent failures (no `|| true`)
# - Automatic retry logic with exponential backoff
# - Remote state verification after push
# - Proper error handling and logging
# - Conflict resolution support
# ============================================================================

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly MAX_RETRY_ATTEMPTS=3
readonly INITIAL_RETRY_DELAY=2

# ============================================================================
# Logging Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}ℹ️  $*${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $*${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $*${NC}"
}

log_error() {
    echo -e "${RED}❌ $*${NC}" >&2
}

# ============================================================================
# Git Operation Functions
# ============================================================================

# Retry a git operation with exponential backoff
# Usage: retry_git_operation "git push origin main"
retry_git_operation() {
    local operation="$1"
    local attempt=1

    while [ $attempt -le $MAX_RETRY_ATTEMPTS ]; do
        log_info "Attempt $attempt/$MAX_RETRY_ATTEMPTS: $operation"

        if eval "$operation"; then
            log_success "$operation successful"
            return 0
        else
            local exit_code=$?
            log_warning "Attempt $attempt failed with exit code $exit_code"

            if [ $attempt -lt $MAX_RETRY_ATTEMPTS ]; then
                local delay=$((INITIAL_RETRY_DELAY * attempt))
                log_info "Retrying in ${delay}s..."
                sleep "$delay"
            fi

            ((attempt++))
        fi
    done

    log_error "$operation failed after $MAX_RETRY_ATTEMPTS attempts"
    return 1
}

# Verify that local and remote commits match
# Usage: verify_remote_commit "main"
verify_remote_commit() {
    local branch="${1:-$(git rev-parse --abbrev-ref HEAD)}"

    log_info "Verifying remote commit for branch: $branch"

    # Fetch latest remote state
    git fetch origin "$branch" --quiet || {
        log_error "Failed to fetch remote branch: $branch"
        return 1
    }

    local local_commit
    local_commit=$(git rev-parse HEAD)
    local remote_commit
    remote_commit=$(git rev-parse "origin/$branch")

    if [ "$local_commit" = "$remote_commit" ]; then
        log_success "Push verified - commits match"
        log_info "Commit: $local_commit"
        return 0
    else
        log_error "Local and remote commits differ"
        log_error "Local:  $local_commit"
        log_error "Remote: $remote_commit"
        return 1
    fi
}

# Safe git push with retry and verification
# Usage: safe_git_push "main" "optional commit message"
safe_git_push() {
    local branch="${1:-$(git rev-parse --abbrev-ref HEAD)}"
    local commit_message="${2:-}"

    log_info "Starting safe git push for branch: $branch"

    # Check if there are changes to commit
    if [ -n "$commit_message" ]; then
        if git diff --quiet && git diff --staged --quiet; then
            log_info "No changes to commit"
            return 0
        fi

        # Stage all changes
        git add -A

        # Commit if there are staged changes
        if ! git diff --staged --quiet; then
            if ! git commit -m "$commit_message"; then
                log_error "Failed to commit changes"
                return 1
            fi
            log_success "Changes committed: $commit_message"
        else
            log_info "No staged changes to commit"
            return 0
        fi
    fi

    # Attempt to push with retry logic
    if retry_git_operation "git push origin $branch"; then
        # Verify the push was successful
        if verify_remote_commit "$branch"; then
            log_success "Push completed and verified successfully"
            return 0
        else
            log_error "Push completed but verification failed"
            return 1
        fi
    else
        log_error "Push failed after all retry attempts"
        return 1
    fi
}

# Safe git push with automatic conflict resolution
# Usage: safe_git_push_with_pull "main" "commit message"
safe_git_push_with_pull() {
    local branch="${1:-$(git rev-parse --abbrev-ref HEAD)}"
    local commit_message="${2:-}"
    local attempt=1

    log_info "Starting safe git push with auto-pull for branch: $branch"

    # Check if there are changes to commit
    if [ -n "$commit_message" ]; then
        if git diff --quiet && git diff --staged --quiet; then
            log_info "No changes to commit"
            return 0
        fi

        # Stage all changes
        git add -A

        # Commit if there are staged changes
        if ! git diff --staged --quiet; then
            if ! git commit -m "$commit_message"; then
                log_error "Failed to commit changes"
                return 1
            fi
            log_success "Changes committed: $commit_message"
        else
            log_info "No staged changes to commit"
            return 0
        fi
    fi

    # Attempt to push with automatic pull and retry
    while [ $attempt -le $MAX_RETRY_ATTEMPTS ]; do
        log_info "Push attempt $attempt/$MAX_RETRY_ATTEMPTS"

        if git push origin "$branch"; then
            # Verify the push
            if verify_remote_commit "$branch"; then
                log_success "Push completed and verified successfully"
                return 0
            else
                log_error "Push completed but verification failed"
                return 1
            fi
        else
            log_warning "Push failed, attempting to pull and rebase"

            if [ $attempt -lt $MAX_RETRY_ATTEMPTS ]; then
                # Pull with rebase to resolve conflicts
                if git pull --rebase origin "$branch"; then
                    log_success "Pulled and rebased successfully"
                else
                    log_error "Pull and rebase failed - manual intervention required"
                    log_error "Run: git rebase --abort && git pull origin $branch"
                    return 1
                fi

                local delay=$((INITIAL_RETRY_DELAY * attempt))
                log_info "Retrying push in ${delay}s..."
                sleep "$delay"
            fi

            ((attempt++))
        fi
    done

    log_error "Push failed after $MAX_RETRY_ATTEMPTS attempts"
    return 1
}

# Pull latest changes with verification
# Usage: safe_git_pull "main"
safe_git_pull() {
    local branch="${1:-$(git rev-parse --abbrev-ref HEAD)}"

    log_info "Pulling latest changes for branch: $branch"

    # Fetch first to check for changes
    if ! git fetch origin "$branch"; then
        log_error "Failed to fetch from remote"
        return 1
    fi

    local local_commit
    local_commit=$(git rev-parse HEAD)
    local remote_commit
    remote_commit=$(git rev-parse "origin/$branch")

    if [ "$local_commit" = "$remote_commit" ]; then
        log_info "Already up to date"
        return 0
    fi

    # Pull with retry
    if retry_git_operation "git pull origin $branch"; then
        log_success "Pull completed successfully"
        return 0
    else
        log_error "Pull failed"
        return 1
    fi
}

# Check if working directory is clean
# Usage: ensure_clean_working_directory
ensure_clean_working_directory() {
    if ! git diff --quiet || ! git diff --staged --quiet; then
        log_error "Working directory is not clean"
        log_error "Please commit or stash your changes before proceeding"
        git status --short
        return 1
    fi

    log_success "Working directory is clean"
    return 0
}

# Get current branch name
# Usage: branch=$(get_current_branch)
get_current_branch() {
    git rev-parse --abbrev-ref HEAD
}

# Check if branch exists on remote
# Usage: remote_branch_exists "main"
remote_branch_exists() {
    local branch="$1"

    git ls-remote --heads origin "$branch" | grep -q "$branch"
}

# ============================================================================
# Export functions for use in other scripts
# ============================================================================

export -f log_info
export -f log_success
export -f log_warning
export -f log_error
export -f retry_git_operation
export -f verify_remote_commit
export -f safe_git_push
export -f safe_git_push_with_pull
export -f safe_git_pull
export -f ensure_clean_working_directory
export -f get_current_branch
export -f remote_branch_exists

log_success "Git operations library loaded"
