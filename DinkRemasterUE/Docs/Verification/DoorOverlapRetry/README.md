# Door overlap retry checkpoint

Returning inside can leave Dink already overlapping the exit trigger while the warp guard suppresses its initial overlap event. Deliberate movement afterward never raises a second BeginOverlap, so he must walk away before exiting again.

The change retries only enabled walk_in door/exit overlaps with fresh movement intent from the current frame. It preserves the original cooldown and recursion guard, rechecks nohard suppression, physical source screen, ownership, frozen/dead/stale-input conditions and makes at most one eligible attempt per poll. Existing script movement and other warp types retain their behavior. No geometry, spawn, Data or cooldown values change.

Root Editor and Development Game builds succeed with zero compiler warnings. Root full153/153 passes with zero test warnings in498.917s; all9,241 inputs remain unchanged. The author also passed full153 and the existing hard0/nohard1 test, then verified actual idle overlap does not bounce and real W exits once without first leaving that overlap. That game closes normally with9,245 inputs unchanged. Independent source review confirms all five Root files match the reviewed80cc patch and validates engine callback ordering.

Tangent, zero-approach and two-blocked-candidate native cases are not claimed as tested. Root integration delivery, source-only master21 reconciliation, final source audit and PR review remain pending at this checkpoint. Raw author fixture failures and paths retain their historical scope; the real-input proof belongs to the author stage, while combined native153 was rerun in Root.
