# GradBefore

A small, offline, order-only repair for a specific Synfig SVG import limitation: a gradient may inherit shared stops only when its linear base appears earlier in the document. GradBefore places each base before its dependents inside one `defs` block. It retains every gradient’s original bytes, ID, links, stops and attributes, and leaves all non-gradient bytes and artwork order untouched.

**Native-feasibility candidate.** The bounded source transformer and literal fixture tests pass locally. Actual Synfig GUI import/save/fresh reopen/render and browser pixel comparisons have not run yet. There is no product UI or completed compatibility claim. The hosted gate must reproduce the original failure and match the independently hand-ordered control before UI work proceeds.

## Source CLI

Use Node.js 22:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm test
node src/cli.mjs input.svg --out repaired.svg --report review.json
```

Inputs and outputs must be different paths. Outputs must not already exist. The CLI reads only the named local file and writes a new SVG plus a dependency/move report with input/output hashes. It does not launch Synfig, render imported content, follow URLs, modify the original, execute code or install anything. If writing the second output fails, the first may already exist; existing files are never overwritten.

Already ordered files produce byte-identical SVG output. Changed files move whole gradient blocks between existing slots; whitespace/comments between those slots stay where they were. A second parse verifies every gradient block and every outside segment is unchanged.

## Supported static profile

- One UTF-8 XML 1.0 SVG document, one direct `defs` block containing only `linearGradient` and `radialGradient` children, and plain static groups/path/basic-shape artwork. Unicode, newline spelling, comments, BOM and quote choices are preserved.
- Gradient IDs are unique, bounded ASCII identifiers; any other supplied IDs must also be unique. Dependencies use a single `href="#id"` or canonical `xlink:href="#id"` spelling. Every referenced base must be a local **linear** gradient. A radial gradient may be a leaf that inherits linear stops; radial bases are rejected because this Synfig importer does not look them up.
- A base has explicit stop colors and numeric offsets from 0 to 1. A referencing gradient has no own stops. Painted gradients require complete numeric geometry and `gradientUnits="userSpaceOnUse"`. Radial focus must equal its center. Only `pad` spread is accepted. Inherited-only gradient transforms on painted gradients reject; the original importer reads only their own transform. These limits avoid presenting an order fix as a repair for unsupported inheritance, focus, units or spread behavior.
- Canvas width/height are bounded numbers. Standard static transform forms and a small explicit presentation-style vocabulary are accepted; style sheets/selectors, dynamic CSS, scripts, events, animation, images, `use`, foreign XML, filters, clipping, unknown elements/attributes, DTD/entity declarations, processing instructions, external references, multiple defs, unresolved references and cycles reject. Editor-specific metadata may require a plain SVG export first.
- Limits: 1 MiB input, 8,192 XML elements, depth 32, 512 gradients, 128 stops per base, dependency depth 64, ordinary attribute length 8,192 and path data length 65,536 and 4,096 segments per path. Path numbers are tokenized, finite and bounded; arc flags must be separately represented zero/one values. Oversize or unsupported files fail closed.

This is neither a general SVG sanitizer nor a guarantee of full Synfig visual fidelity. Known 1.5.5 shape-gradient clipping behavior is outside this fix; the native fixture deliberately uses closed paths. The transformation only changes dependency order in the supported static profile.

## Existing tools and differentiation

The demand is [Synfig issue #3752](https://github.com/synfig/synfig/issues/3752). A topological ordering is standard; this is a modest workflow integration, not a new algorithm or a uniqueness claim.

Actual local tests on the committed shared-gradient fixture ran SVGO 4.0.0 (default, preserve IDs, and sortDefsChildren only), Scour 0.38.2 (default and preservation-oriented flags), and svgcleaner 0.9.5 (default, no defaults, and preserve graph). All eight outputs still contain forward dependencies. Several retain the original IDs/shared edges, but none satisfies the dependency order on this fixture. Their actual outputs and settings are retained in `evidence/optimizers/`; this is a bounded comparison, not a claim about every possible plugin or custom script.

[Inkscape’s SIF exporter](https://wiki.synfig.org/Doc:Svg2synfig) is a real recommended alternative and resolves gradient links recursively. The native gate also attempts its unmodified installed exporter on the original and ordered fixture, then compares the resulting native renders. That execution is pending. GradBefore’s proposed difference is retaining an editable SVG with shared definitions for Synfig’s SVG import, rather than converting the document into SIF or merging its gradients.

See [native acceptance method](docs/NATIVE_METHOD.md) and [primary sources](docs/RESEARCH.md). Native applications, browsers and optimizer executables are test-only and are not included in the source package. Original project code has no license grant; dependency notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
