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
import re
import sys

BASE_DIR = Path.home() / "mlb_app_data"
BASE_DIR.mkdir(exist_ok=True)
PROJECT_DIR = Path(__file__).parent
SPEECH_DIR = PROJECT_DIR / "speech_mp3s"
SPEECH_DIR.mkdir(exist_ok=True)

# Clear out any leftovers from prior runs
for old in SPEECH_DIR.glob("speech_*.mp3"):
    try:
        old.unlink()
    except:
        pass

# Register end-of-program cleanup
atexit.register(lambda: shutil.rmtree(SPEECH_DIR, ignore_errors=True))


NBA_SCOREBOARD_URL = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Accept": "application/json, text/plain, */*",
}


# Favorite teams, in the order they come first WITHIN their own league (when they play today).
# MLB games are still listed before NBA games. Each entry is (league, text in the team name).
FAVORITES = [
    ("MLB", "Red Sox"),
    ("MLB", "Cubs"),
    ("NBA", "Celtics"),
    ("NBA", "Knicks"),
]


def _windows_login(site):
    """(username, password) from Windows Credential Manager entry 'StreamingSimplifier-<site>', or None."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    advapi32 = ctypes.windll.advapi32
    cred_ptr = ctypes.POINTER(CREDENTIAL)()
    CRED_TYPE_GENERIC = 1
    if not advapi32.CredReadW(f"StreamingSimplifier-{site}", CRED_TYPE_GENERIC, 0, ctypes.byref(cred_ptr)):
        return None
    try:
        c = cred_ptr.contents
        raw = bytes(ctypes.cast(c.CredentialBlob, ctypes.POINTER(ctypes.c_ubyte * c.CredentialBlobSize)).contents)
        return c.UserName, raw.decode("utf-16-le")
    finally:
        advapi32.CredFree(cred_ptr)


def load_login(site):
    """(username, password) for 'nba' or 'mlb' from Windows Credential Manager, or None to sign in by hand."""
    found = _windows_login(site)
    if found and found[0] and found[1]:
        return found
    dbg(f"No saved login 'StreamingSimplifier-{site}': sign in by hand in the browser window")
    return None


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
            if ev.type == pygame.JOYBUTTONDOWN \
                    or ev.type == pygame.JOYAXISMOTION \
                    or ev.type == pygame.JOYHATMOTION:
                app.root.after(0, app.next_game)
        time.sleep(0.01)


def dbg(*args, **kwargs):
    print("[DEBUG]", *args, **kwargs)


_ORDINALS = {"1": "1st", "2": "2nd", "3": "3rd", "4": "4th"}
_QMAP_Q   = {"Q1": "1st quarter", "Q2": "2nd quarter", "Q3": "3rd quarter", "Q4": "4th quarter"}
_QMAP_ORD = {"1st": "1st quarter", "2nd": "2nd quarter", "3rd": "3rd quarter", "4th": "4th quarter"}
_OT_LABELS = {
    "OT":  "overtime",
    "2OT": "double overtime",
    "3OT": "triple overtime",
    "4OT": "quadruple overtime",
}


def _normalize_quarter_word(s: str) -> str:
    s = s.strip()
    if s in _QMAP_Q:
        return _QMAP_Q[s]
    m = re.fullmatch(r'(1st|2nd|3rd|4th)\s*(?:QTR|QUARTER)?', s, flags=re.I)
    if m:
        return _QMAP_ORD[m.group(1).lower()]
    return s


def parse_nba_status(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return "Status not available"
    if raw.lower() in {"final", "halftime"}:
        return raw.capitalize()
    m = re.match(r'^end of\s+(.+)$', raw, flags=re.I)
    if m:
        period = m.group(1).strip()
        up = period.upper().replace(" ", "")
        if up in _OT_LABELS:
            return f"End of {_OT_LABELS[up]}"
        return f"End of the {_normalize_quarter_word(period)}"
    mq = re.match(r'^(Q[1-4])\s+(\d{1,2}:\d{2})$', raw, flags=re.I)
    if mq:
        return f"{mq.group(2)} to go in the {_QMAP_Q.get(mq.group(1).upper(), mq.group(1))}"
    mo = re.match(r'^(1st|2nd|3rd|4th)\s*(?:QTR|QUARTER)\s+(\d{1,2}:\d{2})$', raw, flags=re.I)
    if mo:
        return f"{mo.group(2)} to go in the {_QMAP_ORD[mo.group(1).lower()]}"
    mo2 = re.match(r'^(1st|2nd|3rd|4th)\s*(?:QTR|QUARTER)$', raw, flags=re.I)
    if mo2:
        return f"In the {_QMAP_ORD[mo2.group(1).lower()]}"
    mq2 = re.match(r'^(Q[1-4])$', raw, flags=re.I)
    if mq2:
        return f"In the {_QMAP_Q[mq2.group(1).upper()]}"
    mot = re.match(r'^([1-4]?OT)\s+(\d{1,2}:\d{2})$', raw, flags=re.I)
    if mot:
        ot, tm = mot.group(1).upper(), mot.group(2)
        return f"{tm} to go in {_OT_LABELS.get(ot, ot.lower())}"
    if raw.upper().replace(" ", "") in _OT_LABELS:
        return f"In {_OT_LABELS[raw.upper().replace(' ', '')]}"
    return raw


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
        try:
            pygame.mixer.music.unload()   # Windows won't delete a file pygame still has open
        except Exception:
            pass
        try:
            fn.unlink()
        except Exception:
            pass


def kill_edge():
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and 'msedge' in p.info['name'].lower():
            try:
                p.terminate()
            except:
                pass


class StreamManager:
    def __init__(self, subdir):
        self.dir   = BASE_DIR / subdir
        self.dir.mkdir(exist_ok=True)
        self.ctx   = None
        self.page  = None
        self._data_page = None   # background page used only for JSON fetches
        self.ready = asyncio.Event()
        self._mlb_feed_index = 0

    async def start(self):
        pw = await async_playwright().start()
        self.ctx = await pw.chromium.launch_persistent_context(
            str(self.dir), channel="msedge", headless=False
        )
        await asyncio.sleep(1)
        self.ready.set()

    async def mute_page(self):
        if self.page:
            await self.page.evaluate(
                "() => { document.querySelectorAll('audio, video, iframe').forEach(el=>el.muted = true); }"
            )
            dbg(f"Muted {self.dir.name} page")

    async def unmute_page(self):
        if self.page:
            await self.page.evaluate(
                "() => { document.querySelectorAll('audio, video, iframe').forEach(el=>el.muted = false); }"
            )
            dbg(f"Unmuted {self.dir.name} page")

    async def fetch_json(self, url):
        """GET a JSON url from inside a real nba.com page (same-origin as the site's own calls)."""
        await self.ready.wait()
        if not self._data_page or self._data_page.is_closed():
            self._data_page = await self.ctx.new_page()
            await self._data_page.goto("https://www.nba.com/games", wait_until="domcontentloaded")
        status, text = await self._data_page.evaluate(
            "async u => { const r = await fetch(u); return [r.status, await r.text()]; }", url
        )
        if status != 200:
            raise RuntimeError(f"{url} returned {status}")
        return json.loads(text)

    async def open(self, url):

        async def wait_for_network_idle_with_timeout(page, timeout):
            try:
                await asyncio.wait_for(page.wait_for_load_state("networkidle"), timeout)
            except asyncio.TimeoutError:
                print(f"Network idle timed out after {timeout}s")

        await self.ready.wait()
        if self.page:
            await self.page.close()
        self.page = await self.ctx.new_page()
        await self.page.goto(url)
        dbg("Opened", url, "→ now", self.page.url)
        await self.unmute_page()

        if self.dir.name.lower() == "nba":
            try:
                await self.page.wait_for_selector('#onetrust-accept-btn-handler', timeout=3000)
                await self.page.click('#onetrust-accept-btn-handler')
                dbg("Clicked cookie-consent accept")
            except Exception:
                pass

            if await self._nba_signed_out():
                dbg("NBA signed-out → signing in…")
                await self._nba_login()
                await self.page.goto(url)

            await self._nba_press_play()
            # Signed-out visitors still get a play button; clicking it raises a
            # "League Pass activation / Sign in with NBA ID" popup. Log in and retry once.
            upsell = self.page.locator('a[class*="ModalBody_upsellAuthButton__"]').first
            try:
                await upsell.wait_for(state="visible", timeout=2000)
                dbg("NBA sign-in popup after play → signing in…")
                await self._nba_login()
                await self.page.goto(url)
                await self._nba_press_play()
            except PlaywrightTimeoutError:
                pass

        elif self.dir.name.lower() == "mlb":
            await wait_for_network_idle_with_timeout(self.page, timeout=10)
            await self._mlb_dismiss_cookies()
            await self._mlb_login()
            await self._mlb_tv_else_radio()

    async def _nba_press_play(self):
        """Click 'Watch Live' (not 'Resume', which jumps back to a saved spot); fall back to the play button, then Listen."""
        page = self.page
        live   = page.get_by_role("button", name="Watch Live")
        play   = page.locator(
            'button[class*="Play_buttonContainer__"][data-is-post-game="false"]'
        ).filter(has=page.locator('svg[class*="Play_playIcon__"]')).first
        listen = page.get_by_role("button", name="Listen")
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                for name, loc in (("Watch Live", live.first), ("play button", play), ("Listen", listen.first)):
                    if await loc.is_visible():
                        await loc.click()
                        dbg("Clicked NBA", name)
                        return
            except Exception as e:
                dbg("NBA play click retry:", e)
            await asyncio.sleep(0.4)
        dbg("NBA watch button not found.")

    async def _nba_signed_out(self):
        """True if the game page says we are not signed in.

        The page marks its hero section data-is-nba-authenticated="true|false",
        which is available as soon as the page renders.
        """
        hero = self.page.locator("section[data-is-nba-authenticated]").first
        try:
            await hero.wait_for(state="attached", timeout=15000)
            return (await hero.get_attribute("data-is-nba-authenticated")) == "false"
        except Exception as e:
            dbg("NBA auth flag not found:", e)
            return False

    async def _nba_login(self, timeout=120):
        """Go through the NBA sign-in steps (email, Continue, password, Sign in) as they appear.

        The generous timeout leaves room for NBA's one-time "I'm not a robot" check.
        With no saved login, wait for the user to sign in by hand.
        """
        login = load_login("nba")
        page = self.page
        await page.goto("https://www.nba.com/account/sign-in")
        if not login:
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline and "/account/sign-in" in page.url:
                await asyncio.sleep(1)
            return
        user, pwd = login
        email_f = page.locator('#email, input[type="email"], input[name="email"]').first
        pwd_f   = page.locator('#password, input[type="password"]').first
        button  = page.locator(
            '#submit, #email-submit, [data-testid="continue"], button[type="submit"], input[type="submit"]'
        ).first
        deadline = time.monotonic() + timeout
        email_done = pwd_done = False
        last_submit = 0.0
        while time.monotonic() < deadline:
            try:
                if "/account/sign-in" not in page.url:
                    return   # redirected away from the sign-in page: logged in
                if pwd_done:
                    # Already submitted. Only retry every 10s so the page is not scrolled
                    # constantly while the user ticks "I'm not a robot".
                    if time.monotonic() - last_submit >= 10 and await pwd_f.is_visible():
                        await pwd_f.fill(pwd)
                        await button.click()
                        last_submit = time.monotonic()
                        dbg("Retried NBA sign-in")
                    await asyncio.sleep(1)
                elif await pwd_f.is_visible():
                    await pwd_f.fill(pwd)
                    await button.click()
                    pwd_done = True
                    last_submit = time.monotonic()
                    dbg("Submitted NBA password (if a robot check shows, tick it, then press Sign in)")
                elif await email_f.is_visible() and not email_done:
                    await email_f.fill(user)
                    await page.keyboard.press("Tab")
                    await button.click()
                    email_done = True
                    dbg("Submitted NBA email")
                    await asyncio.sleep(2)
                else:
                    await asyncio.sleep(0.5)
            except Exception as e:   # page navigated mid-check; look again
                dbg("NBA login step retry:", e)
                await asyncio.sleep(1)
        dbg("NBA login did not finish within", timeout, "seconds")

    async def _mlb_wait_for_manual_login(self, timeout=300):
        """No saved login: give the user time to sign in by hand until the player page is up."""
        page = self.page
        fields = 'input[name="identifier"], input[autocomplete="username"], input[type="password"]'
        deadline = time.monotonic() + timeout
        quiet = 0
        while time.monotonic() < deadline:
            try:
                if "/tv/" in page.url and not await page.locator(fields).first.is_visible():
                    quiet += 1
                    if quiet >= 4:
                        return
                else:
                    quiet = 0
            except Exception:
                quiet = 0
            await asyncio.sleep(0.5)

    async def _mlb_login(self, timeout=45):
        """Work through whichever MLB login step is on screen until the player page is up.

        The steps (username, 'verify with password', password) can each be skipped
        or come in a different order, so look at the page every half second
        instead of waiting for a fixed sequence.
        """
        login = load_login("mlb")
        if not login:
            await self._mlb_wait_for_manual_login()
            return
        username, password = login
        user_sel = 'input[name="identifier"], input[autocomplete="username"]'
        pwd_sel  = 'input[name="credentials.passcode"], input[type="password"]'
        verify_sel = 'a.select-factor:has-text("Verify Account With Password"), a:has-text("Verify Account With Password")'
        submit_sel = ('input.button-primary[type="submit"], input[type="submit"], '
                      'button[type="submit"]')
        page = self.page
        deadline = time.monotonic() + timeout
        quiet = 0
        while time.monotonic() < deadline:
            try:
                if await page.locator(pwd_sel).first.is_visible():
                    quiet = 0
                    await page.locator(pwd_sel).first.fill(password)
                    await page.locator(submit_sel).first.click()
                    dbg("Submitted MLB password")
                    await asyncio.sleep(3)
                elif await page.locator(verify_sel).first.is_visible():
                    quiet = 0
                    await page.locator(verify_sel).first.click()
                    dbg("Clicked 'Verify Account With Password'")
                    await asyncio.sleep(1)
                elif await page.locator(user_sel).first.is_visible():
                    quiet = 0
                    await page.locator(user_sel).first.fill(username)
                    await page.locator(submit_sel).first.click()
                    dbg("Submitted MLB username")
                    await asyncio.sleep(2)
                elif "/tv/" in page.url:
                    # no login field on the player page; make sure it stays that way
                    quiet += 1
                    if quiet >= 4:
                        await page.wait_for_load_state("networkidle")
                        return
                    await asyncio.sleep(0.5)
                else:
                    await asyncio.sleep(0.5)
            except Exception as e:   # page navigated mid-check; look again
                dbg("MLB login step retry:", e)
                await asyncio.sleep(1)
        dbg("MLB login did not finish within", timeout, "seconds")

    async def _mlb_tv_else_radio(self):
        """Leave the TV feed alone; only switch to a radio (AUDIO) feed if no video starts."""
        page = self.page
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                playing = await page.evaluate(
                    "() => [...document.querySelectorAll('video')].some(v => v.readyState >= 2 && v.videoWidth > 0)"
                )
                if playing:
                    dbg("MLB TV feed is up")
                    return
            except Exception:
                pass
            await asyncio.sleep(0.5)
        dbg("No MLB TV video after 15s, trying a radio feed")
        try:
            await page.get_by_role("button", name="Broadcast selector").click(timeout=8000)
            feeds = page.get_by_role("button").filter(has=page.get_by_label("AUDIO -"))
            count = await feeds.count()
            if count == 0:
                dbg("No MLB radio feeds either")
                return
            feed_btn = feeds.nth(self._mlb_feed_index % count)
            label = await feed_btn.get_attribute("aria-label")
            await feed_btn.click()
            dbg(f"Clicked MLB radio feed: {label}")
            self._mlb_feed_index += 1
        except Exception as e:
            dbg("MLB radio feed attempt failed:", e)


class GameCycler:
    def __init__(self, root):
        self.root = root
        root.title("NBA + MLB Cycler")
        self.lbl1 = tk.Label(root, text="Loading games…", font=("Arial", 16))
        self.lbl1.pack(pady=8)
        self.lbl2 = tk.Label(root, text="", font=("Arial", 14))
        self.lbl2.pack(pady=4)
        tk.Button(root, text="Next Game", command=self.next_game).pack(pady=10)

        self.nba_mgr   = StreamManager("nba")
        self.mlb_mgr   = StreamManager("mlb")
        self.game_list = []
        self.idx       = 0
        self.current   = None
        self.last_mgr  = None

        # ── Re-entrancy guards ───────────────────────────────────────────
        self.loading              = False
        self._busy                = False   # single-flight: only one load at a time
        self._pending_next        = False   # queue one next while busy
        self._last_next_ts        = 0.0     # debounce timestamp
        self._loading_thread_alive = False
        # ─────────────────────────────────────────────────────────────────

        self.first_load = True
        threading.Thread(target=self._startup_sound_loop, daemon=True).start()

        pygame.mixer.init()
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self._run_loop, daemon=True).start()
        asyncio.run_coroutine_threadsafe(self._startup(), self.loop)

    def _startup_sound_loop(self):
        while self.first_load:
            self.root.after(0, lambda: self.lbl1.config(text="Opening, please wait…"))
            playSound("Opening, please wait")
            time.sleep(4)

    def _status_key(self, entry):
        league, meta = entry
        if league == "NBA":
            code = meta.get("gameStatus", 1)
            return 0 if code == 2 else 1 if code == 3 else 2
        else:
            state = meta.get("state", "Preview")
            return 0 if state == "Live" else 1 if state == "Final" else 2

    @staticmethod
    def _team_names(entry):
        league, meta = entry
        if league == "NBA":
            return [meta["awayTeam"].get("teamName", ""), meta["homeTeam"].get("teamName", "")]
        return [meta["away"]["team"].get("name", ""), meta["home"]["team"].get("name", "")]

    def _favorites_first(self, games):
        """Within one league's list, move favorite-team games to the front in FAVORITES order (rest keep their order)."""
        front = []
        for league, text in FAVORITES:
            for g in games:
                if g[0] == league and g not in front and any(text in n for n in self._team_names(g)):
                    front.append(g)
        return front + [g for g in games if g not in front]

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _startup(self):
        dbg("Starting browsers…")
        await asyncio.gather(self.nba_mgr.start(), self.mlb_mgr.start())

        await self._fetch_nba_meta()
        await self._fetch_mlb_meta()

        nba_list = [e for e in self.game_list if e[0] == "NBA"]
        mlb_list = [e for e in self.game_list if e[0] == "MLB"]
        nba_list.sort(key=self._status_key)
        mlb_list.sort(key=self._status_key)
        self.game_list = self._favorites_first(mlb_list) + self._favorites_first(nba_list)

        self.root.after(0, self._load_and_show, self.idx)

    # ── next_game: debounce + single-flight + pending queue ───────────────
    def next_game(self):
        # Debounce: ignore rapid double-fires (controller bounce, double clicks)
        now = time.time()
        if now - self._last_next_ts < 0.9:
            return
        self._last_next_ts = now

        if not self.game_list:
            return

        # Single-flight: if already loading, queue one pending next
        if self._busy:
            self._pending_next = True
            return

        self._busy = True
        self.idx   = (self.idx + 1) % len(self.game_list)
        self._load_and_show(self.idx)
    # ─────────────────────────────────────────────────────────────────────

    def _load_and_show(self, idx):
        self.lbl1.config(text="Loading next game…")
        self.lbl2.config(text="")
        self.loading = True

        # Guard against duplicate loading threads
        if not self._loading_thread_alive:
            self._loading_thread_alive = True
            threading.Thread(target=self._loading_loop, daemon=True).start()

        asyncio.run_coroutine_threadsafe(self._fetch_and_display(idx), self.loop)

    def _loading_loop(self):
        try:
            while getattr(self, "loading", False):
                playSound("Loading next game")
                time.sleep(4)
        finally:
            self._loading_thread_alive = False

    async def _fetch_nba_scoreboard(self):
        """Today's NBA scoreboard JSON.

        cdn.nba.com answers 403 to plain scripts (aiohttp/curl); it only answers
        a real page on nba.com. Try the cheap request first, then fetch from
        inside the NBA browser.
        """
        try:
            async with aiohttp.ClientSession(headers=NBA_HEADERS) as s:
                async with s.get(NBA_SCOREBOARD_URL) as r:
                    if r.status == 200:
                        return await r.json(content_type=None)
                    dbg("NBA scoreboard direct fetch status", r.status)
        except Exception as e:
            dbg("NBA scoreboard direct fetch failed:", e)
        return await self.nba_mgr.fetch_json(NBA_SCOREBOARD_URL)

    async def _fetch_nba_meta(self):
        try:
            data = await self._fetch_nba_scoreboard()
            for g in data.get('scoreboard', {}).get('games', []):
                self.game_list.append(("NBA", {
                    "gameId":         g["gameId"],
                    "awayTeam":       g["awayTeam"],
                    "homeTeam":       g["homeTeam"],
                    "gameStatus":     g["gameStatus"],
                    "gameStatusText": g.get("gameStatusText", ""),
                    "gameTimeUTC":    g.get("gameTimeUTC"),
                }))
        except Exception as e:
            dbg("NBA meta fetch error:", e)

    async def _fetch_mlb_meta(self):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            url   = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"
            async with aiohttp.ClientSession() as s:
                async with s.get(url) as r:
                    data = await r.json()
            for date in data.get("dates", []):
                for g in date.get("games", []):
                    self.game_list.append(("MLB", {
                        "gamePk":   g["gamePk"],
                        "away":     g["teams"]["away"],
                        "home":     g["teams"]["home"],
                        "gameDate": g["gameDate"],
                        "state":    g["status"]["abstractGameState"],
                    }))
        except Exception as e:
            dbg("MLB meta fetch error:", e)

    async def _fetch_and_display(self, idx):
        self.current = None   # clear before fetch — prevents stale game on error
        league, meta = self.game_list[idx]
        try:
            if league == "NBA":
                g = await self._fetch_nba_detail(meta["gameId"])
            else:
                g = await self._fetch_mlb_detail(meta["gamePk"])
            self.current = (league, g)
        except Exception as e:
            dbg("Fetch detail error:", e)
        finally:
            self.loading = False
            self.root.after(0, self._render_current)

    async def _fetch_nba_detail(self, gameId):
        data = await self._fetch_nba_scoreboard()
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
        try:
            self._render_current_inner()
        except Exception as e:
            dbg("_render_current unexpected error:", e)
            self.lbl1.config(text="Error loading game")
            self.lbl2.config(text="")
            threading.Thread(
                target=playSound, args=("Sorry, there was an error loading the game.",), daemon=True
            ).start()
        finally:
            self._finish_render()

    def _render_current_inner(self):
        if hasattr(self, "last_mgr") and self.last_mgr:
            asyncio.run_coroutine_threadsafe(self.last_mgr.mute_page(), self.loop)

        self.loading = False

        if getattr(self, "first_load", True):
            self.first_load = False

        if not self.current:
            self.lbl1.config(text="Could not load game — check your connection")
            self.lbl2.config(text="")
            threading.Thread(
                target=playSound, args=("Could not load game. Please check your internet connection.",), daemon=True
            ).start()
            return

        league, g   = self.current
        open_stream = False
        now         = datetime.now().astimezone()

        if league == "NBA":
            code       = g.get("gameStatus", 1)
            away, home = g["awayTeam"], g["homeTeam"]
            match      = f"{away['teamCity']} {away['teamName']} at {home['teamCity']} {home['teamName']}"

            if code == 1:
                start_txt   = g.get("gameStatusText", "").strip()
                status      = f"Starts at {start_txt}"
                score       = ""
                dt_str      = g.get("gameTimeUTC")
                if dt_str:
                    try:
                        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone()
                        if now >= dt - timedelta(minutes=45):
                            open_stream = True
                    except Exception:
                        pass
            elif code == 2:
                status      = parse_nba_status(g.get("gameStatusText", ""))
                hs, as_     = home.get("score", 0), away.get("score", 0)
                if hs >= as_:
                    ln, ls, tn, ts = home["teamName"], hs, away["teamName"], as_
                else:
                    ln, ls, tn, ts = away["teamName"], as_, home["teamName"], hs
                score       = f"{ln} {ls}, {tn} {ts}"
                open_stream = True
            else:
                status  = "Final"
                hs, as_ = home.get("score", 0), away.get("score", 0)
                if hs >= as_:
                    ln, ls, tn, ts = home["teamName"], hs, away["teamName"], as_
                else:
                    ln, ls, tn, ts = away["teamName"], as_, home["teamName"], hs
                score = f"{ln} {ls}, {tn} {ts}"

        else:  # MLB
            state      = g.get("status", {}).get("abstractGameState", "Preview")
            away, home = g["teams"]["away"], g["teams"]["home"]
            match      = f"{away['team']['name']} at {home['team']['name']}"

            if state == "Preview":
                dt_str = g.get("gameDate")
                if dt_str:
                    try:
                        dt        = datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone()
                        start_str = dt.strftime("%I:%M %p").lstrip("0")
                    except Exception:
                        start_str = g.get("status", {}).get("detailedState", "Scheduled")
                else:
                    start_str = g.get("status", {}).get("detailedState", "Scheduled")
                status = f"Scheduled at {start_str}"
                score  = ""
                if dt_str:
                    try:
                        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone()
                        if now >= dt - timedelta(minutes=45):
                            open_stream = True
                    except Exception:
                        pass
            elif state == "Live":
                status  = g["status"].get("detailedState", "Live")
                hs, as_ = home.get("score", 0), away.get("score", 0)
                if hs >= as_:
                    ln, ls, tn, ts = home["team"]["name"], hs, away["team"]["name"], as_
                else:
                    ln, ls, tn, ts = away["team"]["name"], as_, home["team"]["name"], hs
                score       = f"{ln} {ls}, {tn} {ts}"
                open_stream = True
            else:
                status  = "Final"
                hs, as_ = home.get("score", 0), away.get("score", 0)
                if hs >= as_:
                    ln, ls, tn, ts = home["team"]["name"], hs, away["team"]["name"], as_
                else:
                    ln, ls, tn, ts = away["team"]["name"], as_, home["team"]["name"], hs
                score = f"{ln} {ls}, {tn} {ts}"

        self.lbl1.config(text=match)
        self.lbl2.config(text=f"{status}\n{score}".strip())

        threading.Thread(target=self._speak_all, args=(match, status, score), daemon=True).start()

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
            fut = asyncio.run_coroutine_threadsafe(mgr.open(url), self.loop)
            fut.add_done_callback(
                lambda f: f.cancelled() or not f.exception() or dbg("open() failed:", repr(f.exception()))
            )
            self.last_mgr = mgr

    def _finish_render(self):
        """Release the single-flight lock and run any queued next."""
        self._busy = False
        if self._pending_next:
            self._pending_next = False
            self.root.after(0, self.next_game)

    def _speak_all(self, match, status, score):
        playSound(match)
        playSound(status)
        if score:
            playSound(score)


if __name__ == "__main__":
    kill_edge()
    root = tk.Tk()
    game = GameCycler(root)
    controller_thread = threading.Thread(target=controller_loop, args=(game,), daemon=True)
    controller_thread.start()
    root.mainloop()
