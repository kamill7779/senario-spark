# Flutter Short Drama Player Design

## Goal

Build the first Flutter mobile client shape for SenarioSpark: a short-drama app with a login entry, bottom navigation, and a playback tab that can play a received episode source.

## Product Shape

The app is a user-facing short-drama player, not a bare video demo. The first screen is a restrained Apple-style login screen in black and white. After login, users enter a three-tab shell:

- Home: a compact short-drama discovery surface.
- Player: the episode playback surface.
- Profile: account and app status.

The player consumes a network URL through `EpisodeSource`, matching the production shape where upstream storage or a backend service distributes playable episode media. The local file `C:\Users\23999\Downloads\第3集.mp4` can be used for acceptance only after it is exposed through a local HTTP/static service and passed to the app as `EPISODE_URL`.

## Architecture

The Flutter project lives in `frontend/mobile-app`, matching the repository boundary already documented for the mobile client. The app uses a simple stateful shell instead of a routing or state-management framework because the MVP has only login state and a selected tab.

Playback uses `media_kit` because the MVP needs one player implementation across mobile targets and Windows desktop verification. `EpisodeVideoPlayer` accepts an `EpisodeSource` URL and opens it through the same playback surface used for production upstream delivery.

## UI Direction

The interface uses a minimalist black-and-white Apple-like direction: bright white surfaces, near-black text, hairline borders, generous spacing, and restrained controls. The visual priority is the episode frame and transport controls. No gradients, neon colors, or decorative cards are used.

## Error Handling

The player exposes loading, ready, and error states. Missing or unreadable upstream video sources show a clear inline message and retry action.

## Verification

Expected checks:

- `flutter test` validates login flow, tab navigation, and episode source behavior.
- `flutter analyze` validates Dart/Flutter static correctness.
- Manual acceptance: launch the app, log in, open Player, and play the configured episode.

If Flutter is not installed in the executing shell, verification is limited to file inspection and the missing tool is reported.
