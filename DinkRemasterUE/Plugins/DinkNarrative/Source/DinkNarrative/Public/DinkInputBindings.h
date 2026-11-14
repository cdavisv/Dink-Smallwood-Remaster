#pragma once

#include "CoreMinimal.h"
#include "InputCoreTypes.h"

/**
 * The narrative layer's controls (FDinkNarrativeInputProcessor), keyboard and a standard gamepad, as data so they can be tested.
 * The original's controls: Ctrl attack, Space talk, Shift magic, arrows move, Enter the item screen, Esc the menu. The remaster keeps
 * F / Left Ctrl, E and Q on the keyboard (Space jumps, Shift is the run key). Gamepad (Xbox names):
 *   X or Right Trigger   attack (held: draws the bow; released: shoots)
 *   B                    talk
 *   Y                    magic
 *   A                    pick in a menu, skip the waited-on text; otherwise it stays the jump (the character's own mapping)
 *   D-pad / left stick   up and down move a menu's highlight (outside a menu the d-pad zooms the camera, the stick walks)
 * Movement, camera, run (left shoulder) and jump (A) are the character's Enhanced Input mappings. There is no item screen and no
 * escape menu in the remaster yet, so Enter / Start / Esc have nothing to open.
 */
namespace DinkInput
{
	enum class EAction : uint8 { Confirm, MenuUp, MenuDown, Talk, Attack, Magic };

	/** Every (key, action) pair, keyboard and gamepad. */
	DINKNARRATIVE_API const TArray<TPair<FKey, EAction>>& Bindings();
	/** True when Key is bound to Action. */
	DINKNARRATIVE_API bool IsBound(const FKey& Key, EAction Action);
}
