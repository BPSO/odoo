#!/usr/bin/env python3
import os
import re
import json
import pprint
import importlib.util

ADDONS_ROOT = "addons"
REPORT_DIR = "build_reports"
os.makedirs(REPORT_DIR, exist_ok=True)

# Dépendances qu'on veut supprimer si elles apparaissent encore
EXCLUDED_DEPENDS = {"iap", "crm", "portal", "contacts"}

# Modules techniques conservés (pour forcer quelques flags)
TECH_MODULES = {"base", "web", "mail", "bus", "base_setup"}

# Langage: remplacements "informatifs" uniquement
RENAME_MAP = {
    # Respect de la casse:
    r"\bOdoo\b": "Solservo",   # Odoo → Solservo
    r"\bODOO\b": "SOLSERVO",   # ODOO → SOLSERVO
    # NOTE: on ne remplace PAS "odoo" en minuscules (imports/code)
}

def load_manifest(path):
    """
    Charge un __manifest__.py en exécutant le fichier dans un namespace isolé.
    Odoo utilise un dict littéral: c'est sûr dans notre contexte de CI contrôlé.
    """
    data = {}
    spec = importlib.util.spec_from_file_location("manifest_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    # Chercher __manifest__ ou __openerp__ (anciennes versions)
    if hasattr(mod, "__manifest__"):
        return mod.__manifest__
    if hasattr(mod, "__openerp__"):
        return mod.__openerp__
    raise RuntimeError(f"Impossible de trouver __manifest__ dans {path}")

def save_manifest(path, manifest):
    # Réécrit le dict de façon propre
    text = pprint.pformat(manifest, width=100, sort_dicts=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text + "\n")

def module_name_from_manifest(path):
    # addons/<mod>/__manifest__.py → <mod>
    return os.path.basename(os.path.dirname(path))

def file_should_rename_text(fname):
    # On remplace uniquement dans ces extensions
    lower = fname.lower()
    if lower.endswith(".md") or lower.endswith(".xml") or lower.endswith(".po"):
        return True
    return False

def apply_rename_in_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    orig = content
    for pat, repl in RENAME_MAP.items():
        content = re.sub(pat, repl, content)
    if content != orig:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False

def normalize_manifest(manifest, modname, report):
    changed = False

    # 1) depends: supprimer les modules exclus s'ils apparaissent
    depends = list(manifest.get("depends", []))
    new_depends = [d for d in depends if d not in EXCLUDED_DEPENDS]
    if new_depends != depends:
        report.setdefault("removed_depends", []).extend(sorted(set(depends) - set(new_depends)))
        manifest["depends"] = new_depends
        changed = True

    # 2) flags techniques
    if modname in TECH_MODULES:
        # base_setup: neutraliser fortement
        if modname == "base_setup":
            if manifest.get("depends"):
                report.setdefault("base_setup_depends_cleared", True)
            manifest["depends"] = []
            if manifest.get("auto_install", True) is not False:
                manifest["auto_install"] = False
                report.setdefault("auto_install_false", True)
            if manifest.get("application", True) is not False:
                manifest["application"] = False
                report.setdefault("application_false", True)
            if manifest.get("category") != "Technical Settings":
                manifest["category"] = "Technical Settings"
                report.setdefault("category_set", True)
            changed = True
        else:
            # Modules techniques: s'assurer que ce ne sont pas des "applications"
            if manifest.get("application", False):
                manifest["application"] = False
                report.setdefault("application_false", True)
                changed = True

    # 3) license
    if manifest.get("license") != "LGPL-3":
        manifest["license"] = "LGPL-3"
        report.setdefault("license_set", True)
        changed = True

    # 4) category
    cat = manifest.get("category")
    if not cat or cat.lower() in {"accounting", "sales", "inventory", "crm"}:
        manifest["category"] = "Technical Settings"
        report.setdefault("category_set", True)
        changed = True

    # 5) version (normalisation légère)
    ver = manifest.get("version")
    if ver and not ver.endswith("-base"):
        manifest["version"] = "18.0-base"
        report.setdefault("version_normalized", True)
        changed = True

    # 6) nettoyage cosmétique
    removed = []
    for k in ("website", "maintainer", "support"):
        if k in manifest:
            removed.append(k)
            manifest.pop(k, None)
            changed = True
    if removed:
        report.setdefault("removed_keys", []).extend(removed)

    # 7) Renommage informatif dans manifest (name/summary/description)
    for key in ("name", "summary", "description"):
        if key in manifest and isinstance(manifest[key], str):
            orig = manifest[key]
            new = orig
            for pat, repl in RENAME_MAP.items():
                new = re.sub(pat, repl, new)
            if new != orig:
                manifest[key] = new
                report.setdefault("renamed_fields", []).append(key)
                changed = True

    return changed

def main():
    overall = {}

    # A) Ajuster manifests
    adjusted = {}
    for root, _, files in os.walk(ADDONS_ROOT):
        for fn in files:
            if fn == "__manifest__.py":
                path = os.path.join(root, fn)
                modname = module_name_from_manifest(path)
                try:
                    manifest = load_manifest(path)
                except Exception as e:
                    adjusted[path] = {"error": str(e)}
                    continue

                report = {}
                changed = normalize_manifest(manifest, modname, report)
                if changed:
                    save_manifest(path, manifest)
                    adjusted[path] = report

    overall["manifests_adjusted"] = adjusted

    # B) Rapport
    with open(os.path.join(REPORT_DIR, "manifest_adjustments.json"), "w", encoding="utf-8") as f:
        json.dump(overall, f, indent=2, ensure_ascii=False)

    with open(os.path.join(REPORT_DIR, "manifest_adjustments.md"), "w", encoding="utf-8") as f:
        f.write("# Manifest adjustments report\n\n")
        f.write(f"- Renamed text files: **{overall['renamed_text_files_count']}**\n")
        f.write("- Adjusted manifests:\n")
        for path, rep in adjusted.items():
            f.write(f"  - `{path}`:\n")
            for k, v in rep.items():
                f.write(f"    - {k}: {v}\n")

    print("✅ adjust_manifests.py terminé")

if __name__ == "__main__":
    main()
