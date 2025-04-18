import asyncio
import json
import tkinter as tk
from tkinter import messagebox, ttk
import aiohttp
import webbrowser
from playwright.async_api import async_playwright
import os
import threading
import psutil
from gtts import gTTS
import pygame
import time
from datetime import datetime, timedelta
from pathlib import Path

# Set up an absolute base directory for persistent browser data
BASE_USER_DATA_DIR = str(Path(os.path.expanduser("~")) / "mlb_app_data")
os.makedirs(BASE_USER_DATA_DIR, exist_ok=True)
PROJECT_DIR = Path(__file__).parent

def playSound(text):
    # Convert text to speech and play the audio
    tts = gTTS(text=text, lang='en')
    filename = PROJECT_DIR / "speech.mp3"
    tts.save(str(filename))
    pygame.mixer.init()
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.2)
    pygame.mixer.music.stop()
    pygame.mixer.quit()


def kill_edge():
    """Closes all Microsoft Edge (msedge) processes."""
    for proc in psutil.process_iter(attrs=['pid', 'name']):
        if proc.info['name'] and "msedge" in proc.info['name'].lower():
            try:
                psutil.Process(proc.info['pid']).terminate()
                print(f"Closed Edge process {proc.info['pid']}")
            except psutil.NoSuchProcess:
                pass


# Simple helper event class to simulate a tab selection event
class SimpleEvent:
    def __init__(self, widget):
        self.widget = widget


# ---------------- Radio Manager ----------------
class RadioContextManager:
    def __init__(self):
        self.browser_context = None
        self.page = None
        self.radio_links = [
            {"name": "ESPN Radio", "url": "https://radiostationusa.fm/online/espn-radio"},
            {"name": "Fox Radio", "url": "https://tunein.com/radio/Fox-981-1230-and-kwsncom-s26371/"},
            {"name": "CBS Sports Radio", "url": "https://tunein.com/radio/CBS-Sports-Radio-p502769/"},
            {"name": "1540 AM", "url": "https://tunein.com/radio/1540-AM-s44834/"}
        ]
        self.current_station_index = 0
        self.browser_ready_event = asyncio.Event()
        self.playwright = None
        self.user_data_dir = str(Path(BASE_USER_DATA_DIR) / "radio")
        os.makedirs(self.user_data_dir, exist_ok=True)

    async def start_browser(self):
        self.playwright = await async_playwright().start()
        self.browser_context = await self.playwright.chromium.launch_persistent_context(
            self.user_data_dir, channel="msedge", headless=False
        )
        print("Radio browser started with persistent context")
        await asyncio.sleep(2)
        self.browser_ready_event.set()
        await self.load_station()

    async def load_station(self):
        await self.browser_ready_event.wait()
        if self.page:
            await self.page.close()
            print("Closed previous radio tab")
        station = self.radio_links[self.current_station_index]
        self.page = await self.browser_context.new_page()
        await self.page.goto(station["url"])
        print(f"Opened {station['name']} page: {station['url']}")
        try:
            if station["name"] == "ESPN Radio":
                await self.page.wait_for_selector('#radio-stream .btn.btn-primary', state='visible')
                await self.page.locator('#radio-stream .btn.btn-primary').click()
                print("Clicked play button for ESPN Radio")
            elif station["name"] == "Fox Radio":
                try:
                    close_button = await self.page.wait_for_selector(
                        'button.close-button-module__button___nu_np', state='visible', timeout=3000)
                    if close_button:
                        await close_button.click()
                        print("Closed prompt for Fox Radio")
                except Exception:
                    print("No prompt to close for Fox Radio.")
                await self.page.wait_for_selector('div.playButton-module__playButtonWrapper___G_wDs',
                                                  state='visible', timeout=10000)
                await self.page.locator('div.playButton-module__playButtonWrapper___G_wDs').click()
                print("Clicked play button for Fox Radio")
            elif station["name"] == "CBS Sports Radio":
                try:
                    close_button = await self.page.wait_for_selector(
                        'button.close-button-module__button___nu_np', state='visible', timeout=3000)
                    if close_button:
                        await close_button.click()
                        print("Closed prompt for CBS Sports Radio")
                except Exception:
                    print("No prompt to close for CBS Sports Radio.")
                await self.page.wait_for_selector('a[href*="CBS-Sports-Radio-p502769"]',
                                                  state='visible', timeout=10000)
                await self.page.locator('a[href*="CBS-Sports-Radio-p502769"]').click()
                print("Clicked play button for CBS Sports Radio")
            elif station["name"] == "1540 AM":
                try:
                    close_button = await self.page.wait_for_selector(
                        'button.close-button-module__button___nu_np', state='visible', timeout=3000)
                    if close_button:
                        await close_button.click()
                        print("Closed prompt for 1540 AM")
                except Exception:
                    print("No prompt to close for 1540 AM.")
                await self.page.wait_for_selector('div.playButton-module__playButtonWrapper___G_wDs',
                                                  state='visible', timeout=10000)
                await self.page.locator('div.playButton-module__playButtonWrapper___G_wDs').click()
                print("Clicked play button for 1540 AM")
        except Exception as e:
            print(f"Error playing {station['name']}: {e}")

    async def next_station(self):
        self.current_station_index = (self.current_station_index + 1) % len(self.radio_links)
        await self.load_station()

    async def mute_page(self):
        if self.page:
            # Special handling for ESPN Radio with a volume slider.
            if self.radio_links[self.current_station_index]["name"] == "ESPN Radio":
                await self.page.evaluate("""
                    () => {
                        const rangeInput = document.querySelector('input.custom-range');
                        if (rangeInput) {
                            rangeInput.value = 0;
                            const event = new Event('input', { bubbles: true });
                            rangeInput.dispatchEvent(event);
                        }
                    }
                """)
                print("ESPN Radio volume set to 0 (muted).")
            else:
                muted_count = await self.page.evaluate(
                    "() => { const media = document.querySelectorAll('audio, video, iframe'); "
                    "media.forEach(el => { try { el.muted = true } catch(e){} }); return media.length; }"
                )
                print(f"Radio page muted; {muted_count} media elements found.")

    async def unmute_page(self):
        if self.page:
            if self.radio_links[self.current_station_index]["name"] == "ESPN Radio":
                await self.page.evaluate("""
                    () => {
                        const rangeInput = document.querySelector('input.custom-range');
                        if (rangeInput) {
                            rangeInput.value = 0.8;
                            const event = new Event('input', { bubbles: true });
                            rangeInput.dispatchEvent(event);
                        }
                    }
                """)
                print("ESPN Radio volume set to 0.8 (unmuted).")
            else:
                unmuted_count = await self.page.evaluate(
                    "() => { const media = document.querySelectorAll('audio, video, iframe'); "
                    "media.forEach(el => { try { el.muted = false } catch(e){} }); return media.length; }"
                )
                print(f"Radio page unmuted; {unmuted_count} media elements found.")


