def load_next_game(self):
    if not self.games:
        return

    # Fetch new game data first
    asyncio.run_coroutine_threadsafe(self.fetch_games(), self.loop)

    # Wait for the game data to update
    time.sleep(2)  # Optionally, adjust the sleep time based on the fetching delay

    # Check if there are no games after fetch
    if len(self.games) == 0:
        playSound("No more games available.")
        self.game_info_label.config(text="No more games available.")
        self.score_label.config(text="")
        return

    # If there are still games, display the next one
    self.current_game_index = (self.current_game_index + 1) % len(self.games)
    self.display_game_info()


async def fetch_games(self):
    """Fetches the live game data from the NBA API."""
    url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.text()
                    self.process_game_data(json.loads(data))
                else:
                    messagebox.showerror("Error", "Failed to fetch game data.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")


def process_game_data(self, data):
    self.games = [game for game in data['scoreboard']['games'] if game['gameStatus'] == 2]
    if not self.games:
        self.game_info_label.config(text="No active games right now.")
        return
    self.current_game_index = 0
    self.display_game_info()
