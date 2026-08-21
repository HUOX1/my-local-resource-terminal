# Local Identity Shell Design

## Goal
Add a single local identity entrance to the existing Flat Baseline without turning it into an online account system or changing movie/game business logic.

## Startup flow
Every application launch opens the Identity Shell first. If no identity exists, the full client area shows identity creation. After creation, the shell shows the saved identity entry state. If an identity already exists, startup immediately shows that entry state. The movie/game/settings shell remains hidden until the user clicks the identity avatar/badge.

## Main-shell identity room
After entry, the identity collapses into the top room of the existing left sidebar, replacing the current “本地资源终端 / LOCAL COLLECTION” brand block. The identity room and the media/system navigation share the same sidebar but remain visually separated. Clicking the identity room opens a lightweight local identity editor.

## Identity data
The identity is independent from movie/game schema and application settings. It is stored under `settings_path.parent / "identity"` with `profile.json` and managed `assets/` copies. Username is required. Avatar is optional and supports PNG/JPG/JPEG/GIF. Frame is optional and supports transparent PNG. Source files are never modified or deleted.

## UI behavior
The avatar widget supports static images and GIF via `QMovie`, with the PNG frame drawn above the avatar. A default local placeholder is shown when no avatar is configured. The identity shell and sidebar identity room use the current Theme tokens; there is no glass/window-chrome work in this feature.

## Non-goals
No password, authentication, multiple users, email, registration, cloud account, sync, online identity, logout, or theme-specific special effects. Existing movie/game/data/session behavior stays unchanged.

## Backup
New backups include the local identity tree when present. Existing v1/v2 backups remain restorable; restoring an old backup without identity data leaves the current identity untouched.
