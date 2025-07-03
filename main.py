#!/usr/bin/env python3
"""
Arc Browser History to Firefox SQLite Importer

This script imports Arc browser history into Firefox's places.sqlite database,
making the history available in Firefox's address bar autocomplete and history view.

Usage:
    python exporthistory.py <arc_json_path> <firefox_places_path>

Example:
    python exporthistory.py ~/Library/Application\ Support/Arc/StorableArchiveItems.json \
        ~/Library/Application\ Support/Firefox/Profiles/xyz123.default/places.sqlite

Requirements:
    - Python 3.6+
    - Arc browser's StorableArchiveItems.json file
    - Firefox profile's places.sqlite file (Firefox must be closed)

Author: Pavel Galaton
License: MIT
"""

import json
import sqlite3
import argparse
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path



def arc_to_firefox_time(arc_timestamp):
    """Convert Arc timestamp to Firefox microseconds since 1970-01-01"""
    mac_epoch = 978307200
    unix_time = arc_timestamp + mac_epoch
    return int(unix_time * 1_000_000)

def calculate_frecency(visit_count, last_visit_time):
    """Calculate frecency score for Firefox autocomplete"""
    # Base score from visit count
    base_score = visit_count * 100
    
    # Recency bonus (more recent visits get higher scores)
    now = int(datetime.now().timestamp() * 1_000_000)
    days_ago = (now - last_visit_time) / (24 * 60 * 60 * 1_000_000)
    
    if days_ago < 1:
        recency_bonus = 1000
    elif days_ago < 7:
        recency_bonus = 500
    elif days_ago < 30:
        recency_bonus = 100
    else:
        recency_bonus = 0
    
    total_score = base_score + recency_bonus
    return min(total_score, 10000)  # Cap at 10000

def calculate_url_hash(url):
    """Calculate a hash for the URL"""
    return hash(url) & 0x7fffffff  # Ensure positive 32-bit integer

def validate_file_paths(arc_json_path, firefox_places_path):
    """Validate that the required files exist"""
    arc_path = Path(arc_json_path)
    firefox_path = Path(firefox_places_path)
    
    if not arc_path.exists():
        raise FileNotFoundError(f"Arc JSON file not found: {arc_json_path}")
    
    if not firefox_path.exists():
        raise FileNotFoundError(f"Firefox places.sqlite file not found: {firefox_places_path}")
    
    if not firefox_path.name == "places.sqlite":
        raise ValueError(f"Firefox path must point to places.sqlite file, got: {firefox_path.name}")