# ---------------- NBA Manager ----------------
class NBAContextManager:
    def __init__(self):
        self.browser_context = None
        self.game_page = None
        self.playwright = None
        self.user_data_dir = str(Path(BASE_USER_DATA_DIR) / "nba")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.browser_ready_event = asyncio.Event()

    async def start_browser(self):
        self.playwright = await async_playwright().start()
        self.browser_context = await self.playwright.chromium.launch_persistent_context(
            self.user_data_dir, channel="msedge", headless=False
        )
        print("NBA Browser started with persistent context")
        await asyncio.sleep(2)
        self.browser_ready_event.set()

    async def open_game_page(self, game_url):
        await self.browser_ready_event.wait()
        if self.game_page:
            await self.game_page.close()
            print("Closed previous game tab")
        self.game_page = await self.browser_context.new_page()
        await self.game_page.goto(game_url)
        print(f"Opened game page: {game_url}")
        try:
            await self.game_page.wait_for_selector('button:text("Listen")', timeout=15000)
            await self.game_page.locator('button:text("Listen")').click()
            print("Clicked 'Listen' button on game page")
        except Exception as e:
            print(f"Error interacting with game page: {e}")

    async def mute_page(self):
        if self.game_page:
            count = await self.game_page.evaluate(
                "() => { const m = document.querySelectorAll('audio, video'); m.forEach(el => el.muted = true); return m.length; }"
            )
            print(f"NBA page muted; {count} media elements found.")

    async def unmute_page(self):
        if self.game_page:
            count = await self.game_page.evaluate(
                "() => { const m = document.querySelectorAll('audio, video'); m.forEach(el => el.muted = false); return m.length; }"
            )
            print(f"NBA page unmuted; {count} media elements found.")


