# Xbox UWP — Audio Notes (XAudio2 / WASAPI), incl. suspend quiesce

Status: STUDY PARTIAL (2026-11-07) — architecture verified against primary project sources;
latency tuning NOT yet measured.

## 1. What this project uses (verified, `platforms/xbox/README.md` @ `UWP-Port`)

- **SDL3 provides the AX (GameCube audio) callback clock; XAudio2 is the output device.**
  `MELEE_XBOX_AUDIO_DRIVER` overrides the SDL driver for local debugging.
- The XAudio2 glue is `platforms/xbox/xaudio_output.cpp` (5.6 KB, `UWP-Port`).
- SDL3-uwp's WASAPI layer (`src/audio/wasapi/SDL_wasapi_winrt.cpp` @ `XboxEmulationHub/SDL3-uwp`
  `ec2e0e7c`) contains **zero suspend handling** — verified by grep (only device-activation
  code, incl. a standing `WaitForCompletion()` FIXME that can block on mic-permission prompts).

## 2. Xbox-specific quirks

1. **Suspend quiesce is the app's job.** Neither the XAudio2 glue nor the WASAPI layer pauses
   on `SDL_EVENT_WILL/DID_ENTER_BACKGROUND`; the process freeze masks this until resume, when
   stale queued buffers can glitch. Mandate (from the suspension contract, BLIND SPOT #3.5):
   `bg_enter` → `Stop()` + `FlushSourceBuffers()` on every source voice; `bg_exit` → refill +
   `Start()`.
2. **The 5-second suspend budget** (see `../03-Memory-CPU-And-JIT/dev-mode-memory-and-system-caps.md`
   and the SDL3-uwp audit) is shared with any audio save/quiesce work — keep it microseconds.
3. XAudio2 on UWP is the `Windows.XAudio2`/xaudio2 WinRT-era API surface via the SDK; the
   mastering-voice format must match the device (console output is resampled by the OS; no
   exclusive-mode low-latency path like WASAPI shared-mode tricks on PC).

## 3. Drop-in suspend quiesce (XAudio2)

```cpp
// Call from the DID_ENTER_BACKGROUND event watch (see audio contract D-S3), never from
// the WILL channel (it runs unprotected inside the suspend handler).
void audio_quiesce(IXAudio2SourceVoice* voice) {   // one per active voice
    if (!voice) return;
    voice->Stop();                 // no new buffers consumed
    voice->FlushSourceBuffers();   // drop queued audio instead of playing it at resume
}
void audio_resume(IXAudio2SourceVoice* voice) {
    if (!voice) return;
    // caller re-submits the first buffers first
    voice->Start();
}
```

## 4. Failure modes

1. **Resume glitch/pop storm** — queued buffers from before suspend replay or race the
   emulated AX clock after `bg_exit` (no quiesce exists today).
2. **AX clock drift** — SDL's audio callback clock vs XAudio2 buffering; suspend freezes the
   callback thread but the emulated clock keeps its own time — resync required on resume.
3. **Mic-permission block** (recording only) — `WaitForCompletion()` in the WASAPI
   activation path can block indefinitely per its own FIXME comment (SDL3-uwp source).

## 5. Untouched

- Latency budget/measurement (XAudio2 buffer sizing on Xbox), Game DVR capture audio mix,
  Bluetooth-headset behavior on console.
