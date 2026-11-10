# Authored screen architecture family identity

The original game has no exposed interior roof sprite family. Fabricating a sprite ID for new3D roof adaptation would misstate its source identity. The owner-authorized narrow exemption requires an explicit `authored_architecture` declaration, an allowed kit class and inspection of every actual runtime mesh reference. It never exempts props by name.

Allowed classes are `kit_ceiling`, `kit_wall`, `kit_piece`; screens must be unique positive integers and purpose nonempty. Every actual occurrence must be direct `dink-art/1` `elements[].mesh` on a declared screen. Family, replacement, asset-list, nested-element, context, different-screen and unknown-schema uses refuse this exemption. Existing unrelated terrain/render-context policies are unchanged. Material, triangle, texture, collision and gameplay requirements remain independent.

Ten focused regressions pass, including all3 allowed classes and negative declaration/class/screen/use cases. The combined worktree with the companion pending roof source records checks441 assets: existing186material/23family violations remain. It resolves8 roof family findings introduced by truthful new records; it does not waive unrelated findings or establish native acceptance. Source-only, no UE execution.