def load_arc_data(arc_json_path):
    """Load and parse Arc browser data from JSON file"""
    try:
        with open(arc_json_path, "r", encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in Arc file: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to read Arc file: {e}")

def parse_arc_history(arc_data):
    """Parse Arc browser data and extract visit information"""
    visits = defaultdict(list)
    
    for item in arc_data.get("items", []):
        if isinstance(item, dict) and "sidebarItem" in item:
            tab = item["sidebarItem"].get("data", {}).get("tab", {})
            title = tab.get("savedTitle")
            url = tab.get("savedURL")
            arc_id = item["sidebarItem"].get("id")
            timestamp = item.get("archivedAt") or tab.get("timeLastActiveAt")
            
            if title and url and timestamp:
                visits[url.strip()].append({
                    "title": title,
                    "id": arc_id,
                    "timestamp": timestamp
                })
    
    return visits

def import_to_firefox(visits, firefox_places_path):
    """Import visit data into Firefox places.sqlite database"""
    try:
        conn = sqlite3.connect(firefox_places_path)
        cursor = conn.cursor()
        
        # Get current max IDs to avoid conflicts
        cursor.execute("SELECT MAX(id) FROM moz_places")
        max_place_id = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT MAX(id) FROM moz_historyvisits")
        max_visit_id = cursor.fetchone()[0] or 0
        
        print(f"Current max place_id: {max_place_id}")
        print(f"Current max visit_id: {max_visit_id}")
        
        # Process each URL and its visits
        place_id_counter = max_place_id + 1
        visit_id_counter = max_visit_id + 1
        inserted_count = 0
        total_visits_added = 0
        
        for url, visit_list in visits.items():
            # Use the most recent title and timestamp for the entry
            latest = max(visit_list, key=lambda v: v["timestamp"])
            title = latest["title"]
            last_visit_time = arc_to_firefox_time(latest["timestamp"])
            visit_count = len(visit_list)
            
            # Check if URL already exists in moz_places
            cursor.execute("SELECT id, title, last_visit_date, visit_count FROM moz_places WHERE url = ?", (url,))
            existing_place = cursor.fetchone()
            
            if existing_place:
                place_id, existing_title, existing_last_visit, existing_visit_count = existing_place
                
                # Update existing place with newer data if needed
                if last_visit_time > (existing_last_visit or 0):
                    frecency = calculate_frecency(visit_count, last_visit_time)
                    cursor.execute("""
                        UPDATE moz_places 
                        SET title = ?, last_visit_date = ?, visit_count = visit_count + ?, 
                            frecency = ?, typed = 1, hidden = 0
                        WHERE id = ?
                    """, (title, last_visit_time, visit_count, frecency, place_id))
            else:
                # Calculate frecency based on visit count and recency
                frecency = calculate_frecency(visit_count, last_visit_time)
                
                # Calculate URL hash
                url_hash = calculate_url_hash(url)
                
                # Insert new place
                cursor.execute("""
                    INSERT INTO moz_places (id, url, title, rev_host, visit_count, hidden, typed, frecency, last_visit_date, guid, foreign_count, url_hash)
                    VALUES (?, ?, ?, ?, ?, 0, 1, ?, ?, ?, 0, ?)
                """, (place_id_counter, url, title, url.split('/')[2][::-1] if len(url.split('/')) > 2 else '', visit_count, frecency, last_visit_time, f"arc_{place_id_counter}", url_hash))
                
                place_id = place_id_counter
                place_id_counter += 1
            
            # Insert visit records
            for visit in visit_list:
                visit_time = arc_to_firefox_time(visit["timestamp"])
                
                # Check if this visit already exists (avoid duplicates)
                cursor.execute("SELECT id FROM moz_historyvisits WHERE place_id = ? AND visit_date = ?", (place_id, visit_time))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO moz_historyvisits (id, from_visit, place_id, visit_date, visit_type, session)
                        VALUES (?, 0, ?, ?, 1, 0)
                    """, (visit_id_counter, place_id, visit_time))
                    visit_id_counter += 1
                    total_visits_added += 1
            
            inserted_count += 1
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        return inserted_count, total_visits_added
        
    except sqlite3.Error as e:
        raise RuntimeError(f"SQLite error: {e}")
    except Exception as e:
        raise RuntimeError(f"Database operation failed: {e}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Import Arc browser history into Firefox places.sqlite database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import from default Arc location to Firefox
  python exporthistory.py ~/Library/Application\\ Support/Arc/StorableArchiveItems.json \\
      ~/Library/Application\\ Support/Firefox/Profiles/xyz123.default/places.sqlite
  
  # Import from custom locations
  python exporthistory.py /path/to/arc/data.json /path/to/firefox/places.sqlite
        """
    )
    
    parser.add_argument(
        "arc_json_path",
        help="Path to Arc browser's StorableArchiveItems.json file"
    )
    
    parser.add_argument(
        "firefox_places_path", 
        help="Path to Firefox profile's places.sqlite file"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate data without importing to database"
    )
    
    args = parser.parse_args()
    
    try:
        print("Arc Browser History to Firefox Importer")
        print("=" * 40)
        
        # Validate file paths
        print("Validating file paths...")
        validate_file_paths(args.arc_json_path, args.firefox_places_path)
        print("✓ File paths validated")
        
        # Load Arc data
        print("Loading Arc browser data...")
        arc_data = load_arc_data(args.arc_json_path)
        print(f"✓ Loaded Arc data with {len(arc_data.get('items', []))} items")
        
        # Parse Arc history
        print("Parsing Arc history...")
        visits = parse_arc_history(arc_data)
        print(f"✓ Parsed {len(visits)} unique URLs")
        
        if args.dry_run:
            print("\nDry run completed successfully!")
            print(f"Would import {len(visits)} URLs with {sum(len(v) for v in visits.values())} total visits")
            return
        
        # Import to Firefox
        print("Importing to Firefox database...")
        inserted_count, total_visits = import_to_firefox(visits, args.firefox_places_path)
        
        print("\nImport completed successfully!")
        print(f"✓ Imported {inserted_count} history items")
        print(f"✓ Added {total_visits} visit records")
        print("\nNote: Restart Firefox to see changes in address bar autocomplete")
        
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nImport cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
