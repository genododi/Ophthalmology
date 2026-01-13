#!/usr/bin/env python3
"""
Ophthalmic Infographic Library Sync Script

This script:
1. Generates a library-index.json from all JSON files in the library folder
2. Commits and pushes changes to GitHub

Usage:
    python sync_to_github.py           # Generate index and push
    python sync_to_github.py --index   # Only generate index (no git)
    python sync_to_github.py --push    # Only push (assumes index exists)
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration
SCRIPT_DIR = Path(__file__).parent
LIBRARY_DIR = SCRIPT_DIR / "library"
INDEX_FILE = SCRIPT_DIR / "library-index.json"
GITHUB_REPO = "https://github.com/genododi/ophthalmology.git"

def log(msg, level="INFO"):
    """Print colored log messages."""
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m"
    }
    print(f"{colors.get(level, '')}{level}: {msg}{colors['RESET']}")


def generate_library_index():
    """Read all JSON files from library folder and create a combined index."""
    log("Generating library index...")
    
    if not LIBRARY_DIR.exists():
        log(f"Library directory not found: {LIBRARY_DIR}", "WARNING")
        LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
        log(f"Created library directory: {LIBRARY_DIR}", "INFO")
    
    all_items = []
    json_files = list(LIBRARY_DIR.glob("*.json"))
    
    log(f"Found {len(json_files)} JSON files in library folder")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                item = json.load(f)
                
                # Ensure essential fields exist
                if 'id' not in item:
                    # Generate ID from filename
                    item['id'] = int(json_file.stem.split('_')[0]) if json_file.stem.split('_')[0].isdigit() else hash(json_file.stem)
                
                if 'title' not in item:
                    # Generate title from filename
                    item['title'] = json_file.stem.replace('_', ' ')
                
                if 'date' not in item:
                    # Use file modification time
                    item['date'] = datetime.fromtimestamp(json_file.stat().st_mtime).isoformat()
                
                if 'chapterId' not in item:
                    item['chapterId'] = 'uncategorized'
                
                all_items.append(item)
                
        except json.JSONDecodeError as e:
            log(f"Invalid JSON in {json_file.name}: {e}", "WARNING")
        except Exception as e:
            log(f"Error reading {json_file.name}: {e}", "ERROR")
    
    # Sort by date (newest first)
    all_items.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # Assign sequential IDs if missing
    max_seq = max((item.get('seqId', 0) for item in all_items), default=0)
    for item in all_items:
        if not item.get('seqId'):
            max_seq += 1
            item['seqId'] = max_seq
    
    # Write the index file
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)
    
    log(f"Generated {INDEX_FILE.name} with {len(all_items)} items", "SUCCESS")
    return len(all_items)


def check_git_status():
    """Check if we're in a git repo and have changes."""
    try:
        # Check if in git repo
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            log("Not a git repository. Initializing...", "WARNING")
            subprocess.run(['git', 'init'], cwd=SCRIPT_DIR, check=True)
            subprocess.run(['git', 'remote', 'add', 'origin', GITHUB_REPO], cwd=SCRIPT_DIR, check=False)
        
        # Check for changes
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True
        )
        return len(result.stdout.strip()) > 0
    except Exception as e:
        log(f"Git check failed: {e}", "ERROR")
        return False


def push_to_github():
    """Commit and push changes to GitHub."""
    log("Preparing to push to GitHub...")
    
    try:
        # Add all changes
        subprocess.run(['git', 'add', '.'], cwd=SCRIPT_DIR, check=True)
        
        # Check if there are changes to commit
        result = subprocess.run(
            ['git', 'diff', '--cached', '--quiet'],
            cwd=SCRIPT_DIR,
            capture_output=True
        )
        
        if result.returncode == 0:
            log("No changes to commit", "INFO")
            return True
        
        # Commit with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = f"Auto-sync library: {timestamp}"
        
        subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            cwd=SCRIPT_DIR,
            check=True
        )
        log(f"Committed: {commit_msg}", "SUCCESS")
        
        # Push to origin
        log("Pushing to GitHub...", "INFO")
        result = subprocess.run(
            ['git', 'push', '-u', 'origin', 'main'],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Try 'master' branch if 'main' fails
            result = subprocess.run(
                ['git', 'push', '-u', 'origin', 'master'],
                cwd=SCRIPT_DIR,
                capture_output=True,
                text=True
            )
        
        if result.returncode == 0:
            log("Successfully pushed to GitHub!", "SUCCESS")
            log(f"View at: https://genododi.github.io/ophthalmology/", "INFO")
            return True
        else:
            log(f"Push failed: {result.stderr}", "ERROR")
            return False
            
    except subprocess.CalledProcessError as e:
        log(f"Git operation failed: {e}", "ERROR")
        return False
    except Exception as e:
        log(f"Error: {e}", "ERROR")
        return False


def copy_library_to_root():
    """Copy library JSON files to root for GitHub Pages access."""
    log("Copying library files to root Library folder...")
    
    # Create Library folder in root (GitHub uses this)
    root_library = SCRIPT_DIR / "Library"
    root_library.mkdir(exist_ok=True)
    
    # Copy all JSON files
    import shutil
    for json_file in LIBRARY_DIR.glob("*.json"):
        dest = root_library / json_file.name
        shutil.copy2(json_file, dest)
    
    log(f"Copied files to {root_library}", "SUCCESS")


def main():
    print("\n" + "="*50)
    print("  Ophthalmic Infographic Library Sync")
    print("="*50 + "\n")
    
    args = sys.argv[1:]
    
    if '--index' in args:
        # Only generate index
        generate_library_index()
    elif '--push' in args:
        # Only push
        push_to_github()
    else:
        # Full sync: generate index, copy files, and push
        item_count = generate_library_index()
        
        if item_count > 0:
            copy_library_to_root()
        
        if check_git_status():
            push_to_github()
        else:
            log("No changes detected", "INFO")
    
    print("\n" + "="*50)
    print("  Sync Complete!")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()
