# StreamingSimplifier

A desktop application that tracks live NBA and MLB games and streams associated audio (radio or game broadcast) using Playwright-controlled browser contexts. Built with Python, Tkinter for the GUI, and Playwright for launching persistent Chromium contexts (Edge).

## Features

- **NBA Tab**: Fetches live NBA game data, displays matchups, scores, and game status. Auto-launches the NBA.com live audio feed and mutes/unmutes when switching tabs.
- **MLB Tab**: Fetches live MLB game data from the MLB Stats API, displays matchups, scores, and game status. Auto-launches the MLB.com live audio feed, with retry logic for closing player modals.
- **Radio Tab**: Plays preset radio stations (ESPN, Fox, CBS Sports, 1540 AM) in a persistent browser context. Supports muting/unmuting, with special handling for ESPN’s custom volume slider.
- **Controller Support**: Navigate tabs and cycle through games/stations using a connected game controller via `pygame`.
- **Text-to-Speech**: Announces matchups, scores, and status using Google TTS and `pygame` audio playback.
- **Persistent Browser Data**: Stores user data in `~/mlb_app_data` to preserve login/session info.
- **Automatic Tab Switching**: If no active NBA/MLB games are found, automatically switches to the next available tab (MLB → Radio).

## Prerequisites

- Python 3.8 or higher
- Microsoft Edge (Chromium) installed (or adjust `channel=` in code to `chrome`)
- A modern game controller (optional)

## Setup

1. **Clone or download** this repository:
   ```bash
   git clone github	https://github.com/gleo-bahamas/StreamingSimplifier.git
   cd StreamingSimplifier
   ```

2. **Create and activate** a virtual environment:
   - macOS/Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\activate
     ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers** (first-time only):
   ```bash
   playwright install
   ```

## Usage

Run the main application:
```bash
python main.py
```

- Switch between tabs to view NBA scores, MLB scores, or listen to radio.
- Click **Next NBA Game** / **Next MLB Game** / **Next Station** buttons to cycle.
- Use a controller for hands-free navigation if connected.

## Project Structure

```
├── main.py              # Entry point with GUI, managers, and controllers
├── nba_playwright.py    # (Optional) helper for NBA browser automation
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── user_data/           # Persistent Playwright contexts
└── .venv/               # Virtual environment (optional)
```

## Troubleshooting

- **No games loaded**: Ensure your machine’s clock/timezone matches an active game window. Games are fetched based on local date.
- **Browser not launching**: Confirm Edge (Chromium) is installed or change `channel` in `launch_persistent_context` to your browser.
- **Audio issues**: Check `pygame` mixer works on your OS and your default audio device is configured.

## License

MIT License © Garnel Leo

