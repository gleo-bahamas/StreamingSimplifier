import asyncio
import json
import tkinter as tk
from tkinter import ttk
import aiohttp
from playwright.async_api import async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import threading
import psutil
from gtts import gTTS
import pygame
import time
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import atexit
import shutil

BASE_DIR    = Path.home() / "mlb_app_data"
BASE_DIR.mkdir(exist_ok=True)
PROJECT_DIR = Path(__file__).parent
SPEECH_DIR  = PROJECT_DIR / "speech_mp3s"
SPEECH_DIR.mkdir(exist_ok=True)

# Clear out any leftovers from prior runs
for old in SPEECH_DIR.glob("speech_*.mp3"):
    try:
        old.unlink()
    except:
        pass

# Register end-of-program cleanup
atexit.register(lambda: shutil.rmtree(SPEECH_DIR, ignore_errors=True))


def controller_loop(app):
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("No controller found!")
        return
    js = pygame.joystick.Joystick(0)
    js.init()
    print("Controller initialized:", js.get_name())

    while True:
        for ev in pygame.event.get():
            # any button press, any axis movement, any hat motion → next game
            if ev.type == pygame.JOYBUTTONDOWN \
                    or ev.type == pygame.JOYAXISMOTION \
                    or ev.type == pygame.JOYHATMOTION:
                app.root.after(0, app.next_game)
        time.sleep(0.01)


def dbg(*args, **kwargs):
    print("[DEBUG]", *args, **kwargs)

def parse_nba_status(raw: str) -> str:
    raw = (raw or "").strip()
    if raw.lower().startswith("end of"):
        parts = raw.split()
        if len(parts) >= 3:
            num = parts[-2]
            qm = {"1st":"1st quarter","2nd":"2nd quarter",
                  "3rd":"3rd quarter","4th":"4th quarter"}
            return f"End of the {qm.get(num,num)}"
        return raw
    if raw.startswith("Q") and " " in raw:
        q, tm = raw.split(" ",1)
        qm = {"Q1":"1st quarter","Q2":"2nd quarter",
              "Q3":"3rd quarter","Q4":"4th quarter"}
        return f"{tm} to go in the {qm.get(q,q)}"
    return raw or "Status not available"

def playSound(text):
    fn = SPEECH_DIR / f"speech_{uuid.uuid4().hex}.mp3"
    try:
        gTTS(text=text, lang="en").save(str(fn))
        pygame.mixer.music.load(str(fn))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print("playSound error:", e)
    finally:
        # best effort: delete once playback is fully done
        try:
            fn.unlink()
        except Exception:
            pass

def kill_edge():
    for p in psutil.process_iter(['pid','name']):
        if p.info['name'] and 'msedge' in p.info['name'].lower():
            try: p.terminate()
            except: pass

