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
6. **Complete**: When done, click **CLOSE** to quit Firefox, then use the red circle (upper left) to close the app

## Configuration

Create a `.env` file in the project root with:
```
PASSWORD=your_geocaching_password
```

## Recent Updates

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