# Flutter Short Drama Player Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create the Flutter mobile app MVP for SenarioSpark with login, bottom navigation, and a video player tab that plays an upstream-provided episode URL.

**Architecture:** The Flutter project is rooted at `frontend/mobile-app`. The app uses a small stateful shell for login and tab state, plus an `EpisodeSource` model and `EpisodeVideoPlayer` widget to isolate upstream URL handling from the UI.

**Tech Stack:** Flutter, Dart, `media_kit`, `media_kit_video`, `media_kit_libs_video`, `flutter_test`.

---

### Task 1: Scaffold Flutter App Files

**Files:**
- Create: `frontend/mobile-app/pubspec.yaml`
- Create: `frontend/mobile-app/analysis_options.yaml`
- Create: `frontend/mobile-app/lib/main.dart`
- Create: `frontend/mobile-app/lib/app.dart`
- Create: `frontend/mobile-app/test/widget_test.dart`
- Modify: `frontend/mobile-app/README.md`

**Steps:**

1. Add a minimal Flutter app manifest with `media_kit`.
2. Add a strict but standard Flutter lint configuration.
3. Add app entrypoint and placeholder app widget.
4. Add a widget test that expects the login screen.
5. Run `flutter test` and expect failure before implementation if Flutter is available.

### Task 2: Add Episode Source Model

**Files:**
- Create: `frontend/mobile-app/lib/features/player/episode_source.dart`
- Create: `frontend/mobile-app/test/episode_source_test.dart`

**Steps:**

1. Write tests for upstream URL source handling.
2. Run `flutter test test/episode_source_test.dart` and confirm red.
3. Implement `EpisodeSource`.
4. Re-run the model test and confirm green.

### Task 3: Build Login and Navigation Shell

**Files:**
- Modify: `frontend/mobile-app/lib/app.dart`
- Create: `frontend/mobile-app/lib/features/auth/login_screen.dart`
- Create: `frontend/mobile-app/lib/features/shell/main_shell.dart`
- Create: `frontend/mobile-app/lib/features/home/home_screen.dart`
- Create: `frontend/mobile-app/lib/features/profile/profile_screen.dart`
- Modify: `frontend/mobile-app/test/widget_test.dart`

**Steps:**

1. Write widget tests for login and bottom navigation labels.
2. Run tests and confirm red.
3. Implement the login screen and shell.
4. Run tests and confirm green.

### Task 4: Build Player Tab

**Files:**
- Create: `frontend/mobile-app/lib/features/player/player_screen.dart`
- Create: `frontend/mobile-app/lib/features/player/episode_video_player.dart`
- Modify: `frontend/mobile-app/lib/features/shell/main_shell.dart`
- Modify: `frontend/mobile-app/test/widget_test.dart`

**Steps:**

1. Add widget coverage for the player tab title and episode metadata.
2. Implement `PlayerScreen` and `EpisodeVideoPlayer`.
3. Wire the default source through `EPISODE_URL`.
4. Run tests.

### Task 5: Verify

**Commands:**

```powershell
flutter test
flutter analyze
git diff --check
git status --short
```

If `flutter` is unavailable, record that blocker and still run `git diff --check` plus file-level inspection.
