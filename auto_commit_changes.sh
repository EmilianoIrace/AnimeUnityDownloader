#!/bin/bash
set -e

# --- CONFIGURATION ---
REPO_PATH=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_PATH")
MIRROR_PATH="${REPO_PATH}.git"
BFG_JAR="/opt/homebrew/Cellar/bfg/1.15.0/libexec/bfg-1.15.0.jar"  # Adjust if needed

cd "$REPO_PATH"
echo "🚀 Starting automatic commit + cleanup for $REPO_NAME..."

# --- DETERMINE SCRIPT RELATIVE PATH (to exclude from commit/display) ---
# Works even if invoked from outside repo root
SCRIPT_ABS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_ABS_PATH="$SCRIPT_ABS_DIR/$(basename "${BASH_SOURCE[0]}")"
# Derive path relative to repo (empty if script is outside repo; then we don't exclude)
case "$SCRIPT_ABS_PATH" in
  "$REPO_PATH"/*) SCRIPT_REL_PATH="${SCRIPT_ABS_PATH#"$REPO_PATH/"}" ;;
  *) SCRIPT_REL_PATH="" ;;
esac

# --- FIND CHANGES (deleted vs added/modified/untracked) ---
# Use ls-files flags to avoid deleted files leaking into the "added" list.
# -d: deleted (tracked, missing in working tree)
# -m: modified (tracked)
# -o: others/untracked (respects .gitignore via --exclude-standard)
deleted_files=$(git ls-files -d)
added_files=$(git ls-files -m -o --exclude-standard)

# Remove any paths from added_files that are also in deleted_files
# Do this case-insensitively on macOS to handle case-only renames
if [ -n "$deleted_files" ] && [ -n "$added_files" ]; then
  if [ "$(uname -s)" = "Darwin" ]; then
    deleted_lc=$(printf "%s\n" "$deleted_files" | tr '[:upper:]' '[:lower:]')
    added_files=$(printf "%s\n" "$added_files" | awk -v dels="$deleted_lc" '
      BEGIN{ n=split(dels, a, "\n"); for(i=1;i<=n;i++){ d[a[i]]=1 } }
      { key=tolower($0); if(!(key in d)) print $0 }
    ')
  else
    added_files=$(awk 'NR==FNR{d[$0]=1; next} { if(!($0 in d)) print $0 }' \
      <(printf "%s\n" "$deleted_files") <(printf "%s\n" "$added_files"))
  fi
fi

# Exclude this script itself from the "added" display list
if [ -n "$SCRIPT_REL_PATH" ]; then
  added_files=$(echo "$added_files" | awk -v skip="$SCRIPT_REL_PATH" 'NF && $0!=skip')
fi

echo
echo "📋 Changes detected:"
[ -n "$deleted_files" ] && echo "$deleted_files" | sed 's/^/  🗑️  /'
[ -n "$added_files" ] && echo "$added_files" | sed 's/^/  ➕  /'
echo

if [ -z "$deleted_files" ] && [ -z "$added_files" ]; then
  echo "⚠️  No changes to commit. Exiting."
  exit 0
fi

# --- ASK FOR COMMIT MESSAGE ---
read -p "✏️  Enter commit message: " commit_message

# --- COMMIT CHANGES ---
# Stage everything, then ensure this script isn't included (if inside repo)
git add -A
if [ -n "$SCRIPT_REL_PATH" ]; then
  git reset -- "$SCRIPT_REL_PATH" >/dev/null 2>&1 || true
fi
git commit -m "$commit_message"
echo "✅ Commit created: '$commit_message'"

# --- CREATE MIRROR CLONE ---
cd "$(dirname "$REPO_PATH")"
rm -rf "$MIRROR_PATH"
git clone --mirror "$REPO_PATH" "$MIRROR_PATH"

# --- RUN BFG ON DELETED FILES ---
cd "$MIRROR_PATH"
if [ -n "$deleted_files" ]; then
  echo "🧹 Running BFG to remove deleted files from history..."
  # Pass deleted files safely to BFG (one per arg)
  # shellcheck disable=SC2086
  java -jar "$BFG_JAR" --delete-files $(echo "$deleted_files" | tr '\n' ' ')
else
  echo "✅ No deleted files to clean with BFG."
fi

# --- CLEAN GIT HISTORY ---
echo "🧽 Cleaning Git reflog and objects..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# --- PUSH CLEAN HISTORY ---
echo
read -p "📤 Push cleaned history to remote (force)? [y/N]: " confirm_push
if [[ "$confirm_push" =~ ^[Yy]$ ]]; then
  git push --force
  echo "✅ Force-pushed cleaned repo to remote."
else
  echo "🚫 Skipped remote push. Cleaned mirror remains at:"
  echo "   $MIRROR_PATH"
fi

echo
echo "🎯 All done! Repository cleaned and committed."