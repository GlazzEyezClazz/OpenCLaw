#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/safeuser/.openclaw/workspace"
REMOTE_URL="git@github.com:GlazzEyezClazz/OpenCLaw.git"
TZ_LOCAL="Asia/Yekaterinburg"

cd "$REPO_DIR"

# Ensure remote exists
if ! git remote get-url origin >/dev/null 2>&1; then
  git remote add origin "$REMOTE_URL"
fi

# Stage all workspace changes
git add -A

# Commit only when there are changes
if git diff --cached --quiet; then
  exit 0
fi

LOCAL_TS="$(TZ="$TZ_LOCAL" date +"%Y-%m-%d %H:%M %Z")"
UTC_TS="$(date -u +"%Y-%m-%d %H:%M UTC")"
COMMIT_MSG="Daily knowledge base backup | ${LOCAL_TS} | ${UTC_TS}"

git commit -m "$COMMIT_MSG"

# Optional safety marker: one tag per local day (keeps easy rollback points)
DAILY_TAG="backup-$(TZ="$TZ_LOCAL" date +"%Y-%m-%d")"
if ! git rev-parse -q --verify "refs/tags/${DAILY_TAG}" >/dev/null; then
  git tag "$DAILY_TAG"
fi

# Push commits and tags to GitHub
git push -u origin master
git push origin --tags