# ---------------- Revised MLB Manager ----------------
class MLBContextManager:
    def __init__(self):
        self.browser_context = None
        self.game_page = None
        self.playwright = None
        self.user_data_dir = str(Path(BASE_USER_DATA_DIR) / "mlb")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.browser_ready_event = asyncio.Event()

    async def start_browser(self):
        self.playwright = await async_playwright().start()
        self.browser_context = await self.playwright.chromium.launch_persistent_context(
            self.user_data_dir, channel="msedge", headless=False
        )
        print("MLB Browser started with persistent context")
        await asyncio.sleep(2)
        self.browser_ready_event.set()

    async def open_game_page(self, game_url):
        await self.browser_ready_event.wait()
        if self.game_page:
            await self.game_page.close()
            print("Closed previous MLB game tab")
        self.game_page = await self.browser_context.new_page()
        await self.game_page.goto(game_url)
        print(f"Opened MLB game page: {game_url}")
        # Retry closing the modal up to 3 times if present.
        max_retries = 3
        for attempt in range(max_retries):
            try:
                close_button = await self.game_page.wait_for_selector(
                    'button.modal-close-btn', state='visible', timeout=5000)
                if close_button:
                    await close_button.click()
                    print(f"Attempt {attempt+1}: Clicked modal close button on MLB page.")
                    await asyncio.sleep(1)
                    try:
                        await self.game_page.wait_for_selector(
                            'button.modal-close-btn', state='hidden', timeout=5000)
                        print("Modal is now hidden.")
                        break
                    except Exception:
                        print(f"Attempt {attempt+1}: Modal still visible after click, retrying...")
                else:
                    print("No modal close button found.")
                    break
            except Exception as e:
                print(f"Attempt {attempt+1}: No modal found or error closing it: {e}")
                break
        # Optionally, check for the audio feed list.
        try:
            await self.game_page.wait_for_selector("ul.style__StyledRadioOptsList-sc-1pgcv8d-1",
                                                     state="visible", timeout=5000)
            print("Audio feed list appeared.")
        except Exception as e:
            print("Audio feed list not found; continuing without it.")

    async def cycle_audio_feed(self):
        try:
            all_buttons = await self.game_page.query_selector_all(
                "ul.style__StyledRadioOptsList-sc-1pgcv8d-1 li button"
            )
            feed_buttons = []
            for button in all_buttons:
                aria_label = await button.get_attribute("aria-label")
                if aria_label and aria_label.startswith("AUDIO -") and await button.is_enabled():
                    feed_buttons.append(button)
            if not feed_buttons:
                print("No enabled audio feed buttons found. Attempting to reload streams...")
                try:
                    broadcast_button = await self.game_page.wait_for_selector(
                        "button.broadcast-control", state="visible", timeout=5000)
                    if broadcast_button:
                        await broadcast_button.click()
                        print("Re-clicked Broadcast selector to reload streams.")
                        await asyncio.sleep(2)
                        all_buttons = await self.game_page.query_selector_all(
                            "ul.style__StyledRadioOptsList-sc-1pgcv8d-1 li button"
                        )
                        for button in all_buttons:
                            aria_label = await button.get_attribute("aria-label")
                            if aria_label and aria_label.startswith("AUDIO -") and await button.is_enabled():
                                feed_buttons.append(button)
                    else:
                        print("Broadcast selector button not found during reload attempt.")
                except Exception as e:
                    print("Error re-loading streams:", e)
            if feed_buttons:
                active_index = None
                for i, button in enumerate(feed_buttons):
                    aria_checked = await button.get_attribute("aria-checked")
                    feed_text = await button.inner_text()
                    print(f"[Cycle] Feed index {i}: {feed_text}, aria-checked: {aria_checked}")
                    if aria_checked == "true":
                        active_index = i
                if active_index is None:
                    active_index = -1
                next_index = (active_index + 1) % len(feed_buttons)
                current_feed = "None"
                if active_index >= 0:
                    current_feed = await feed_buttons[active_index].inner_text()
                next_feed = await feed_buttons[next_index].inner_text()
                print(f"[Cycle] Currently active feed: {current_feed}")
                print(f"[Cycle] Switching to feed index {next_index}: {next_feed}")
                await feed_buttons[next_index].click()
            else:
                print("No valid audio feed buttons found after reload attempt.")
        except Exception as e:
            print("Error cycling audio feeds:", e)

    async def mute_page(self):
        if self.game_page:
            count = await self.game_page.evaluate(
                "() => { const media = document.querySelectorAll('audio, video, iframe'); "
                "media.forEach(el => { try { el.muted = true } catch(e){} }); return media.length; }"
            )
            print(f"MLB page muted; {count} media elements found.")

    async def unmute_page(self):
        if self.game_page:
            count = await self.game_page.evaluate(
                "() => { const media = document.querySelectorAll('audio, video, iframe'); "
                "media.forEach(el => { try { el.muted = false } catch(e){} }); return media.length; }"
            )
            print(f"MLB page unmuted; {count} media elements found.")


