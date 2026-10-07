# Native-first acceptance method

## Status

Source tests and the literal order-only fixture comparison pass locally. Eight actual optimizer configurations have been executed on the fixed fixture and retain forward references. Native Synfig import, Inkscape SIF conversion, native render and browser semantic gates are **unrun** until the exact published workflow and original artifact are inspected. No UI is built before that result.

The [first hosted attempt](https://github.com/Masanori-Spec/grad-before/actions/runs/37597540596) passed all 44 source tests, then stopped because the official AppImage loader lacked `libfuse.so.2`. Adding that runtime library allowed the [second attempt](https://github.com/Masanori-Spec/grad-before/actions/runs/37598970037) to expose the format mismatch: this older AppImage ignores `--appimage-extract` and starts its GUI. Both stopped before the intended native test.

Static inspection of the exact digest-pinned asset confirms `AI\x01` at bytes 8–10 and the ISO9660 primary descriptor at offset 32768. The workflow now uses the [documented type-1 archive extraction route](https://docs.appimage.org/user-guide/troubleshooting/fuse.html#mount-or-extract-type-1-appimages), through Ubuntu's `libarchive-tools`. The asset runtime is never executed or mounted during preparation; `libfuse2` is no longer needed. A temporary tar representation permits explicit path, link, entry-count and expanded-size checks before materialization. Regular files are written before internal links, and every resolved extracted path is checked again before any native executable runs. Eight small archive guard tests cover ordinary links and unsafe paths, duplicate/special entries, and missing/cyclic hardlinks.

The vendor launch script was also inspected: it writes HOME-based configuration and clears a font cache. The gate therefore launches the unchanged official `usr/bin/synfigstudio` ELF with the required process-local vendor paths and disposable configuration/cache files. It retains inherited HOME. The asset/header observations and original launcher hashes are retained in `appimage-inspection.json`; vendor scripts/binaries are not distributed. Native GUI/importer, rendering and browser outcomes remain pending.

## Fixed independent fixtures

`original.svg` places `paintA`, `radialLeaf`, `bridgeB`, `sharedC` in that order. A references B; B and the radial leaf reference C. C has the three independently specified red/green/blue stops at 0, 0.5 and 1. Three separate closed paths use A, B and the radial leaf. The shared graph is intentional, rather than a trivial one-use gradient optimization case. Geometry is explicit, numeric and userSpaceOnUse; radial focus is centered. The profile rejects inherited-only gradient transforms on painted gradients, malformed/nonfinite/out-of-range path numbers, invalid arity and excessive segments.

`manual-control.svg` is a separately written literal control in dependency order C, B, A, radial leaf. The transformer must equal those bytes. `altered-stop.svg` changes the middle shared stop from green to yellow and must fail the pixel equality oracle. Unit controls include a wrong/missing dependency, cycles, radial bases, loss of stop bytes and unsafe XML/style forms.

The blank native SIF only specifies an empty 560×200 canvas with the same 60-pixels-per-unit view box used by the pinned importer. It does not contain the imported artwork, gradients or a replacement importer.

## Genuine Synfig consumer/producer

The hosted Ubuntu 22.04 workflow downloads the official digest-pinned 1.5.5 AppImage, extracts its verified type-1 ISO9660 archive without executing the runtime, verifies source blob identities and records the actual CLI version, original GUI/CLI/launcher/module hashes and paths. The original application is unchanged. The GUI uses the original official synfigstudio ELF and the supported SYNFIG_USER_SETTINGS override with disposable per-case XDG directories on ordinary Xvfb/Openbox. Inherited HOME is retained; no home directory variable is repurposed. The CLI uses the vendor wrapper when present, otherwise its original ELF with process-local vendor library/module paths following the published launcher variables. No OS security policy, sandbox, account, real user profile or real artwork is changed.

For original, repaired, manual-control and altered-stop cases, normal keyboard File→Import selects the actual SVG file. The GUI saves an editable SIF. Assertions reject retained svg_layer, bitmap import layers or filename parameters and require the closed paths to be native vector regions. Original must have zero gradient layers; repaired/control must have exactly two linear and one radial layer, each with the complete literal three-stop table. Altered-stop must carry the exact yellow middle stop.

The imported temporary SVG is then made unavailable. A fresh GUI process opens the saved SIF and saves a new SIF. The native structure and stops must survive. Both saved files are rendered by the same official Synfig CLI, one frame, one thread. The two renders must be pixel-identical for each case. Repaired must exactly match the independent ordered control; original must differ substantially and have the expected black samples. The altered stop must create a substantial controlled difference. The control must contain meaningful nonuniform colored gradients, preventing blank-output equality from passing.

## Independent browser semantics

Sandboxed Chromium opens the actual SVG files offline and captures 560×200 RGBA pixels. Original, repaired and manual control must be exactly identical within the browser, independently of Synfig’s rendering conventions. The altered stop must differ. All actual optimizer outputs are also rendered and compared, with their dependency orders, IDs and shared edges reported. Browser errors, console errors, external requests and actual launch arguments are retained; sandbox-disabling flags are rejected.

There is no cross-engine full-pixel equality claim: native gamma and rendering conventions can differ. The two native outputs compare to each other, and browser outputs compare to each other.

## Inkscape alternative

A separate bounded step executes the unmodified officially installed Inkscape SIF exporter on original and manual-control SVGs, in a disposable profile. It records actual version and extension-file hashes. Both SIFs must contain three editable gradients and render identically through the pinned Synfig CLI. This is an explicit alternative, not an attempt to claim that all other tools fail. Its execution remains pending.

## Distribution

Only original source, dependency locks, notices, synthetic fixtures, small comparison outputs and evidence metadata are in the source archive. Native application/optimizer/browser executables, extracted packages, their source trees, caches and profiles stay outside published source and uploaded evidence. CI artifacts contain only synthetic SVG/SIF/PNG results, reports and diagnostic logs. Original code remains without a license grant.
