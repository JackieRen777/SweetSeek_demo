#!/usr/bin/env bash
# Quick deploy script - commit, push, and trigger deployment
set -euo pipefail

# Check if there are changes to commit
if [[ -z "$(git status --porcelain)" ]]; then
  echo "No changes to commit"
  exit 0
fi

# Get commit message from user or use default
COMMIT_MSG="${1:-Update: quick deployment}"

# Clean up temporary files
find . -name "* 2.tsx" -type f -delete 2>/dev/null || true

# Commit and push
echo "📝 Committing changes..."
git add -A
git commit -m "$COMMIT_MSG

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"

echo "🚀 Pushing to GitHub..."
git push origin main

# Get the commit SHA
COMMIT=$(git rev-parse HEAD)
echo ""
echo "✅ Pushed successfully!"
echo "📦 Commit: $COMMIT"
echo ""
echo "🔄 CI will build and test (check: https://github.com/JackieRen777/SweetSeek_demo/actions)"
echo ""
echo "📋 After CI passes, deploy with:"
echo "   ssh your-server \"sudo bash /www/sweetseek/repo.git/../scripts/maintenance/deploy/deploy_ecs_oneclick.sh --commit $COMMIT\""
