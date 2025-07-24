# geocaching-review-flet-selenium

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