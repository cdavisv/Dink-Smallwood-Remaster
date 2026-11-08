# Starting-house exterior-context candidate

This branch contains source/native/import work for views through the original house openings. It does not publish a runtime Data layer.

The immutable source bundle has139 pinned payloads plus its bundle manifest. It supplies54 terrain packages and1 doorstep,17,604triangles;316 render-only components reference62 meshes. Existing material/shared-mesh references are reused. The importer documents the original Meadow path alias and preserves the Props doorstep catalogue path.

Native real-PIE visibility/NoCollision/lifecycle checks pass. Independent review caught and fixed same-room controller replacement with one bounded actor-level timer; there are no per-mesh ticks. Native sources and original assets remain unchanged outside the candidate additions.

Private editor import and separate check pass; all55package bytes stay unchanged during check. Loaded-world geometry audit passes644rooms/643other rooms,316placements,62meshes,zero confirmed room intrusions/neighbor overlaps andunchanged protected hashes. Fifteen threshold samples have ground/step coverage. Actual rendered window/door acceptance is pending. Source collars, distant backdrop composition and material finish remain candidates.

The source bundle keeps its original pre-import README/proposal as frozen provenance; this document records current verification state.
