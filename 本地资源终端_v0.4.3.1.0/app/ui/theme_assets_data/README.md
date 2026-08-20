# Theme assets

Optional skin-owned assets live under one folder per theme ID, for example:

```text
theme_assets_data/
  aero_millennium/
    background.png
    texture.png
    brand_mark.png
```

Register relative filenames through `ThemeAssets` in `app/config/theme_registry.py`.
The current Flat themes intentionally use no external assets.
