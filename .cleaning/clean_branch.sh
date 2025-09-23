#!/bin/bash
set -e

echo "🔹 Nettoyage du repo pour base_framework"

# 0) Modules à conserver (techniques). Ajuste la liste si besoin.
KEEP_MODULES=("base" "web" "web_tour" "html_editor" "mail" "bus" "base_setup" "l10n_be")

# 1) Supprimer tous les addons sauf ceux conservés
for d in addons/*; do
  [ -d "$d" ] || continue
  mod="$(basename "$d")"
  keep=false
  for k in "${KEEP_MODULES[@]}"; do
    if [ "$mod" = "$k" ]; then keep=true; break; fi
  done
  if [ "$keep" = false ]; then
    echo "🗑️  Suppression module: $mod"
    rm -rf "$d"
  else
    echo "✅ On garde: $mod"
  fi
done

# 2) i18n → garder uniquement EN/FR/NL (et variantes)
# (en*, fr*, nl*)
find addons -type f -path "*/i18n/*.po" \
  ! -name "en*.po" \
  ! -name "fr*.po" \
  ! -name "nl*.po" \
  -delete

# 3) Suppression ciblée de fichiers individuels
# Liste des fichiers (chemins relatifs au repo) à supprimer
single_files_to_delete=(
  ".github/PULL_REQUEST_TEMPLATE.md"
  ".github/ISSUE_TEMPLATE/1_bug_form.yml"
  ".github/ISSUE_TEMPLATE/config.yml"
)

for f in "${single_files_to_delete[@]}"; do
  if [ -f "$f" ]; then
    echo "🗑️  Suppression fichier: $f"
    rm -f "$f"
  else
    echo "ℹ️  Fichier absent (ok): $f"
  fi
done

# 4) Supprimer fichiers Windows-only
find . -type f -name "*.bat" -delete
find . -type d -iname "*win32*" -exec rm -rf {} +

echo "✅ Nettoyage terminé"
