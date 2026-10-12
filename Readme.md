# StreamingSimplifier

A local desktop app that cycles through today's MLB and NBA games, announces each matchup and score out loud, and opens the game's stream (TV feed first, radio if there is no TV). Built with Python and Tkinter, with Playwright driving dedicated Microsoft Edge profiles for MLB.TV and NBA League Pass. Everything runs on your own machine; there is no cloud service, tunnel or voice-assistant hook.

---

## Features

* **One game list**: Today's MLB games first, then NBA games, each group ordered live, then final, then upcoming.
* **Next Game**: A button (or any controller button) moves to the next game and announces the matchup, status and score with Google text-to-speech.
* **TV first, radio second**:
  * **NBA**: clicks **Watch Live** (not Resume); if that is missing it uses **Listen**.
  * **MLB**: keeps the TV feed MLB.TV loads; only if no video starts within 15 seconds does it switch to a radio (audio) feed.
* **Auto login**: Signs in to NBA.com and MLB.com for you, handling whichever login step is on screen. Browser profiles are kept locally so a saved session can skip the login.
* **Streams open ahead of time**: Games that start within 45 minutes are opened; the previous stream is muted.
* **Controller support**: Any button, stick or hat press on a connected controller goes to the next game (via `pygame`).
* **Rapid-press safe**: Fast double presses are ignored and only one game loads at a time.
* **Temporary speech files**: Each spoken clip is deleted right after it plays, leftovers are swept on startup, and the folder is removed on exit.

---

## Prerequisites

* **Python 3.8** or higher
* **Microsoft Edge** installed (or change the `channel` in `StreamManager.start` to `chrome`)
* Accounts for **NBA League Pass** and **MLB.TV**
* A game controller (optional)

---

## Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/gleo-bahamas/StreamingSimplifier.git
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

3.  **Install dependencies**:
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

4.  **Install Playwright browsers** (first time only):
    ```bash
    playwright install
    ```

---

## Usage

* **Windows**: Double-click `launch.bat`, or install [AutoHotkey v1](https://www.autohotkey.com/) and run `Launch.ahk`. Press **F2** to start the app, or to bring it forward if it is already running. Both scripts use their own folder, so the project can live anywhere.
* **Any platform**: With the virtual environment active, run `python main.py`.

On start-up the app closes any open Edge windows, opens the MLB and NBA browsers, loads today's games and starts with the first one. Press **Next Game** (or a controller button) to move on.

---

## Notes

* NBA's scoreboard feed (`cdn.nba.com`) refuses plain scripts, so the app falls back to reading it from inside the NBA browser page.
* If you are never asked to log in again after the first time, the saved profile is working. If you are asked every launch, the site is not keeping a long-lived session cookie.
* Console lines starting with `[DEBUG]` show each step (login, which button was clicked, which feed was chosen). Include them when reporting a problem.

---

## Project Structure

```
StreamingSimplifier/
├── main.py            # the app: game list, speech, browsers, logins
├── launch.bat         # activates the venv and runs main.py
├── Launch.ahk         # F2 hotkey to start or focus the app
├── nba_playwright.py  # older standalone NBA script (not used by main.py)
├── requirements.txt
├── CHANGELOG.MD
└── Readme.md
```
