# StreamingSimplifier

A local desktop app that cycles through today's MLB and NBA games, announces each matchup and score out loud, and opens the game's stream (TV feed first, radio if there is no TV). Built with Python and Tkinter, with Playwright driving dedicated Microsoft Edge profiles for MLB.TV and NBA League Pass. Everything runs on your own machine; there is no cloud service, tunnel or voice-assistant hook.

---

## Features

* **One game list**: Today's MLB games first, then NBA games, each group ordered live, then final, then upcoming.
* **Favorite teams first**: Within MLB the Red Sox and Cubs come first, within NBA the Celtics and Knicks (when they play that day). Change the `FAVORITES` list in `main.py` to use your own.
* **Next Game**: A button (or any controller button) moves to the next game and announces the matchup, status and score with Google text-to-speech.
* **Current NBA scores**: For a game that has started, the score and clock come from that game's own box score, which is more up to date than the day's scoreboard file (it can lag by a minute or more). If the box score can't be fetched, the scoreboard values are used.
* **TV first, radio second**:
  * **NBA**: clicks **Watch Live** (not Resume); if that is missing it uses **Listen**.
  * **MLB**: keeps the TV feed MLB.TV loads; only if no video starts within 15 seconds does it switch to a radio (audio) feed.
* **Auto login**: Signs in to NBA.com and MLB.com for you if you have saved your logins (see below), handling whichever login step is on screen. Otherwise you sign in by hand in the browser window. Browser profiles are kept locally so a saved session can skip the login.
* **Streams open ahead of time**: Games that start within 45 minutes are opened; the previous stream is muted.
* **Controller support**: Any button press, d-pad press or clear push of a stick on a connected controller goes to the next game (via `pygame`). A stick counts once per push and small drift is ignored.
* **Rapid-press safe**: Fast double presses are ignored, and a newer game request cancels one that is still loading, so they never fight over the browser tab.
* **Self-recovering**: If Edge closes mid-game, only that league's browser is restarted and the game is retried once. Old tabs left by earlier runs are closed each time a game opens.
* **One copy only**: A second copy of the app refuses to start (it would close the first copy's browsers). Each refused launch is noted in `second_launch.log`.
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

5.  **Optional: save your logins so the app signs in for you.** If you would rather not type your passwords in the browser window, store them in Windows Credential Manager (nothing is kept in the project folder):
    1.  Press Start, type **Credential Manager** and open it.
    2.  Click **Windows Credentials**, then **Add a generic credential**.
    3.  For NBA, fill in:
        * **Internet or network address:** `StreamingSimplifier-nba`
        * **User name:** your NBA.com email
        * **Password:** your NBA.com password
    4.  Click **OK**, then repeat for MLB with the address `StreamingSimplifier-mlb` and your MLB.com login.

    The two addresses must be spelled exactly as shown. If an entry is missing, the app leaves that site alone and waits for you to sign in by hand.

    **First NBA sign-in:** NBA shows an "I'm not a robot" check the first time. Click it yourself in the browser window; afterwards the saved browser profile normally keeps you signed in. MLB works the same way, and if a site asks again later, just sign in and carry on.

---

## Usage

* **Windows**: Double-click `launch.bat`. It uses its own folder, so the project can live anywhere. If you want a hotkey, make your own AutoHotkey script that runs `launch.bat` when the app window ("NBA + MLB Cycler") is not already open.
* **Any platform**: With the virtual environment active, run `python main.py`.

On start-up the app closes any open Edge windows (so save anything open in Edge first), opens the MLB and NBA browsers, loads today's games and starts with the first one. Press **Next Game** (or a controller button) to move on.

---

## Notes

* NBA's scoreboard feed (`cdn.nba.com`) refuses plain scripts, so the app falls back to reading it from inside the NBA browser page.
* If you are never asked to log in again after the first time, the saved profile is working. If you are asked every launch, the site is not keeping a long-lived session cookie.
* **Updating**: Double-click `update.bat`. It pulls the latest code (or downloads it if the folder is not a git clone) and refreshes the libraries. It never replaces `launch.bat`.
* Console lines starting with `[DEBUG]` show each step (login, which button was clicked, which feed was chosen). Include them when reporting a problem.

---

## Project Structure

```
StreamingSimplifier/
├── main.py            # the app: game list, speech, browsers, logins
├── launch.bat         # activates the venv and runs main.py
├── update.bat         # one-click update to the latest code
├── nba_playwright.py  # older standalone NBA script (not used by main.py)
├── requirements.txt
├── CHANGELOG.MD
└── Readme.md
```