# ---------------- Main Application (NBA & MLB Live Game Tracker) ----------------
class NBAGameTracker:
    def __init__(self, root):
        notebook = ttk.Notebook(root)
        notebook.pack(expand=True, fill="both")
        self.notebook = notebook  # For tab switching
        self.current_tab_index = 0

        # Create frames for each tab
        nba_tab = ttk.Frame(notebook)
        mlb_tab = ttk.Frame(notebook)
        radio_tab = ttk.Frame(notebook)

        notebook.add(nba_tab, text="NBA")
        notebook.add(mlb_tab, text="MLB")
        notebook.add(radio_tab, text="Radio")

        self.nba_tab = nba_tab
        self.mlb_tab = mlb_tab
        self.radio_tab = radio_tab
        self.root = root
        self.root.title("NBA & MLB Live Game Tracker")
        self.radio_manager = RadioContextManager()
        self.nba_manager = NBAContextManager()
        self.mlb_manager = MLBContextManager()
        self.radio_browser_started = False
        self.mlb_browser_started = False

        # NBA Widgets
        self.game_info_label = tk.Label(nba_tab, text="Loading NBA game data...", font=("Arial", 16))
        self.game_info_label.pack(pady=10)
        self.score_label = tk.Label(nba_tab, text="", font=("Arial", 14))
        self.score_label.pack(pady=5)
        self.next_button = tk.Button(nba_tab, text="Next NBA Game", command=self.load_next_game)
        self.next_button.pack(pady=10)

        # MLB Widgets
        self.mlb_game_info_label = tk.Label(mlb_tab, text="Loading MLB game data...", font=("Arial", 16))
        self.mlb_game_info_label.pack(pady=10)
        self.mlb_score_label = tk.Label(mlb_tab, text="", font=("Arial", 14))
        self.mlb_score_label.pack(pady=5)
        self.mlb_next_button = tk.Button(mlb_tab, text="Next MLB Game", command=self.load_next_mlb_game)
        self.mlb_next_button.pack(pady=10)
        self.mlb_cycle_audio_button = tk.Button(mlb_tab, text="Cycle Audio Feed", command=self.cycle_mlb_audio)
        self.mlb_cycle_audio_button.pack(pady=10)

        # Radio Widgets
        tk.Label(radio_tab, text="Radio Tab Content", font=("Arial", 16)).pack(pady=20)
        self.radio_label = tk.Label(radio_tab, text="Current Station: None", font=("Arial", 14))
        self.radio_label.pack(pady=10)
        self.next_station_button = tk.Button(radio_tab, text="Next Station", command=self.load_next_station)
        self.next_station_button.pack(pady=10)

        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.run_event_loop, daemon=True).start()
        notebook.bind("<<NotebookTabChanged>>", self.on_tab_selected)
        # Trigger initial tab selection using a simple event.
       # self.on_tab_selected(SimpleEvent(notebook))

        # MLB game data will be managed in this class.
        self.mlb_games = []
        self.current_mlb_game_index = 0

    def load_next_station(self):
        if not self.radio_manager.browser_context:
            future = asyncio.run_coroutine_threadsafe(self.radio_manager.start_browser(), self.loop)
            try:
                future.result(timeout=10)
            except Exception as e:
                print("Error starting Radio browser:", e)
        future = asyncio.run_coroutine_threadsafe(self.radio_manager.next_station(), self.loop)
        try:
            future.result(timeout=10)
        except Exception as e:
            print("Error switching radio station:", e)
        station = self.radio_manager.radio_links[self.radio_manager.current_station_index]
        self.radio_label.config(text=f"Current Station: {station['name']}")

    def on_tab_selected(self, event):
        new_tab_index = event.widget.index(event.widget.select())
        # Mute previous tab's page.
        if self.current_tab_index != new_tab_index:
            if self.current_tab_index == 0:
                asyncio.run_coroutine_threadsafe(self.nba_manager.mute_page(), self.loop)
            elif self.current_tab_index == 1:
                asyncio.run_coroutine_threadsafe(self.mlb_manager.mute_page(), self.loop)
            elif self.current_tab_index == 2:
                asyncio.run_coroutine_threadsafe(self.radio_manager.mute_page(), self.loop)
        self.current_tab_index = new_tab_index
        # Unmute new tab's page and load content as needed.
        if new_tab_index == 0:
            asyncio.run_coroutine_threadsafe(self.nba_manager.unmute_page(), self.loop)
            print("NBA tab selected. Starting NBA browser and fetching NBA game data...")
            asyncio.run_coroutine_threadsafe(self.nba_manager.start_browser(), self.loop)
            asyncio.run_coroutine_threadsafe(self.wait_and_fetch_games(), self.loop)
        elif new_tab_index == 1:
            asyncio.run_coroutine_threadsafe(self.mlb_manager.unmute_page(), self.loop)
            self.mlb_browser_started = True
            print("MLB tab selected. Starting MLB browser and fetching MLB game data...")
            asyncio.run_coroutine_threadsafe(self.mlb_manager.start_browser(), self.loop)
            asyncio.run_coroutine_threadsafe(self.wait_and_fetch_mlb_games(), self.loop)
        elif new_tab_index == 2:
            asyncio.run_coroutine_threadsafe(self.radio_manager.unmute_page(), self.loop)
            self.radio_browser_started = True
            print("Radio tab selected. Starting Radio browser...")
            asyncio.run_coroutine_threadsafe(self.radio_manager.start_browser(), self.loop)
            station = self.radio_manager.radio_links[self.radio_manager.current_station_index]
            self.radio_label.config(text=f"Current Station: {station['name']}")

    def run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def wait_and_fetch_games(self):
        await self.nba_manager.browser_ready_event.wait()
        print("NBA Browser is ready. Fetching NBA game data...")
        await self.fetch_games()

    async def fetch_games(self):
        url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.text()
                        self.process_game_data(json.loads(data))
                    else:
                        messagebox.showerror("Error", "Failed to fetch NBA game data.")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {e}")

    def process_game_data(self, data):
        self.games = [game for game in data['scoreboard']['games'] if game['gameStatus'] == 2]
        if not self.games:
            self.game_info_label.config(text="No active NBA games.")
            playSound("No active NBA games, switching to MLB")
            # ← jump to MLB
            self.root.after(0, lambda: self.notebook.select(1))
            return
        self.current_game_index = 0
        self.display_game_info()

    def display_game_info(self):
        if not self.games:
            return
        game = self.games[self.current_game_index]
        home = game['homeTeam']
        away = game['awayTeam']
        matchup = f"{away['teamCity']} {away['teamName']} at {home['teamCity']} {home['teamName']}"
        self.game_info_label.config(text=matchup)
        game_status_text = self.parse_game_status(game.get('gameStatusText'))
        score_info = self.get_score_info(home, away)
        self.score_label.config(text=f"{game_status_text}\n{score_info}")
        playSound(matchup)
        playSound(game_status_text)
        playSound(score_info)

        game_url = f"https://www.nba.com/game/{away['teamTricode']}-vs-{home['teamTricode']}-{game['gameId']}?watch"

        #kill_edge()  # Kill any existing Edge processes.