class StreamManager:
    def __init__(self, subdir):
        self.dir   = BASE_DIR/subdir; self.dir.mkdir(exist_ok=True)
        self.ctx   = None; self.page = None
        self.ready = asyncio.Event()
        self._mlb_feed_index = 0

    async def start(self):
        pw = await async_playwright().start()
        self.ctx = await pw.chromium.launch_persistent_context(
            str(self.dir), channel="msedge", headless=False
        )
        await asyncio.sleep(1)
        self.ready.set()

    # ——— BACK IN StreamManager ———
    async def mute_page(self):
        """Mute all audio/video on the current page."""
        if self.page:
            await self.page.evaluate(
                "() => { document.querySelectorAll('audio, video, iframe').forEach(el=>el.muted = true); }"
            )
            dbg(f"Muted {self.dir.name} page")

    async def unmute_page(self):
        """Unmute all audio/video on the current page."""
        if self.page:
            await self.page.evaluate(
                "() => { document.querySelectorAll('audio, video, iframe').forEach(el=>el.muted = false); }"
            )
            dbg(f"Unmuted {self.dir.name} page")
    async def open(self, url):

        async def wait_for_network_idle_with_timeout(page, timeout):
            try:
                # Wait for the network idle state with a manual timeout
                await asyncio.wait_for(page.wait_for_load_state("networkidle"), timeout)
                print("Network idle state achieved.")
            except asyncio.TimeoutError:
                print(f"Operation timed out after {timeout} seconds.")

        # Example usage with a 10-second timeout

        await self.ready.wait()
        if self.page:
            await self.page.close()
        self.page = await self.ctx.new_page()
        await self.page.goto(url)
        dbg("Opened", url)
        await self.unmute_page()
        # — NBA auto‑login & click “Listen”/“Watch Live” —
        if self.dir.name.lower() == "nba":
            try:
                await self.page.wait_for_selector('#onetrust-accept-btn-handler', timeout=3000)
                await self.page.click('#onetrust-accept-btn-handler')
                dbg("Clicked cookie‑consent accept")
            except Exception:
                pass

            # If signed‑out link present, go log in
            if await self.page.query_selector('a[href="/account/sign-in"]'):
                dbg("NBA signed‑out → signing in…")
                await self.page.goto("https://www.nba.com/account/sign-in")
                await self.page.wait_for_selector("#email")
                creds = (BASE_DIR/"credentials-nba.txt").read_text().splitlines()
                user, pwd = creds[0], creds[1]
                await self.page.fill("#email", user)
                await self.page.fill("#password", pwd)
                await self.page.click("#submit")
                await self.page.wait_for_load_state("networkidle")
                await self.page.goto(url)

            # then kick off the audio
            try:
                await self.page.wait_for_selector('button:text("Watch Live")', timeout=5000)
                await self.page.click('button:text("Watch Live")')
                dbg("Clicked NBA “Watch Live”")
            except:
                try:
                    await self.page.wait_for_selector('button:text("Listen")', timeout=5000)
                    await self.page.click('button:text("Listen")')
                    dbg("Clicked NBA “Listen”")
                except:
                    dbg("NBA watch button not found.")

        # … inside your auto‑login routine, after you do page.goto(url) …
# … inside your auto‑login routine, after you do page.goto(url) …
        elif self.dir.name.lower() == "mlb":
            # give the page a moment to settle
            await wait_for_network_idle_with_timeout(self.page, timeout=10)

            # 1) dismiss OneTrust banner (main frame or any frame)
            btn = await self.page.query_selector('#onetrust-accept-btn-handler')
            if btn:
                await btn.click()
                dbg("Clicked OneTrust accept in main frame")
            else:
                for frame in self.page.frames:
                    btn = await frame.query_selector('#onetrust-accept-btn-handler')
                    if btn:
                        await btn.click()
                        dbg(f"Clicked OneTrust accept in frame {frame.name or frame.url}")
                        break

            # 2) detect & fill username if we’re on the login page
            try:
                identifier = await self.page.wait_for_selector(
                    'input[name="identifier"], input[autocomplete="username"]',
                    timeout=5000
                )
                dbg("MLB login prompt detected – filling username/password")

                # read credentials
                username, password = (BASE_DIR / "credentials-mlb.txt")\
                    .read_text().splitlines()[:2]

                # fill username + continue
                await identifier.fill(username)
                await self.page.click(
                    'input.button-primary[type="submit"], input[type="submit"][value="Continue"]'
                )
                dbg("Submitted MLB username")

                # optional “Verify Account With Password”
                try:
                    verify = await self.page.wait_for_selector(
                        'a.button.select-factor.link-button:has-text("Verify Account With Password")',
                        timeout=2000
                    )
                    await verify.click()
                    dbg("Clicked ‘Verify Account With Password’")
                except PlaywrightTimeoutError:
                    dbg("No ‘Verify Account With Password’ link")

            except PlaywrightTimeoutError:
                dbg("No MLB username prompt (already signed in?)")

            # 3) detect & fill password if prompted
            try:
                pwd_field = await self.page.wait_for_selector(
                    'input[name="credentials.passcode"], #input62',
                    timeout=2000
                )
                await pwd_field.fill(password)
                dbg("Filled MLB password")

                await self.page.wait_for_selector(
                    'input.button.button-primary[type="submit"][value="Log in"][data-type="save"]')
                await self.page.click('input.button.button-primary[type="submit"][value="Log in"][data-type="save"]')

                await self.page.wait_for_url("**/tv/**", timeout=5000)

                # now we’re on the protected MLB TV page
                await self.page.wait_for_load_state("networkidle")

                # === Try Audio Feed First ===
                try:
                    # 1) open the broadcast selector
                    await self.page.get_by_role("button", name="Broadcast selector").click()
                    dbg("Clicked Broadcast selector")

                    # 2) grab *all* audio‐feed buttons by their accessible name
                    feeds = self.page.get_by_role("button").filter(
                        has=self.page.get_by_label("AUDIO -")
                    )
                    count = await feeds.count()
                    if count > 0:
                        # pick the one at our current index
                        idx = self._mlb_feed_index % count
                        feed_btn = feeds.nth(idx)
                        label = await feed_btn.get_attribute("aria-label")
                        await feed_btn.click()
                        dbg(f"Clicked MLB audio feed: {label}")
                        self._mlb_feed_index += 1
                        return  # done—audio is playing
                    else:
                        dbg("No enabled audio feeds found, falling back to TV")
                except Exception as e:
                    dbg("Audio‐feed attempt failed:", e)

                # === Fallback to TV (do nothing since the video is already loaded) ===
                dbg("Falling back to TV stream")
            except PlaywrightTimeoutError:
                dbg("No MLB password prompt (already signed in?)")

