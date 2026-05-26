# SenarioSpark Mobile App

Flutter client for the SenarioSpark short-drama playback experience.

## MVP

- Login entry screen.
- Bottom navigation: home, player, profile.
- Player tab consumes an upstream video URL through `EpisodeSource`.
- Playback uses `media_kit` so the same player can handle mobile and desktop
  verification targets.

## Episode URL

The player reads the upstream source from `EPISODE_URL`:

```powershell
& 'C:\Users\23999\flutter\bin\flutter.bat' run -d windows `
  --dart-define=EPISODE_URL=http://127.0.0.1:8787/%E7%AC%AC3%E9%9B%86.mp4
```

For local acceptance with `C:\Users\23999\Downloads\第3集.mp4`, expose the file
through a local HTTP/static service first, then pass that URL as `EPISODE_URL`.
This keeps the app path identical to production upstream delivery.

## Local Commands

```powershell
& 'C:\Users\23999\flutter\bin\flutter.bat' test
& 'C:\Users\23999\flutter\bin\flutter.bat' analyze
```
