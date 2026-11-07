# Xbox UWP — Input Stack: GameInput vs Windows.Gaming.Input (and what this project uses)

Status: STUDY COMPLETE (2026-11-07).

## 1. The decision, stated up front

**For UWP-on-Xbox, the input API is `Windows.Gaming.Input` (WGI) — GameInput is a GDK API
and is not in the UWP API surface.** GameInput (`GameInputCreate`, `IGameInputDevice`) ships
with the GDK/Xbox dev kit and a PC redistributable; a UWP package links the Windows SDK
contract, where WGI lives [S1][S2]. This project sidesteps the choice: **SDL3's WGInput
backend** does the work and the game sees `SDL_EVENT_GAMEPAD_*` (verified in
`YTReviveMe/melee-UWP.` `UWP-Port`, `src/pc/launcher.cpp` gamepad handlers).

| Capability | XInput | WGI | GameInput |
|---|---|---|---|
| Max controllers | **4** | **unlimited** [S4] | unlimited |
| Xbox pad certified path | ✅ | ✅ (`Gamepad` class) | ✅ |
| Non-certified HID pads | ❌ | ⚠️ `RawGameController` | ✅ |
| Keyboard/mouse unified | ❌ | ❌ | ✅ |
| Trigger rumble (XB1) | ❌ | ✅ `VibrationMotor` [S4] | ✅ `SetRumbleState` [S3] |
| Background access | ✅ | **❌ none** [S4] | coexistence-focused [S3] |
| Available to UWP pkg | ✅ | ✅ | **❌ GDK-only** [S1] |

## 2. WGI quirks (Xbox-specific, real)

1. **The gamepad list starts empty and takes 1–2 seconds to populate.** A game that grabs
   `Gamepad::Gamepads().GetAt(0)` in its start function gets **null** and, if it never
   re-polls, has no controller for the whole session. Microsoft's own "Input practices for
   games" documents this and prescribes added/removed handlers plus a refresh path [S2].
2. **Hot-swap via `GamepadAdded`/`GamepadRemoved`** — player slot assignment must survive
   removal (invalidate the slot, don't cache a dead `Gamepad^`) [S2].
3. **No background input**: WGI does not deliver controller state while the app lacks focus
   [S4] — on Xbox, suspension freezes input entirely (see the B-button note below).
4. **> 4 local players** is WGI territory; XInput cannot [S4].
5. **B button = Back** — on Xbox, `B` raises `SystemNavigationManager::BackRequested`
   (`SDL_WINRT` glue comment in `XboxEmulationHub/SDL3-uwp`
   `src/core/winrt/SDL_winrtapp_direct3d.cpp:345`); unhandled back requests can **suspend the
   app**. Any game UI must handle back explicitly (this project's disc browser maps B to
   "parent folder / close" — `platforms/xbox/README.md`).

## 3. Rumble

- WGI: `Gamepad.Vibration = { LeftMotor, RightMotor, LeftTrigger, RightTrigger }`
  (Xbox One pads expose trigger motors) [S4].
- GameInput (GDK, for comparison): `IGameInputDevice::SetRumbleState(GameInputRumbleParams)`
  with 4 motors [S3].
- **Desktop cautionary tale:** legacy DirectInput exclusive acquisition blocks the rumble
  output path at the driver level so that *no* other API can vibrate the pad while the game
  holds it [S3]. On UWP this class of problem doesn't arise (WGI is shared), but it is the
  reason not to bolt DirectInput onto a Windows build of the same code.

## 4. Drop-in WGI gamepad tracker (C++/WinRT)

```cpp
#include <winrt/Windows.Gaming.Input.h>
#include <mutex>
using namespace winrt::Windows::Gaming::Input;

struct PadTracker {
    std::mutex m;
    std::vector<Gamepad> pads;

    void Start() {
        Gamepad::GamepadAdded({ this, &PadTracker::OnAdded });
        Gamepad::GamepadRemoved({ this, &PadTracker::OnRemoved });
        for (auto const& g : Gamepad::Gamepads()) OnAdded(nullptr, g); // pre-enumerate!
    }
    void OnAdded(IInspectable const&, Gamepad const& g) {
        std::lock_guard lk(m);
        if (!contains(pads, g)) pads.push_back(g);           // never assume index 0 exists
    }
    void OnRemoved(IInspectable const&, Gamepad const& g) {
        std::lock_guard lk(m);
        erase(pads, g);                                      // invalidate player slots here
    }
    std::optional<GamepadReading> PollFirst() {
        std::lock_guard lk(m);
        if (pads.empty()) return std::nullopt;               // handles the 1-2s empty window
        return pads.front().GetCurrentReading();
    }
};
```

Failure modes covered: null-at-startup (pre-enumerate + empty check), hot-swap (erase on
remove), multi-thread event delivery (mutex — the events arrive on WinRT threads, compare the
suspension-thread findings in the SDL3-uwp audit).

## 5. What this project actually does (verified)

- Input via **SDL3** (WGInput backend on UWP); `src/pc/launcher.cpp` handles
  `SDL_EVENT_GAMEPAD_ADDED/REMOVED/BUTTON_DOWN/AXIS_MOTION` and chord handling
  (Start+Select opens Settings per `platforms/xbox/README.md`).
- Mouse/keyboard: the manifest grants no input capability beyond defaults; console UX is
  pad-first. KB/M support on Xbox UWP is possible (WGI has no KB/M class — use
  `Windows.UI.Core.CoreWindow` key events or SDL keyboard events) — **not yet studied
  end-to-end** (see README coverage map).

## Sources

- [S1] liukunup, "Windows.Gaming.Input (WGI)" overview/matrix (WGI = UWP-native; GameInput = GDK) — liukunup.github.io/blog/windows-gaming-input/
- [S2] Microsoft Learn, "Input practices for games" (empty-list quirk, added/removed pattern) — learn.microsoft.com/windows/uwp/gaming/input-practices-for-games (PRIMARY)
- [S3] Frontier forums, "No controller rumble … migrate to GameInput" (SetRumbleState, DirectInput rumble-blocking) — forums.frontier.co.uk (SINGLE-SOURCE anecdote for the driver-blocking claim)
- [S4] Steam discussion, "Steam Input > 4 players" (WGI unlimited pads, trigger rumble, no background access) — steamcommunity.com/groups/SteamClientBeta/discussions/1/1742265965884432584/
- [S5] Primary code: `YTReviveMe/melee-UWP.` @ `UWP-Port` — `src/pc/launcher.cpp`, `platforms/xbox/README.md`; `XboxEmulationHub/SDL3-uwp@ec2e0e7c` — `src/core/winrt/SDL_winrtapp_direct3d.cpp`
