# Retro Prototype v1

Date: 2026-08-29
Version: v0.5.0.0
Status: FIRST RUNNABLE PROTOTYPE

## Purpose

This build exists to answer a visual/product question before more management UI is rewritten:

> Does the application feel more compelling when the main window is treated as a collection scene instead of a traditional manager dashboard?

The prototype therefore prioritizes the scene, Arc Showcase and focus/detail interaction. It intentionally reuses existing Flat Pro operations for management functions that have not yet been redesigned.

## Startup

- Identity is bypassed.
- Startup opens Game Scene.
- Game ordering prefers most recently played.
- Empty libraries show the environment with a minimal empty-state label.

## Scene foundation

The first environment is a neutral-dark semi-skeuomorphic digital display space:

- cool cyan/blue ambient light;
- smoked acrylic rear surfaces;
- an indistinct half-floating stage;
- slowly moving reflected light;
- low-amplitude mouse parallax;
- no particle field;
- no real-time OS blur requirement.

## Hidden primary navigation

Primary navigation contains only three icon controls:

- Movie
- Game
- Settings

Default location: bottom-right.

The controls remain hidden until the pointer enters the corner hot zone. They use simple fade-in/fade-out only. The corner can be switched to bottom-left in the Retro system panel.

Flat Pro window chrome is hidden in Retro. The top edge remains a system-drag area, and minimal minimize/maximize/close controls reveal only when the pointer reaches the top-right hot zone.

## Arc Showcase

Game and Movie Scenes share the same Arc interaction language:

- current object is left-of-center and closest to the viewer;
- previous object sits left/rear and is partially hidden;
- next object sits right/rear and is partially hidden;
- mouse wheel or arrow keys rotate one item at a time through a mixed horizontal/depth arc;
- transition feel is console-like: quick response, smooth movement, short snap-to-item ending.

### Focus

- single click current object: focus it, enlarge about 25%, reduce its angle, reveal right-side information;
- click empty scene: leave focus;
- wheel remains available while focused and keeps the focus state;
- double click: launch game / play movie;
- right click: object operations.

### Expanded details

“MORE +” opens an in-scene smoked translucent panel occupying about the right two-thirds of the scene. The object remains visible on the left as a physical anchor.

Game tabs:

- 概览
- 截图
- 记录
- 本地

Movie tabs:

- single movie: 概览 / 截图 / 记录 / 本地
- multi-episode work: 概览 / 剧集 / 记录 / 本地

The expanded detail state does not navigate to the legacy Archive Page.

## Game object styles

Arc Showcase contains two first-pass game-box presentations sharing the same interaction system.

### Classic Box

- high case proportions inspired by Xbox 360 / PS3 era packaging;
- visible spine/depth;
- subdued semi-transparent plastic structure;
- very light plastic-film reflection;
- cover art remains the main visual content.

### Neo Box

- smoked semi-transparent acrylic shell;
- restrained cyan edge light;
- cover floats inside the shell at medium visual depth;
- no strong neon emission;
- cover remains the main visual content.

Neo is the default prototype style. Style can be changed from the Retro system panel or scene context menu.

## Movie object

The first Movie Showcase uses a slightly thick floating portrait poster plate rather than a game-style case. It shares Arc movement and focus behavior with games.

A Blu-ray/case-based Movie Showcase remains a future independent display mode.

## System panel

The Settings icon opens a scene-local smoked panel instead of leaving the environment. The active Showcase moves visually backward while the panel is open.

Prototype categories:

- 外观
- 资源库
- 扫描
- 备份
- 高级

Only a subset is implemented natively in Retro R0. “打开完整设置…” invokes the existing settings dialog, and F12/Advanced can expose the Flat Pro baseline.

## Prototype boundary

This is not yet a full replacement for every Flat Pro management surface.

Intentionally deferred:

- true 3D renderer;
- shaders/real-time blur;
- final material system;
- full Retro search/filter/folder UI;
- full Retro editing forms;
- final screenshot browser;
- episode playback directly from the Retro episode grid;
- final system/backup management panel;
- removal of legacy Identity code;
- removal of legacy Archive Pages.

The next decision should be based on using and seeing this build, not on extending the written design further.
