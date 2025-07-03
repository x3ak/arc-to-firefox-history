# Arc Browser History to Firefox Importer

A Python script to import Arc browser history into Firefox's SQLite database, making your Arc browsing history available in Firefox's address bar autocomplete and history view.

## Features

- ✅ Imports Arc browser history to Firefox's `places.sqlite` database
- ✅ Preserves visit counts and timestamps
- ✅ Enables address bar autocomplete for imported URLs
- ✅ Handles duplicate URLs gracefully
- ✅ Calculates proper frecency scores for Firefox's ranking algorithm
- ✅ Supports dry-run mode for testing
- ✅ Comprehensive error handling and validation

## Requirements

- Python 3.6 or higher
- Arc browser's `StorableArchiveItems.json` file
- Firefox profile's `places.sqlite` file (Firefox must be closed during import)

## Installation

1. Clone or download this repository
2. No additional dependencies required (uses only Python standard library)

## Usage

### Basic Usage

```bash
python exporthistory.py <arc_json_path> <firefox_places_path>
```

### Examples

**Import from default Arc location to Firefox:**
```bash
python exporthistory.py ~/Library/Application\ Support/Arc/StorableArchiveItems.json \
    ~/Library/Application\ Support/Firefox/Profiles/xyz123.default/places.sqlite
```

**Import from custom locations:**
```bash
python exporthistory.py /path/to/arc/data.json /path/to/firefox/places.sqlite
```

**Dry run (test without importing):**
```bash
python exporthistory.py --dry-run ~/Library/Application\ Support/Arc/StorableArchiveItems.json \
    ~/Library/Application\ Support/Firefox/Profiles/xyz123.default/places.sqlite
```

## Finding Your Files

### Arc Browser Data Location

**macOS:**
```
~/Library/Application Support/Arc/StorableArchiveItems.json
```

**Windows:**
```
%APPDATA%\Arc\User Data\Default\StorableArchiveItems.json
```

### Firefox Profile Location

**macOS:**
```
~/Library/Application Support/Firefox/Profiles/<profile-id>.default/places.sqlite
```

**Windows:**
```
%APPDATA%\Mozilla\Firefox\Profiles\<profile-id>.default\places.sqlite
```

**Linux:**
```
~/.mozilla/firefox/<profile-id>.default/places.sqlite
```

To find your Firefox profile ID:
1. Open Firefox
2. Go to `about:profiles` in the address bar
3. Look for the "Root Directory" path of your default profile

## Important Notes

⚠️ **Firefox must be completely closed** before running the import script to avoid database locking issues.

⚠️ **Backup your Firefox profile** before running the script (copy the entire profile folder).

⚠️ **Restart Firefox** after the import to see changes in address bar autocomplete.

## How It Works

1. **Parses Arc Data**: Reads the `StorableArchiveItems.json` file and extracts URL, title, and timestamp information
2. **Validates Files**: Ensures both input and output files exist and are accessible
3. **Calculates Frecency**: Computes Firefox's frecency score based on visit count and recency
4. **Updates Database**: Inserts or updates records in Firefox's `moz_places` and `moz_historyvisits` tables
5. **Handles Duplicates**: Avoids creating duplicate visit records

## Firefox Database Schema

The script works with Firefox's Places database schema:

- **`moz_places`**: Stores URL information, titles, visit counts, and frecency scores
- **`moz_historyvisits`**: Stores individual visit records with timestamps

Key fields populated:
- `frecency`: Score used by Firefox for autocomplete ranking
- `typed`: Indicates URL should appear in typed URL suggestions
- `hidden`: Set to 0 to ensure URLs appear in autocomplete
- `url_hash`: Performance optimization hash

## Troubleshooting

### Common Issues

**"Firefox places.sqlite file not found"**
- Make sure Firefox is closed
- Verify the profile path is correct
- Check that the file is named `places.sqlite`

**"Arc JSON file not found"**
- Verify the path to your Arc data file
- Check file permissions

**"SQLite error"**
- Ensure Firefox is completely closed
- Check if the database file is corrupted
- Try backing up and restoring your Firefox profile

**"Import completed but no autocomplete"**
- Restart Firefox completely
- Clear Firefox's autocomplete cache (about:config → browser.urlbar.autocomplete.enabled)
- Wait a few minutes for Firefox to rebuild its indexes

### Getting Help

If you encounter issues:

1. Run with `--dry-run` first to validate your data
2. Check the error messages for specific issues
3. Ensure Firefox is completely closed before running
4. Try with a fresh Firefox profile to test

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Author

Pavel Galaton

## Disclaimer

This tool modifies Firefox's internal database. Use at your own risk and always backup your Firefox profile before running the script. 
