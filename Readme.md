# StreamingSimplifier

A desktop application designed to track live NBA and MLB games and stream their associated audio broadcasts. Built with Python and Tkinter for the graphical user interface, it uses Playwright to launch and manage dedicated Chromium (Edge) browser contexts for seamless audio streaming.

---

## Features

* **NBA Tab**: Fetches live NBA game data, displaying matchups, scores, and game status. It automatically manages the NBA.com live audio feed, handling muting/unmuting upon tab switching.
* **MLB Tab**: Retrieves live MLB game data from the MLB Stats API, showing matchups, scores, and game status. It auto-launches the MLB.com live audio, including robust retry logic for dismissing player modals.
* **Radio Tab**: Plays preset radio stations (ESPN, Fox, CBS Sports, 1540 AM) within persistent browser contexts. It supports muting/unmuting, with special handling for ESPN’s custom volume slider.
* **Controller Support**: Navigate tabs and cycle through games/stations effortlessly using a connected game controller via `pygame`.
* **Text-to-Speech**: Announces matchups, scores, and status updates using Google TTS and `pygame` for audio playback.
* **Persistent Browser Data**: Stores browser user data (e.g., login, session info) locally in `user_data/` (or `~/mlb_app_data` as configured for Playwright profiles) to preserve session state.
* **Automatic Tab Switching**: If no active NBA or MLB games are found, the application intelligently switches to the next available tab (e.g., MLB → Radio).

---

## Prerequisites

* **Python 3.8** or higher
* **Microsoft Edge (Chromium)** installed (or configure the `channel` parameter in the code to `chrome` for Google Chrome support)
* A modern **game controller** (optional, for hands-free navigation)

---

## Setup

Follow these steps to get StreamingSimplifier up and running:

1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/gleo-bahamas/StreamingSimplifier.git](https://github.com/gleo-bahamas/StreamingSimplifier.git)
    cd StreamingSimplifier
    ```

2.  **Create and activate a virtual environment**:
    * **macOS/Linux**:
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        ```
    * **Windows**:
        ```powershell
        python -m venv .venv
        .\.venv\Scripts\activate
        ```

3.  **Install Python dependencies**:
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

4.  **Install Playwright browsers** (first-time only):
    ```bash
    playwright install
    ```

5.  **Create a launch script** (Windows only, recommended for easy execution):
    In your project's root directory (`StreamingSimplifier/`), create a file named `launch.bat` and paste the following content:
    ```batch
    @echo off
    REM This script activates the Python virtual environment and runs main.py

    REM Define the path to your project directory.
    REM IMPORTANT: Adjust if your project is not in 'C:\Users\admin\StreamingSimplifier'
    set "PROJECT_DIR=C:\Users\admin\StreamingSimplifier"

    REM Navigate to the project directory
    cd /d "%PROJECT_DIR%"

    REM Activate the virtual environment
    call ".\.venv\Scripts\activate.bat"

    REM Run your main Python application
    python main.py

    REM Optional: Remove 'pause' if you want the command window to close immediately
    pause
    ```
    **Note:** If you plan to launch this via AutoHotkey with the `Hide` option, you might want to remove the `pause` line from `launch.bat`.

---

## Usage

To launch the application:

* **Windows (Recommended)**: Double-click the `launch.bat` file in your project's root directory.
* **All Platforms (Manual)**:
    1.  Open your terminal.
    2.  Navigate to the `StreamingSimplifier` directory.
    3.  Activate your virtual environment (as shown in Step 2 of Setup).
    4.  Run: `python main.py`

Once launched:
* Switch between tabs to view NBA scores, MLB scores, or listen to radio stations.
* Click **Next NBA Game** / **Next MLB Game** / **Next Station** buttons to cycle through options.
* Use a connected controller for hands-free navigation.

---

## Project Structure