class GameCycler:
    def __init__(self, root):
        self.root       = root
        root.title("NBA + MLB Cycler")
        self.lbl1       = tk.Label(root, text="Loading games…", font=("Arial",16))
        self.lbl1.pack(pady=8)
        self.lbl2       = tk.Label(root, text="",             font=("Arial",14))
        self.lbl2.pack(pady=4)
        tk.Button(root, text="Next Game", command=self.next_game).pack(pady=10)

        self.nba_mgr    = StreamManager("nba")
        self.mlb_mgr    = StreamManager("mlb")
        self.game_list  = []   # list of (league, meta_dict)
        self.idx        = 0
        self.current    = None


        # before starting asyncio:
        self.first_load = True
        threading.Thread(target=self._startup_sound_loop, daemon=True).start()

        pygame.mixer.init()
        self.loop       = asyncio.new_event_loop()
        threading.Thread(target=self._run_loop, daemon=True).start()
        asyncio.run_coroutine_threadsafe(self._startup(), self.loop)

    def _startup_sound_loop(self):
        # runs until first_load is set False
        while self.first_load:
            # update on‑screen prompt
            self.root.after(0, lambda: self.lbl1.config(text="Opening, please wait…"))
            playSound("Opening, please wait")
            time.sleep(4)
    def _status_key(self, entry):
        league, meta = entry
        if league == "NBA":
            code = meta.get("gameStatus", 1)
            # Live→0, Final→1, Scheduled→2
            return 0 if code == 2 else 1 if code == 3 else 2
        else:
            state = meta.get("state", "Preview")
            return 0 if state == "Live" else 1 if state == "Final" else 2

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _startup(self):
        dbg("Starting browsers…")
        await asyncio.gather(self.nba_mgr.start(), self.mlb_mgr.start())

        # fetch only *meta* for today's NBA + MLB
        await self._fetch_nba_meta()
        await self._fetch_mlb_meta()

        # split into separate NBA/MLB lists
        nba_list = [e for e in self.game_list if e[0] == "NBA"]
        mlb_list = [e for e in self.game_list if e[0] == "MLB"]

        # sort by in‑progress / final / scheduled
        nba_list.sort(key=self._status_key)
        mlb_list.sort(key=self._status_key)

        # recombine
        self.game_list = nba_list + mlb_list
        dbg("Sorted NBA then MLB:", [
            (l, m.get("gameStatus") or m.get("state")) for l,m in self.game_list
        ])

        # load first
        self.root.after(0, self._load_and_show, self.idx)

    async def _fetch_nba_meta(self):
        url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
        dbg("🔍 _fetch_nba_meta starting:", url)
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url) as r:
                    dbg("NBA response status:", r.status)
                    text = await r.text()
                    data = json.loads(text)
            games = data.get('scoreboard', {}).get('games', [])
            dbg(f"Found {len(games)} NBA games")
            for g in games:
                self.game_list.append(("NBA", {
                    "gameId":         g["gameId"],
                    "awayTeam":       g["awayTeam"],
                    "homeTeam":       g["homeTeam"],
                    "gameStatus":     g["gameStatus"],
                    "gameStatusText": g.get("gameStatusText",""),
                    "gameDate":       g.get("gameDate")    # include for start‑time logic
                }))
        except Exception as e:
            dbg("NBA meta fetch error:", e)

    async def _fetch_mlb_meta(self):
        dbg("🔍 _fetch_mlb_meta starting")
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            url   = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"
            async with aiohttp.ClientSession() as s:
                async with s.get(url) as r:
                    dbg("MLB response status:", r.status)
                    data = await r.json()
            for date in data.get("dates",[]):
                for g in date.get("games",[]):
                    self.game_list.append(("MLB", {
                        "gamePk":   g["gamePk"],
                        "away":     g["teams"]["away"],
                        "home":     g["teams"]["home"],
                        "gameDate": g["gameDate"],
                        "state":    g["status"]["abstractGameState"]
                    }))
        except Exception as e:
            dbg("MLB meta fetch error:", e)

    def next_game(self):
        if not self.game_list:
            return
        self.idx = (self.idx + 1) % len(self.game_list)
        self._load_and_show(self.idx)

    def _load_and_show(self, idx):
        # announce loading
        self.lbl1.config(text="Loading next game…")
        self.lbl2.config(text="")
        self.loading = True
        threading.Thread(target=self._loading_loop, daemon=True).start()
        asyncio.run_coroutine_threadsafe(self._fetch_and_display(idx), self.loop)

    def _loading_loop(self):
        while getattr(self, "loading", False):
            playSound("Loading next game")
            time.sleep(4)

    async def _fetch_and_display(self, idx):
        league, meta = self.game_list[idx]
        dbg(f"Fetching details for {league}", meta)
        if league == "NBA":
            g = await self._fetch_nba_detail(meta["gameId"])
        else:
            g = await self._fetch_mlb_detail(meta["gamePk"])
        self.current = (league, g)
        self.loading = False
        self.root.after(0, self._render_current)

    async def _fetch_nba_detail(self, gameId):
        url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
        async with aiohttp.ClientSession() as s:
            r    = await s.get(url)
            data = await r.json(content_type=None)
        for g in data['scoreboard']['games']:
            if g["gameId"] == gameId:
                return g
        raise RuntimeError("NBA game not found")

    async def _fetch_mlb_detail(self, gamePk):
        today = datetime.now().strftime("%Y-%m-%d")
        url   = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"
        async with aiohttp.ClientSession() as s:
            r    = await s.get(url)
            data = await r.json()
        for date in data.get("dates", []):
            for g in date.get("games", []):
                if g["gamePk"] == gamePk:
                    return g
        raise RuntimeError("MLB game not found")

    def _render_current(self):
          # if we’re switching from a previous live stream, mute it

        if hasattr(self, "last_mgr") and self.last_mgr:
            asyncio.run_coroutine_threadsafe(self.last_mgr.mute_page(), self.loop)

        # 1) Stop any “loading…” loop
        self.loading = False

        # 2) Only-once startup flag
        if getattr(self, "first_load", True):
            self.first_load = False

        league, g = self.current
        open_stream = False
        now = datetime.now().astimezone()

        # — NBA —
        if league == "NBA":
            code = g.get("gameStatus", 1)  # 1=Scheduled, 2=Live, 3=Final
            away, home = g["awayTeam"], g["homeTeam"]
            match = f"{away['teamCity']} {away['teamName']} at {home['teamCity']} {home['teamName']}"

            if code == 1:
                # Scheduled
                start_txt = g.get("gameStatusText", "").strip()
                status = f"Starts at {start_txt}"
                score = ""

                # if we have ISO start time, open once we're within 45 min before it
                dt_str = g.get("gameDate")
                if dt_str:
                    try:
                        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone()
                        # as soon as now >= (dt - 45min), flag open
                        if now >= dt - timedelta(minutes=45):
                            open_stream = True
                    except Exception:
                        pass

            elif code == 2:
                # Live
                status = parse_nba_status(g.get("gameStatusText", ""))
                hs, as_ = home.get("score", 0), away.get("score", 0)
                if hs >= as_:
                    ln, ls, tn, ts = home["teamName"], hs, away["teamName"], as_
                else:
                    ln, ls, tn, ts = away["teamName"], as_, home["teamName"], hs
                score = f"{ln} {ls}, {tn} {ts}"
                open_stream = True

            else:  # code == 3 → Final
                status = "Final"
                hs, as_ = home.get("score", 0), away.get("score", 0)
                if hs >= as_:
                    ln, ls, tn, ts = home["teamName"], hs, away["teamName"], as_
                else:
                    ln, ls, tn, ts = away["teamName"], as_, home["teamName"], hs
                score = f"{ln} {ls}, {tn} {ts}"

        # — MLB —
        else:
            state = g.get("status", {}).get("abstractGameState", "Preview")
            away, home = g["teams"]["away"], g["teams"]["home"]
            match = f"{away['team']['name']} at {home['team']['name']}"

            if state == "Preview":
                # Scheduled
                dt_str = g.get("gameDate")
                if dt_str:
                    try:
                        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone()
                        start_str = dt.strftime("%I:%M %p").lstrip("0")
                    except Exception:
                        start_str = g.get("status", {}).get("detailedState", "Scheduled")
                else:
                    start_str = g.get("status", {}).get("detailedState", "Scheduled")
                status = f"Scheduled at {start_str}"
                score = ""

                # open once within 45 min of start
                if dt_str:
                    try:
                        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone()
                        if now >= dt - timedelta(minutes=45):
                            open_stream = True
                    except Exception:
                        pass

            elif state == "Live":
                # Live
                status = g["status"].get("detailedState", "Live")
                hs, as_ = home.get("score", 0), away.get("score", 0)
                if hs >= as_:
                    ln, ls, tn, ts = home["team"]["name"], hs, away["team"]["name"], as_
                else:
                    ln, ls, tn, ts = away["team"]["name"], as_, home["team"]["name"], hs
                score = f"{ln} {ls}, {tn} {ts}"
                open_stream = True

            else:
                # Final
                status = "Final"
                hs, as_ = home.get("score", 0), away.get("score", 0)
                if hs >= as_:
                    ln, ls, tn, ts = home["team"]["name"], hs, away["team"]["name"], as_
                else:
                    ln, ls, tn, ts = away["team"]["name"], as_, home["team"]["name"], hs
                score = f"{ln} {ls}, {tn} {ts}"

        # — Update UI —
        self.lbl1.config(text=match)
        self.lbl2.config(text=f"{status}\n{score}".strip())

        # — Speak in background —
        threading.Thread(
            target=self._speak_all,
            args=(match, status, score),
            daemon=True
        ).start()

        # — Open stream if flagged —
        if open_stream:
            if league == "NBA":
                url = (
                    f"https://www.nba.com/game/"
                    f"{away['teamTricode']}-vs-{home['teamTricode']}-{g['gameId']}?watch"
                )
                mgr = self.nba_mgr
            else:
                url = f"https://www.mlb.com/tv/g{g['gamePk']}"
                mgr = self.mlb_mgr
            asyncio.run_coroutine_threadsafe(mgr.open(url), self.loop)
            self.last_mgr = mgr

    def _speak_all(self, match, status, score):
        playSound(match)
        playSound(status)
        if score:
            playSound(score)

if __name__ == "__main__":
    kill_edge()
    root = tk.Tk()
    game = GameCycler(root)

    # start listening to the controller
    controller_thread = threading.Thread(
        target=controller_loop,
        args=(game,),
        daemon=True
    )
    controller_thread.start()
    root.mainloop()