#        future = asyncio.run_coroutine_threadsafe(self.nba_manager.start_browser(), self.loop)
#        try:
#            future.result(timeout=10)
#        except Exception as e:
#            print("Error starting NBA browser:", e)
#        asyncio.run_coroutine_threadsafe(self.nba_manager.open_game_page(game_url), self.loop)


        if self.nba_manager.game_page:
            future = asyncio.run_coroutine_threadsafe(self.nba_manager.game_page.close(), self.loop)
            try:
                future.result(timeout=5)
                print("Closed previous NBA game tab")
            except Exception as e:
                print("Error closing NBA game page:", e)
        if not self.nba_manager.browser_context:
            future = asyncio.run_coroutine_threadsafe(self.nba_manager.start_browser(), self.loop)
            try:
                future.result(timeout=10)
            except Exception as e:
                print("Error starting NBA browser:", e)
        asyncio.run_coroutine_threadsafe(self.nba_manager.open_game_page(game_url), self.loop)


    def load_next_game(self):
        if not self.games:
            return
        self.current_game_index = (self.current_game_index + 1) % len(self.games)
        self.display_game_info()

    def load_next_mlb_game(self):
        if not self.mlb_games:
            return
        self.current_mlb_game_index = (self.current_mlb_game_index + 1) % len(self.mlb_games)
        self.display_mlb_game_info()

    def display_mlb_game_info(self):
        if not self.mlb_games:
            return
        game = self.mlb_games[self.current_mlb_game_index]
        away = game["teams"]["away"]
        home = game["teams"]["home"]
        matchup = f"{away['team']['name']} at {home['team']['name']}"
        self.mlb_game_info_label.config(text=matchup)
        status_text = self.parse_mlb_game_status(game["status"]["detailedState"])
        score_info = self.get_mlb_score_info(home, away)
        self.mlb_score_label.config(text=f"{status_text}\n{score_info}")
        playSound(matchup)
        playSound(status_text)
        playSound(score_info)
        game_url = f"https://www.mlb.com/tv/g{game['gamePk']}"
        if self.mlb_manager.game_page:
            future = asyncio.run_coroutine_threadsafe(self.mlb_manager.game_page.close(), self.loop)
            try:
                future.result(timeout=5)
                print("Closed previous MLB game tab")
            except Exception as e:
                print("Error closing MLB game page:", e)
        if not self.mlb_manager.browser_context:
            future = asyncio.run_coroutine_threadsafe(self.mlb_manager.start_browser(), self.loop)
            try:
                future.result(timeout=10)
            except Exception as e:
                print("Error starting MLB browser:", e)
        asyncio.run_coroutine_threadsafe(self.mlb_manager.open_game_page(game_url), self.loop)

    def cycle_mlb_audio(self):
        asyncio.run_coroutine_threadsafe(self.mlb_manager.cycle_audio_feed(), self.loop)

    @staticmethod
    def parse_game_status(status_text):
        if not status_text or not isinstance(status_text, str):
            return "Status not available"
        status_text = status_text.strip()
        if status_text.lower().startswith("end of"):
            quarter_text = {
                "1st Qtr": "1st Quarter",
                "2nd Qtr": "2nd Quarter",
                "3rd Qtr": "3rd Quarter",
                "4th Qtr": "4th Quarter"
            }
            quarter = status_text.split("of")[-1].strip()
            return f"The End of the {quarter_text.get(quarter, quarter)}"
        if "Qtr" in status_text:
            quarter_map = {
                "1st Qtr": "1st Quarter",
                "2nd Qtr": "2nd Quarter",
                "3rd Qtr": "3rd Quarter",
                "4th Qtr": "4th Quarter"
            }
            return quarter_map.get(status_text, status_text)
        if status_text.startswith("Q"):
            parts = status_text.split()
            if len(parts) == 2:
                quarter, time_left = parts
                quarter_text = {
                    "Q1": "1st Quarter",
                    "Q2": "2nd Quarter",
                    "Q3": "3rd Quarter",
                    "Q4": "4th Quarter"
                }.get(quarter, quarter)
                return f"{time_left} to go in the {quarter_text}"
        elif status_text == "Half":
            return "Half Time"
        elif status_text.startswith("END"):
            parts = status_text.split()
            if len(parts) > 1:
                quarter = parts[1]
                quarter_text = {
                    "Q1": "1st Quarter",
                    "Q2": "2nd Quarter",
                    "Q3": "3rd Quarter",
                    "Q4": "4th Quarter"
                }.get(quarter, quarter)
                return f"The End of the {quarter_text}"
        else:
            return status_text

    @staticmethod
    def get_score_info(home, away):
        if home['score'] >= away['score']:
            return f"The {home['teamName']} {home['score']} The {away['teamName']} {away['score']}"
        elif away['score'] > home['score']:
            return f"The {away['teamName']} {away['score']} The {home['teamName']} {home['score']}"
        else:
            return f"The {home['teamName']} {home['score']} The {away['teamName']} {away['score']}"

    @staticmethod
    def get_mlb_score_info(home, away):
        if home.get('score', 0) >= away.get('score', 0):
            leading_team = home['team']['name']
            trailing_team = away['team']['name']
            leading_score = home.get('score', 0)
            trailing_score = away.get('score', 0)
        elif away.get('score', 0) > home.get('score', 0):
            leading_team = away['team']['name']
            trailing_team = home['team']['name']
            leading_score = away.get('score', 0)
            trailing_score = home.get('score', 0)
        else:
            leading_team = home['team']['name']
            trailing_team = away['team']['name']
            leading_score = home.get('score', 0)
            trailing_score = away.get('score', 0)
        return f"The {leading_team} {leading_score} The {trailing_team} {trailing_score}"

    async def wait_and_fetch_mlb_games(self):
        await self.mlb_manager.browser_ready_event.wait()
        print("MLB Browser is ready. Fetching MLB game data...")
        await self.fetch_mlb_games()

    async def fetch_mlb_games(self):
        today_date = datetime.now()
        today_str = today_date.strftime('%Y-%m-%d')
        yesterday_str = (today_date - timedelta(days=1)).strftime('%Y-%m-%d')
        urls = [
            f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={yesterday_str}",
            f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today_str}"
        ]
        mlb_games_combined = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get("dates"):
                                for date_info in data["dates"]:
                                    mlb_games_combined.extend(date_info.get("games", []))
                        else:
                            print(f"Failed to fetch MLB game data for URL: {url}")
                except Exception as e:
                    print(f"An error occurred while fetching MLB data: {e}")
        self.process_mlb_game_data({"games": mlb_games_combined})

    def process_mlb_game_data(self, data):
        games = data.get("games", [])
        if not games:
            message = "No MLB games today. Switching to Radio tab."
            self.mlb_game_info_label.config(text=message)
            playSound(message)
            self.root.after(0, lambda: self.notebook.select(2))
            return
        self.mlb_games = [game for game in games if game["status"]["abstractGameState"] == "Live"]
        if not self.mlb_games:
            message = "No active MLB games right now. Switching to Radio."
            self.mlb_game_info_label.config(text=message)
            playSound(message)
            self.root.after(0, lambda: self.notebook.select(2))
            return
        self.current_mlb_game_index = 0
        self.display_mlb_game_info()

    def display_mlb_game_info(self):
        if not self.mlb_games:
            return
        game = self.mlb_games[self.current_mlb_game_index]
        away = game["teams"]["away"]
        home = game["teams"]["home"]
        matchup = f"{away['team']['name']} at {home['team']['name']}"
        self.mlb_game_info_label.config(text=matchup)
        status_text = self.parse_mlb_game_status(game["status"]["detailedState"])
        score_info = self.get_mlb_score_info(home, away)
        self.mlb_score_label.config(text=f"{status_text}\n{score_info}")
        playSound(matchup)
        playSound(status_text)
        playSound(score_info)
        game_url = f"https://www.mlb.com/tv/g{game['gamePk']}"
        if self.mlb_manager.game_page:
            future = asyncio.run_coroutine_threadsafe(self.mlb_manager.game_page.close(), self.loop)
            try:
                future.result(timeout=5)
                print("Closed previous MLB game tab")
            except Exception as e:
                print("Error closing MLB game page:", e)
        if not self.mlb_manager.browser_context:
            future = asyncio.run_coroutine_threadsafe(self.mlb_manager.start_browser(), self.loop)
            try:
                future.result(timeout=10)
            except Exception as e:
                print("Error starting MLB browser:", e)
        asyncio.run_coroutine_threadsafe(self.mlb_manager.open_game_page(game_url), self.loop)

    def load_next_mlb_game(self):
        if not self.mlb_games:
            return
        self.current_mlb_game_index = (self.current_mlb_game_index + 1) % len(self.mlb_games)
        self.display_mlb_game_info()

    def cycle_mlb_audio(self):
        asyncio.run_coroutine_threadsafe(self.mlb_manager.cycle_audio_feed(), self.loop)

    @staticmethod
    def parse_mlb_game_status(status_text):
        if not status_text or not isinstance(status_text, str):
            return "Status not available"
        return status_text.strip()

    @staticmethod
    def get_mlb_score_info(home, away):
        if home.get('score', 0) >= away.get('score', 0):
            leading_team = home['team']['name']
            trailing_team = away['team']['name']
            leading_score = home.get('score', 0)
            trailing_score = away.get('score', 0)
        elif away.get('score', 0) > home.get('score', 0):
            leading_team = away['team']['name']
            trailing_team = home['team']['name']
            leading_score = away.get('score', 0)
            trailing_score = home.get('score', 0)
        else:
            leading_team = home['team']['name']
            trailing_team = away['team']['name']
            leading_score = home.get('score', 0)
            trailing_score = away.get('score', 0)
        return f"The {leading_team} {leading_score} The {trailing_team} {trailing_score}"

    async def wait_and_fetch_mlb_games(self):
        await self.mlb_manager.browser_ready_event.wait()
        print("MLB Browser is ready. Fetching MLB game data...")
        await self.fetch_mlb_games()

    async def fetch_mlb_games(self):
        today_date = datetime.now()
        today_str = today_date.strftime('%Y-%m-%d')
        yesterday_str = (today_date - timedelta(days=1)).strftime('%Y-%m-%d')
        urls = [
            f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={yesterday_str}",
            f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today_str}"
        ]
        mlb_games_combined = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get("dates"):
                                for date_info in data["dates"]:
                                    mlb_games_combined.extend(date_info.get("games", []))
                        else:
                            print(f"Failed to fetch MLB game data for URL: {url}")
                except Exception as e:
                    print(f"An error occurred while fetching MLB data: {e}")
        self.process_mlb_game_data({"games": mlb_games_combined})

    def process_mlb_game_data(self, data):
        games = data.get("games", [])
        if not games:
            message = "No MLB games today. Switching to Radio tab."
            self.mlb_game_info_label.config(text=message)
            playSound(message)
            self.root.after(0, lambda: self.notebook.select(2))
            return
        self.mlb_games = [game for game in games if game["status"]["abstractGameState"] == "Live"]
        if not self.mlb_games:
            message = "No active MLB games right now. Switching to Radio tab."
            self.mlb_game_info_label.config(text=message)
            playSound(message)
            self.root.after(0, lambda: self.notebook.select(2))
            return
        self.current_mlb_game_index = 0
        self.display_mlb_game_info()


