# GUI Quick Start Guide

## Starting the Application

### Method 1: Using the launcher script (Easiest)
```bash
./start.sh
```

### Method 2: Using Python directly
```bash
python launch_gui.py
```

The launcher will automatically:
- Use the project's `.venv` when available
- Check for missing dependencies
- Launch the GUI

## Using the GUI

### 1. Enter Anime URL
Paste the AnimeUnity URL of the series you want to download.

**Example:**
```
https://www.animeunity.so/anime/1517-yuru-yuri
```

### 2. Set Episode Range

**Start Episode:** 
- Default is `1` (first episode)
- Change this if you want to start from a different episode

**End Episode:**
- Leave empty to download all episodes from start to end
- Set a number to stop at a specific episode

**Examples:**
- Start: `1`, End: `` (empty) → Downloads all episodes
- Start: `5`, End: `10` → Downloads episodes 5 through 10
- Start: `1`, End: `5` → Downloads episodes 1 through 5
- Start: `10`, End: `` (empty) → Downloads from episode 10 to the last

### 3. Choose Download Location

Click the **"Browse"** button to select where you want to save the episodes.

Default location: `Downloads` folder in the current directory

### 4. Start Download

Click the **"Download"** button to begin.

**During download:**
- The progress bar will show activity
- Status updates will appear at the bottom
- The UI will be disabled until download completes

**After download:**
- A success message will appear
- All downloaded episodes will be in your chosen directory
- Episodes are organized in a folder named after the anime

## Troubleshooting

### "Please enter an anime URL"
Make sure you've pasted a valid AnimeUnity URL in the first field.

### "Start episode must be less than or equal to end episode"
Check your episode numbers - the start number should be smaller than the end number.

### Download fails
- Check your internet connection
- Verify the anime URL is correct and still accessible
- Make sure you have write permissions in the download directory

### Dependencies not installing
Activate the project virtual environment and run:
```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Features

- **Clean Interface:** Simple and intuitive design
- **Progress Tracking:** See download status in real-time
- **Flexible Episodes:** Download single episodes, ranges, or entire series
- **Custom Location:** Save files wherever you want
- **Automatic Organization:** Episodes organized by anime name
