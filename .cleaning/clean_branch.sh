name: Clean Odoo Framework

on:
  workflow_dispatch:
  push:
    branches:
      - "18.0"

jobs:
  clean:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Ensure Python available
        uses: actions/setup-python@v4
        with:
          python-version: "3.x"

      - name: Make cleanup script executable
        run: chmod +x scripts/clean_branch.sh

      - name: Switch to clean branch (from 18.0)
        run: |
          git checkout -B 18.0-cleaned 18.0

      - name: Run cleanup script
        run: bash scripts/clean_branch.sh

      - name: Commit cleaned version
        run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add -A
          git commit -m "🔄 Build cleaned from 18.0" || echo "No changes to commit"
          git push origin 18.0-cleaned --force
