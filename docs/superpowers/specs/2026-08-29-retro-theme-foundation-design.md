# Retro Theme Foundation Design

## Goal

Build a primary presentation that behaves like a personal digital collection showcase rather than a conventional media-manager dashboard, while retaining Flat Pro as a functional baseline.

## Presentation model

Retro is organized as three conceptual layers:

1. **Scene** — dynamic depth background and environmental material/light.
2. **Showcase** — Arc and future display modes that decide how collection objects are presented.
3. **Control** — hidden primary navigation, context menus, focus detail and system panels.

Shared Movie/Game services, repositories, JSON, SQLite, scanners, launch/play services and persistence stay outside these layers.

## R0 composition

- Default scene: Game.
- Default ordering: recent play.
- Visual center: one large collection object, left-of-center.
- Primary information: initially hidden; appears only in focus state at right.
- Persistent navigation: none.
- Hidden navigation: Movie / Game / Settings icons at bottom-right hot corner.

## Environment

- neutral-dark base;
- cyan/blue ambient light;
- smoked acrylic environmental planes;
- industrial/pearl-plastic language reserved for controls;
- half-floating stage with weak contact reflection/shadow;
- slow light movement plus mild pointer parallax;
- no dependency on native glass blur.

## Arc interaction

Arc is a reusable Showcase mode, not part of the theme itself.

States:

- browsing;
- focused;
- expanded details;
- system control.

Input:

- wheel/arrow: previous/next with item snapping;
- single click current: focus;
- double click current: primary action (launch/play);
- right click current: management context menu;
- click empty scene: back one visual state.

## Game material variants

Classic and Neo are material/object variants inside Arc, not independent navigation systems. They share selection, focus, launch, context menu, and details behavior.

## Detail panels

Expanded object details are scene overlays rather than separate Archive pages. They occupy roughly two-thirds of the window and preserve the collection object at left.

System settings also use a scene overlay, but with more functional layout and a de-emphasized Showcase behind it.

## Migration strategy

Retro is introduced as an overlay over the current MainWindow so existing services and Flat Pro widgets remain alive. This gives immediate rollback and lets the project migrate management surfaces gradually.

F12 is the development baseline toggle.

## Non-goals for R0

- engine migration to QML;
- true 3D;
- replacing every management form;
- deleting Flat Pro;
- deleting Identity internals before dependencies are removed;
- perfect final animation curves.
