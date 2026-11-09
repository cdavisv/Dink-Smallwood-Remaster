# Optional physical-element navigation

New physical art elements may specify `can_affect_navigation` as a JSON boolean. Omission leaves inherited navigation untouched; strings, numbers, null, arrays and objects are rejected before any manifest replacement, hiding or spawn. False is set before completing the actor transform and assigning its mesh; true is set after setup. The existing collision profile, channels and overlap policy are retained.

This is confined to physical `elements`. Fireplace/replacement cards and render-only contexts are unchanged; no asset, art-reference or scene Data file is edited. A private in-memory overload shares the file loader path and lets native tests exercise complete manifests without writing fixture Data.

Own Editor/Game builds pass with zero compiler diagnostics. Focused2/2 and full168/168 pass with0 warning tests. Source/fixture13582 pins and native11738 pins remain unchanged; all seven custom Editor DLLs resolve to this checkout and retain hashes through Game/full. Exact commands, source/module hashes and raw report seal are in `validation.json`. Source audit passes. Native coverage includes the actual legacy spawn default, explicit overrides, actual profile/all-channel responses, placement/tags/registration, replacement navigation isolation and whole-manifest rejection for seven invalid value types. No class-default/template mutations are needed.

No GPU or new roof/exterior/hero acceptance is claimed. This delivery is authorized only through a draft PR; coordinating independent review precedes merge.

Preserved failures: initial assertion template deduction compile error, then a test fixture assumption about runtime CDO inheritance. Diagnostic native output proved the absence case follows the constructor/legacy spawn result. Final coverage uses an actual unmodified legacy spawn as its reference; explicit false and true behavior and all seven invalid-type atomic rejections pass. No product assertions were relaxed or runtime policy changed to accommodate the fixture. Raw attempts remain under Saved/NavPolicy/{Run,Retry1,Diagnostic1,Final}.
