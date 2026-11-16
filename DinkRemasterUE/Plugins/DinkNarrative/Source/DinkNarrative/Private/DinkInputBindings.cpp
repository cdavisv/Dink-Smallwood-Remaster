#include "DinkInputBindings.h"

namespace DinkInput
{
	const TArray<TPair<FKey, EAction>>& Bindings()
	{
		static const TArray<TPair<FKey, EAction>> Table = {
			{ EKeys::Enter, EAction::Confirm }, { EKeys::SpaceBar, EAction::Confirm }, { EKeys::E, EAction::Confirm },
			{ EKeys::Gamepad_FaceButton_Bottom, EAction::Confirm },
			{ EKeys::Up, EAction::MenuUp }, { EKeys::W, EAction::MenuUp }, { EKeys::Gamepad_DPad_Up, EAction::MenuUp }, { EKeys::Gamepad_LeftStick_Up, EAction::MenuUp },
			{ EKeys::Down, EAction::MenuDown }, { EKeys::S, EAction::MenuDown }, { EKeys::Gamepad_DPad_Down, EAction::MenuDown }, { EKeys::Gamepad_LeftStick_Down, EAction::MenuDown },
			{ EKeys::E, EAction::Talk }, { EKeys::Gamepad_FaceButton_Right, EAction::Talk },
			{ EKeys::F, EAction::Attack }, { EKeys::LeftControl, EAction::Attack }, { EKeys::Gamepad_FaceButton_Left, EAction::Attack }, { EKeys::Gamepad_RightTrigger, EAction::Attack },
			{ EKeys::Q, EAction::Magic }, { EKeys::Gamepad_FaceButton_Top, EAction::Magic },
			{ EKeys::Escape, EAction::MainMenu }, { EKeys::Gamepad_Special_Right, EAction::MainMenu },
			{ EKeys::M, EAction::Map }, { EKeys::Gamepad_Special_Left, EAction::Map },
			{ EKeys::Enter, EAction::Inventory }, { EKeys::I, EAction::Inventory },
			// The original's button 4 is the item screen (default button[u] = u, dink.cpp:18048; human_brain 14946-14960).
			{ EKeys::Gamepad_RightShoulder, EAction::Inventory },
		};
		return Table;
	}

	bool IsBound(const FKey& Key, EAction Action)
	{
		for (const TPair<FKey, EAction>& B : Bindings())
		{
			if (B.Key == Key && B.Value == Action)
			{
				return true;
			}
		}
		return false;
	}
}
