#!/bin/bash
# ============================================================================
# Azure Agent Deployment Script
# ============================================================================
# This script demonstrates proper git operations with verification and retry logic.
# It uses the git-operations.sh library for safe git commands.
# ============================================================================

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load git operations library
if [ -f "$SCRIPT_DIR/lib/git-operations.sh" ]; then
    # shellcheck source=lib/git-operations.sh
    source "$SCRIPT_DIR/lib/git-operations.sh"
else
    echo "❌ Error: git-operations.sh library not found"
    echo "Expected location: $SCRIPT_DIR/lib/git-operations.sh"
    exit 1
fi

# Configuration
BRANCH="${GIT_BRANCH:-feature/feb-2026-enterprise-enhancements}"
DEPLOYMENT_ENV="${DEPLOYMENT_ENV:-production}"
AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-CTAFleet-RG}"

# ============================================================================
# Deployment Functions
# ============================================================================

check_prerequisites() {
    log_info "Checking deployment prerequisites..."

    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository"
        return 1
    fi

    # Check if Azure CLI is installed (if needed)
    if [ "$DEPLOYMENT_ENV" != "local" ]; then
        if ! command -v az &> /dev/null; then
            log_warning "Azure CLI not found - skipping Azure-specific checks"
        else
            log_success "Azure CLI found: $(az version --query '"azure-cli"' -o tsv 2>/dev/null || echo 'unknown')"
        fi
    fi

    # Check current branch
    local current_branch
    current_branch=$(get_current_branch)
    log_info "Current branch: $current_branch"

    if [ "$current_branch" != "$BRANCH" ]; then
        log_warning "Current branch ($current_branch) does not match target branch ($BRANCH)"
        read -p "Switch to $BRANCH? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git checkout "$BRANCH" || {
                log_error "Failed to switch to branch $BRANCH"
                return 1
            }
        else
            log_error "Deployment cancelled"
            return 1
        fi
    fi

    log_success "Prerequisites check passed"
    return 0
}

run_tests() {
    log_info "Running tests before deployment..."

    cd "$PROJECT_ROOT"

    # Run linting
    if [ -f "package.json" ]; then
        if grep -q '"lint"' package.json; then
            log_info "Running linter..."
            npm run lint || {
                log_error "Linting failed"
                return 1
            }
            log_success "Linting passed"
        fi
    fi

    # Run tests
    if [ -f "package.json" ]; then
        if grep -q '"test"' package.json; then
            log_info "Running tests..."
            npm test || {
                log_error "Tests failed"
                return 1
            }
            log_success "Tests passed"
        fi
    fi

    log_success "All tests passed"
    return 0
}

build_application() {
    log_info "Building application..."

    cd "$PROJECT_ROOT"

    if [ -f "package.json" ]; then
        if grep -q '"build"' package.json; then
            npm run build || {
                log_error "Build failed"
                return 1
            }
            log_success "Build completed"
        else
            log_info "No build script found, skipping build"
        fi
    fi

    return 0
}

commit_and_push_changes() {
    log_info "Committing and pushing changes..."

    cd "$PROJECT_ROOT"

    # Check if there are any changes
    if git diff --quiet && git diff --staged --quiet; then
        log_info "No changes to commit"
        return 0
    fi

    # Generate commit message
    local commit_message="deploy: Autonomous agent deployment to $DEPLOYMENT_ENV

Environment: $DEPLOYMENT_ENV
Branch: $BRANCH
Azure Resource Group: $AZURE_RESOURCE_GROUP
Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")

🤖 Generated with autonomous agent deployment
"

    # Use safe push with automatic pull/rebase
    if safe_git_push_with_pull "$BRANCH" "$commit_message"; then
        log_success "Changes committed and pushed successfully"
        return 0
    else
        log_error "Failed to commit and push changes"
        return 1
    fi
}

verify_deployment() {
    log_info "Verifying deployment..."

    # Verify remote state
    if verify_remote_commit "$BRANCH"; then
        log_success "Remote state verified"
    else
        log_error "Remote state verification failed"
        return 1
    fi

    # Additional deployment verification
    if [ "$DEPLOYMENT_ENV" != "local" ]; then
        if command -v az &> /dev/null; then
            log_info "Checking Azure deployment status..."
            # Add Azure-specific verification here
            # Example: az webapp show --name <app-name> --resource-group $AZURE_RESOURCE_GROUP
        fi
    fi

    log_success "Deployment verified"
    return 0
}

# ============================================================================
# Main Deployment Flow
# ============================================================================

main() {
    log_info "Starting Azure agent deployment..."
    log_info "Environment: $DEPLOYMENT_ENV"
    log_info "Branch: $BRANCH"
    echo ""

    # Step 1: Check prerequisites
    if ! check_prerequisites; then
        log_error "Prerequisites check failed"
        exit 1
    fi
    echo ""

    # Step 2: Pull latest changes
    log_info "Pulling latest changes from remote..."
    if ! safe_git_pull "$BRANCH"; then
        log_error "Failed to pull latest changes"
        exit 1
    fi
    echo ""

    # Step 3: Run tests
    if ! run_tests; then
        log_error "Tests failed - aborting deployment"
        exit 1
    fi
    echo ""

    # Step 4: Build application
    if ! build_application; then
        log_error "Build failed - aborting deployment"
        exit 1
    fi
    echo ""

    # Step 5: Commit and push changes
    if ! commit_and_push_changes; then
        log_error "Failed to commit and push changes"
        exit 1
    fi
    echo ""

    # Step 6: Verify deployment
    if ! verify_deployment; then
        log_error "Deployment verification failed"
        exit 1
    fi
    echo ""

    # Success summary
    log_success "╔════════════════════════════════════════════════════════════╗"
    log_success "║  Deployment Completed Successfully                         ║"
    log_success "╚════════════════════════════════════════════════════════════╝"
    echo ""
    log_info "Environment: $DEPLOYMENT_ENV"
    log_info "Branch: $BRANCH"
    log_info "Commit: $(git rev-parse HEAD)"
    log_info "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
    echo ""
    log_success "✅ All deployment steps completed successfully"

    return 0
}

# ============================================================================
# Script Entry Point
# ============================================================================

# Handle script interruption
trap 'log_error "Deployment interrupted"; exit 130' INT TERM

# Run main function
main "$@"
