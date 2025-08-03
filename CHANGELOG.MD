# Change Log

All notable changes documented here; using 0.x “pre-1.0” versioning.

---

## 0.1.0 – 2024-12-12

* Initial prototype

  * Playwright scraper + Tkinter GUI
  * Separate NBA and MLB tabs

---

## 0.1.1 – 2025-01-03

* Dual-browser-tab refactor

  * One context for auto-refresh, one for stable playback
  * Wrapped logic in `NBAContextManager`

---

## 0.1.2 – 2025-01-07

* UI & stability refinements

  * Tweaked grid layouts to prevent widget overlap
  * Fixed race condition when closing the scraper tab
  * Improved logging for easier troubleshooting

---

## 0.2.0 – 2025-01-08

* Usability tweaks

  * Removed the “radio” TTS feature (performance issues)
  * Added joystick/gamepad support

---

## 0.2.1 – 2025-01-13

* Audio consistency

  * Patched intermittent muting when switching games
  * Smoothed out playback buffering
* Configuration UI

  * Exposed refresh-interval setting in preferences

---

## 0.3.0 – 2025-01-15

* Data export

  * “Export to CSV” for current game list (timestamps & link texts)

---

## 0.3.1 – 2025-02-10

* Audio engine overhaul

  * Switched to a more robust playback library for prompts & commentary

---

## 0.3.2 – 2025-02-20

* Volume controls

  * Added master-volume slider and mute toggle

---

## 0.4.0 – 2025-03-05

* Major bug sweep

  * Handled “no games available” edge case
  * Off-by-one fixes in list indexing
  * Prevented focus-stealing on refresh

---

## 0.4.1 – 2025-03-16

* Network resiliency

  * Retry logic for HTTP failures
  * User alerts on connectivity issues
* Minor polish

  * Better error dialogs
  * Cleaned up console logs

---

## 0.5.0 – 2025-04-02 to 2025-04-09

* Packaging & installer prep

  * Built an executable installer
  * Pre-trial UI tweaks (icons, README updates)

---

## 0.5.1 – 2025-04-18

* First trial release

---

## 0.5.2 – 2025-04-22

* Unified “Games” tab

  * Merged MLB+NBA listings into one view
* Post-trial fixes

  * Addressed crash on empty lists
  * Improved link-fetch timeout handling
  * Polished button tooltips

---

## 0.6.0 – 2025-04-25

* Feedback-driven tweaks

  * Increased default refresh interval
  * Adjusted GUI font sizes for readability

---

## 0.6.1 – 2025-05-10

* UX polish

  * Refined button labels
  * Added inline help text
  * Minor layout spacing adjustments
