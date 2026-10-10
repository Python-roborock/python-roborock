# V1 Map Test Data Fixtures

These binary test files contain real raw Roborock V1 map payloads (`RRMap` format) used for unit testing and performance benchmarking of the Roborock V1 map parser (`roborock.map.map_parser`).

## Source & Attribution

The fixtures in this directory are adapted from the [Valetudo](https://github.com/Hypfer/Valetudo) project:
- **Repository**: https://github.com/Hypfer/Valetudo
- **Path in Source**: `backend/test/lib/robots/roborock/res/map/`
- **License**: Apache License 2.0 (compatible with `python-roborock`)
- **Author/Project**: Hypfer and Valetudo contributors

## Fixture Descriptions

| File Name | Original Source File | Model & Firmware | Features Exercised |
| :--- | :--- | :--- | :--- |
| `s5_fw2008_with_segments.bin` | `S5_FW2008_with_segments.bin` | Roborock S5 (fw 2008) | Multi-room segmentation (rooms 1 & 2), charger dock location, vacuum position, and path coordinates. |
| `s5_fw1886_with_forbidden_zones_and_virtual_walls.bin` | `S5_FW1886_with_forbidden_zones_and_virtual_walls_and_currently_cleaned_zones.bin` | Roborock S5 (fw 1886) | Virtual walls (`walls`), forbidden/no-go zones (`no_go_areas`), and currently cleaned zones (`zones`). |
| `s5_fw1886_with_goto_target.bin` | `S5_FW1886_with_goto_target.bin` | Roborock S5 (fw 1886) | Pinpoint target location (`goto`) and predicted navigation path to target (`predicted_path`). |
| `s6_fw2652_with_active_segment_and_no_mop_zone.bin` | `S6_FW2652_with_active_segment_and_no_mop_zone.bin` | Roborock S6 (fw 2652) | Complex layout with 6 segmented rooms (16, 17, 18, 19, 20, 21), active cleaning segment, and no-mop zone. |