def controller_loop(app):
    """
    Controller loop with new mapping:
      - Next Tab: Button 4 or Axis 4
      - Previous Tab: Button 8 or Button 9
      - Next Game: Button 2,5,3,0,1 or Axis 5
      - Cycle Audio Feed (MLB only): Axis 0
    """
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("No controller found!")
        return
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print("Controller initialized:", joystick.get_name())

    last_axis0_value = 0.0
    threshold = 0.9

    while True:
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == 4:
                    current = app.notebook.index(app.notebook.select())
                    next_index = (current + 1) % app.notebook.index("end")
                    print("[DEBUG] JOYBUTTONDOWN: Button 4 -> Next Tab")
                    app.root.after(0, lambda idx=next_index: app.notebook.select(idx))
                elif event.button in [8, 9]:
                    current = app.notebook.index(app.notebook.select())
                    prev_index = (current - 1) % app.notebook.index("end")
                    print(f"[DEBUG] JOYBUTTONDOWN: Button {event.button} -> Previous Tab")
                    app.root.after(0, lambda idx=prev_index: app.notebook.select(idx))
                elif event.button in [2, 5, 3, 0, 1]:
                    print(f"[DEBUG] JOYBUTTONDOWN: Button {event.button} -> Next Game")
                    current = app.notebook.index(app.notebook.select())
                    if current == 0:
                        app.root.after(0, app.load_next_game)
            elif event.type == pygame.JOYAXISMOTION:
                if event.axis == 0 and abs(event.value) >= threshold:
                    current = app.notebook.index(app.notebook.select())
                    next_index = (current + 1) % app.notebook.index("end")
                    print("[DEBUG] JOYAXISMOTION: Axis 0 -> Next Tab")
                    app.root.after(0, lambda idx=next_index: app.notebook.select(idx))
                elif event.axis == 5 and abs(event.value) >= threshold:
                    print("[DEBUG] JOYAXISMOTION: Axis 5 -> Next Game")
                    current = app.notebook.index(app.notebook.select())
                    if current == 0:
                        app.root.after(0, app.load_next_game)
            elif event.type == pygame.JOYHATMOTION:
                hat = event.value
                if hat[0] == 1:
                    current = app.notebook.index(app.notebook.select())
                    next_index = (current + 1) % app.notebook.index("end")
                    print("[DEBUG] JOYHATMOTION: D-pad Right -> Next Tab")
                    app.root.after(0, lambda idx=next_index: app.notebook.select(idx))
                elif hat[0] == -1:
                    current = app.notebook.index(app.notebook.select())
                    prev_index = (current - 1) % app.notebook.index("end")
                    print("[DEBUG] JOYHATMOTION: D-pad Left -> Previous Tab")
                    app.root.after(0, lambda idx=prev_index: app.notebook.select(idx))
        time.sleep(0.01)


if __name__ == "__main__":
    kill_edge()
    root = tk.Tk()
    app = NBAGameTracker(root)
    controller_thread = threading.Thread(target=controller_loop, args=(app,), daemon=True)
    controller_thread.start()
    root.mainloop()
