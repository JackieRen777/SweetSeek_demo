#!/bin/bash
# Rollback Script
# Use this to revert the changes if the refactor causes issues.

echo "Reverting frontend refactoring..."
git checkout main
echo "Revert complete. You are now on the main branch."
