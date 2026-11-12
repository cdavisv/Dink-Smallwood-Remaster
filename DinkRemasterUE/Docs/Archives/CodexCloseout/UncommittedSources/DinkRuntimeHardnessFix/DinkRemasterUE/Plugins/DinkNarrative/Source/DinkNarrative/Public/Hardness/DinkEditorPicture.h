#pragma once
#include <cstdint>

namespace DinkHardness
{
// dink.cpp change_edit(unsigned short*) / change_edit_char(unsigned char*).
// -1 reads; other signed values wrap to the original unsigned storage width.
inline std::int32_t ChangeEditorPicture(int Placement, bool Sequence,
                                       std::int32_t Value, std::int32_t& Stored)
{
    if (Placement < 1 || Placement > 99) return -1;
    if (Value != -1)
        Stored = Sequence ? static_cast<std::uint16_t>(Value) : static_cast<std::uint8_t>(Value);
    return Stored;
}
}
