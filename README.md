# geocaching-review-flet-selenium

A work in progress demonstrating Flet with Selenium for geocaching review tasks.

## Features

- **Automated Firefox Setup**: Automatically launches Firefox with your existing profile (including extensions)
- **Progress Tracking**: Visual progress bar and status updates during initialization
- **Bookmark List Assignment**: Bulk add caches to a specified bookmark list
- **Timed Publishing**: Schedule multiple caches for timed publication with custom date and time
- **Disable with Same Message**: Apply the same disable message to multiple caches
- **Persistent Settings**: Bookmark name and timed publish date/time are saved between sessions
- **Real-time Status Updates**: In-app status messages show operation progress and errors
- **Error Handling**: Validates inputs and provides clear error messages
- **Queue Dump to CSV**: Export on-hold listings to a sorted CSV file

## Automation Selector Reference

- See [HTML_ELEMENTS.md](HTML_ELEMENTS.md) for a complete list of HTML elements/selectors used by Selenium and why each is needed.

## Installation

Run the included `run.sh` script which will:
1. Create a Python virtual environment (`.venv`) if it doesn't exist
2. Install all required dependencies from `python-requirements.txt`
3. Launch the Flet application

```bash
./run.sh
```

If you need to make the script executable:
```bash
chmod +x run.sh
```

## Usage

1. **Launch**: Run `./run.sh` to start the application
2. **Wait for Firefox**: The app will load Firefox with your profile (be patient during initial load)
3. **Load Review Tabs**: In the Firefox window, open the review queue tabs you want to process
4. **Configure Actions**:
   - **Add to Bookmark List**: Check the box and enter your bookmark list name
   - **Add to Timed Publishing**: Check the box and select date/time using the pickers
   - **Disable with Same Message**: Check the box (ensure clipboard has your message)
5. **Execute**: Click **GO!** to process all loaded review tabs
6. **Export Queue**: Click **Dump On-Hold to CSV** to export all on-hold listings with publication dates
   - A Firefox window opens to the queue page using your configured profile
   - The app will scrape the data and create a sorted CSV file (`geocaching_queue.csv`)
   - CSV columns: `ID`, `Set to publish`, `D`, `T`, `Title`, `Owner`
   - `D`/`T` are extracted from the ID block (e.g., `(2/1.5)`), and `Set to publish` is extracted from the title text
7. **Complete**: When done, click **CLOSE** to quit Firefox, then use the red circle (upper left) to close the app

### CSV Export Troubleshooting

- After export, check the in-app status summary (example: `Exported 259 unique IDs | missing publish: 0 | missing D/T: 0`).
- If `geocaching_queue.csv` appears to have far more lines than listings, compare against the in-app **unique ID** count.
- Confirm the output header is exactly: `ID,Set to publish,D,T,Title,Owner`.
- Spot-check a few rows:
   - `ID` should look like `GC...`
   - `D` and `T` should be numeric values from `(D/T)`
   - `Set to publish` should be parsed from `Set to publish at ...` text
- If data looks shifted, rerun **Dump On-Hold to CSV** after the queue page is fully loaded in Firefox.
- If needed, delete `geocaching_queue.csv` and export again to avoid comparing against stale output.

## Configuration

Copy `example.env` to `.env` in the project root, then fill in your real values:

```bash
cp example.env .env
```

Template contents:

```
USERNAME=your_geocaching_username
PASSWORD=your_geocaching_password
FIREFOX_PROFILE_PATH=/full/path/to/your/firefox/profile
GEOCACHING_SCRAPE_QUEUE_URL=https://www.geocaching.com/admin/queue.aspx?filter=AllHolds&stateid=16&pagesize=-1
```

The app also accepts the older aliases `GEOCACHING_USERNAME` and `GEOCACHING_FIREFOX_PROFILE`.

`GEOCACHING_SCRAPE_QUEUE_URL` is used to open the queue page after login and as the CSV export target page.

After opening that URL, the app sets the queue filter by workflow:
- Startup/normal processing (`GO!`) forces filter value `1` (**All Caches Not On Hold**).
- **Dump On-Hold to CSV** forces filter value `3` (**All Caches I'm Holding**).

You can point `GEOCACHING_SCRAPE_QUEUE_URL` to similar queue pages (different filters/states) without changing code.

## Recent Updates

### 2026-02-11
- Added timed publish increments with blackout window enforcement (10 PM–6 AM) and chained increments.
- Added disable message input (persistent) and conditional visibility when enabled.
- Added splash-screen Firefox profile path input with required selection before start.
- Added profile selection persistence and support for manual path entry.
- Added automatic closure of extra tabs opened during startup/processing.
- Improved disable workflow tab targeting and retries to avoid wrong tabs.
- Added detailed per-listing logging and error context for operations.
- Made the UI scrollable and adjusted layout to prevent controls from being hidden.
- Fixed ISO datetime parsing for timed publish dates.

### Session Enhancements
- Added `run.sh` script for easy setup and launch
- Implemented Firefox profile loading to preserve extensions
- Added loading progress bar with stage-by-stage updates
- Persistent storage for bookmark name and timed publish settings
- Enhanced cookie banner dismissal with retry logic
- Added scroll-into-view and timing delays to prevent element interception
- Implemented 12-hour to 24-hour time conversion for timed publishing
- Added detailed status messages for each operation stage
- GO button transforms to CLOSE after completion
- Improved error handling with in-app status display
- Added tab filtering to only process review detail pages
- Real-time status updates throughout operations

## Requirements

- Python 3.10+
- Firefox browser
- See `python-requirements.txt` for Python dependencies

## Project Setup

I used the `venv` guidance at [https://flet.dev/docs/getting-started/create-flet-app](https://flet.dev/docs/getting-started/create-flet-app) to create this project.  My specific, complete command sequence was...  

```zsh
cd ~/GitHub
mkdir geocaching-review-flet-selenium
cd geocaching-review-flet-selenium
python3 -m venv .venv
source .venv/bin/activate
pip3 install 'flet[all]'
pip3 install selenium os dotenv
pip3 freeze > python-requirements.txt
flet create
# Created new empty project directory at https://github.com/SummittDweller/geocaching-review-flet-selenium, then...  
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/SummittDweller/geocaching-review-flet-selenium.git
git push -u origin main
```

I have since added a `.env` file to the project and am keeping it out of GitHub with an addition to the `.gitignore` file.  

## Flet Controls 

See [https://flet-controls-gallery.fly.dev](https://flet-controls-gallery.fly.dev) for a complete demo of all available controls.  

## Run the app

Run as a desktop app:  

```
flet run
```

Run as a web app:  

```
flet run --web
```

For more details on running the app, refer to the [Getting Started Guide](https://flet.dev/docs/getting-started/).

## Build the app

### Android

```
flet build apk -v
```

For more details on building and signing `.apk` or `.aab`, refer to the [Android Packaging Guide](https://flet.dev/docs/publish/android/).

### iOS

```
flet build ipa -v
```

For more details on building and signing `.ipa`, refer to the [iOS Packaging Guide](https://flet.dev/docs/publish/ios/).

### macOS

```
flet build macos -v
```

For more details on building macOS package, refer to the [macOS Packaging Guide](https://flet.dev/docs/publish/macos/).

### Linux

```
flet build linux -v
```

For more details on building Linux package, refer to the [Linux Packaging Guide](https://flet.dev/docs/publish/linux/).

### Windows

```
flet build windows -v
```

For more details on building Windows package, refer to the [Windows Packaging Guide](https://flet.dev/docs/publish/windows/).