# Demand, overlap and sources

## Observed demand

[Synfig #3752](https://github.com/synfig/synfig/issues/3752), reported May 29, 2026 against 1.5.5, describes black objects when a referenced gradient occurs later in an Inkscape-generated SVG. Its June comments describe a broader sequential-reference architecture and mention Inkscape’s SIF export route. The issue remained open when checked October 7, 2026. This supports a specific workaround use case; demand for this exact standalone product is not validated.

## Native boundary

The official [1.5.5 release](https://github.com/synfig/synfig/releases/tag/v1.5.5) resolves to `79bf708e2483cba678fc93f0ecf48b2178263795`. The official Linux64 AppImage asset has 115,539,968 bytes and SHA-256 `b85aabc26f690a0c150d2143c656c17f358b73abbedf8d01007f15a7a95740e9`, as reported by release metadata. The native gate verifies the actual downloaded bytes. 1.5.x is the development series; GitHub’s release metadata itself marks this asset release `prerelease=false`.

The pinned [SVG parser](https://github.com/synfig/synfig/blob/79bf708e2483cba678fc93f0ecf48b2178263795/synfig-core/src/modules/mod_svg/svg_parser.cpp) parses defs children sequentially. `get_colorStop` finds only already parsed linear gradients. An unresolved referencing gradient is not added. The parser separately reads each gradient’s own geometry/transform; this is why the profile requires complete painted geometry instead of claiming all SVG inheritance is repaired. Radial leaves can read linear stops, but radial bases are not searched.

The pinned [GUI import path](https://github.com/synfig/synfig/blob/79bf708e2483cba678fc93f0ecf48b2178263795/synfig-studio/src/synfigapp/canvasinterface.cpp) creates a normal group and temporary svg_layer, sets the real SVG filename, copies its parsed canvas into the group and removes the temporary layer. [layer_svg.cpp](https://github.com/synfig/synfig/blob/79bf708e2483cba678fc93f0ecf48b2178263795/synfig-core/src/modules/mod_svg/layer_svg.cpp) calls the unmodified `open_svg` implementation. The gate uses that genuine GUI action; it does not substitute a rewritten importer or assume direct SVG CLI import.

The research snapshot of current master `b385fbb2ce4b02b3fe628ed3f3c7480586a48cb3` has the same order-dependent lookup. [PR #3754](https://github.com/synfig/synfig/pull/3754) concerns spreadMethod; [PR #3764](https://github.com/synfig/synfig/pull/3764) concerns gradient clipping on rect/circle. Neither is a dependency-order fix. The synthetic baseline uses closed path artwork to avoid confusing those issues with ordering.

Exact source blob identities and asset pins are in `upstream-pins.json`.

## Existing solutions

- [SVGO sortDefsChildren](https://github.com/svg/svgo/blob/e4cb29bebcc9820ac979dfc05106b512cc5de986/plugins/sortDefsChildren.js) sorts by element-name frequency/length/name, rather than gradient references. The actual 4.0.0 tests include default and ID-preserving configurations as well as that plugin alone.
- [Scour](https://github.com/scour-project/scour/blob/0609c596766ec98e4e2092b49bd03b802702ba1a/scour/scour.py) can merge singly referenced gradients. Actual 0.38.2 default and preservation-oriented output is retained. Ubuntu 22.04 also [packages Scour 0.38.2](https://packages.ubuntu.com/en/jammy/scour).
- [svgcleaner](https://github.com/RazrFalcon/svgcleaner/tree/575eac74400a5ac45c912b144f0c002aa4a0135f) resolves and optimizes gradients, with merging/regrouping options. Actual official 0.9.5 release output is retained for three configurations. The older release has no API digest; the observed official asset hash is pinned separately and identified honestly as locally measured.
- [Inkscape’s shipped Synfig exporter](https://gitlab.com/inkscape/extensions/-/raw/master/synfig_output.py) contains recursive gradient resolution, and [Synfig’s documentation](https://wiki.synfig.org/Doc:Svg2synfig) recommends the SIF conversion route. Source inspection alone did not establish that the entire exporter pipeline succeeds. The actual Ubuntu1.1.2 exporter ran its normal preprocessing but emitted no gradients for this original fixture. Its inspected dispatch calls parse_defs for SvgDocumentElement, while ordinary Defs is a different class. The exact installed source/package identities are pinned in `inkscape-source-pins.json`; the next comparison will retain both unchanged source orders and native renders. This is a bounded version/fixture observation, not a general Inkscape failure claim.

Custom XML scripts, editor extensions and general dependency sorting can implement the same algorithm. The proposed value is the explicit static profile, unchanged SVG blocks, dependency/move review and tested native import path. No adoption, novelty, market validation or general superiority is claimed.
