#pragma once

// Engine-independent transition core. Not wired into legacy-world collision yet;
// see Docs/Verification/RuntimeHardness/MIGRATION.md for the admission contract.
#include <algorithm>
#include <cstdint>
#include <optional>
#include <utility>
#include <vector>

namespace DinkHardness
{
struct Rect
{
    int Left, Top, Right, Bottom; // map pixels, exclusive right/bottom
};
struct Stamp
{
    Rect Bounds;
    std::uint8_t Code; // 100 + editor index, or 1 for a dynamic sprite
};
struct OwnedRect
{
    Rect Bounds;
    std::uint8_t Code;
};

// Callers supply background stamps followed by active stamps, each in original
// que-or-y order (ties by original index), AFTER update_play_changes. Never
// infer a tile base by clearing owner bytes in an already-composed map.
class Layers
{
public:
    static constexpr int Width = 600;
    static constexpr int Height = 400;
    using Pixels = std::vector<std::uint8_t>;

    static std::optional<Layers> Create(Pixels TileBase, const std::vector<Stamp>& InitialStamps)
    {
        if (TileBase.size() != Width * Height || !ValidStamps(InitialStamps) ||
            std::any_of(TileBase.begin(), TileBase.end(), [](std::uint8_t C) { return C > 3; }))
            return std::nullopt;
        Layers Result(std::move(TileBase));
        Result.Apply(InitialStamps);
        return Result;
    }

    // sp_hard does NOT call this. draw_hard_sprite restores only the CURRENT
    // explicit pseq/pframe box, then re-stamps ALL eligible sprites globally.
    // This deliberately retains original stale pixels outside the clear box.
    bool Redraw(Rect ClearPictureBox, const std::vector<Stamp>& OrderedStamps)
    {
        if (!ValidStamps(OrderedStamps)) return false; // transactional refusal
        const Rect R = Clip(ClearPictureBox);
        for (int Y = R.Top; Y < R.Bottom; ++Y)
            for (int X = R.Left; X < R.Right; ++X)
                Current[Y * Width + X] = Base[Y * Width + X];
        Apply(OrderedStamps);
        return true;
    }

    int Get(int X, int Y) const
    {
        return X < 0 || X >= Width || Y < 0 || Y >= Height ? 0 : Current[Y * Width + X];
    }
    const Pixels& GetPixels() const { return Current; }

    // Deterministic exact raster partition, with owner/code retained. Consumers
    // may update owner collision without merging it with walls/floor/fill.
    // No approximate bounding rectangle may replace the returned union.
    std::vector<OwnedRect> CollisionRects() const
    {
        std::vector<OwnedRect> Result;
        std::vector<std::size_t> Previous;
        for (int Y = 0; Y < Height; ++Y)
        {
            std::vector<std::size_t> ThisRow;
            for (int X = 0; X < Width;)
            {
                const int Start = X;
                const auto Code = Current[Y * Width + X++];
                while (X < Width && Current[Y * Width + X] == Code) ++X;
                if (!Code) continue;
                auto Match = std::find_if(Previous.begin(), Previous.end(), [&](std::size_t I) {
                    const auto& P = Result[I];
                    return P.Code == Code && P.Bounds.Left == Start && P.Bounds.Right == X;
                });
                if (Match == Previous.end())
                {
                    Result.push_back({{Start, Y, X, Y + 1}, Code});
                    ThisRow.push_back(Result.size() - 1);
                }
                else
                {
                    Result[*Match].Bounds.Bottom = Y + 1;
                    ThisRow.push_back(*Match);
                }
            }
            Previous = std::move(ThisRow);
        }
        return Result;
    }

private:
    Pixels Base, Current;
    explicit Layers(Pixels TileBase) : Base(std::move(TileBase)), Current(Base) {}
    static Rect Clip(Rect R)
    {
        R.Left = std::max(0, std::min(Width, R.Left));
        R.Right = std::max(0, std::min(Width, R.Right));
        R.Top = std::max(0, std::min(Height, R.Top));
        R.Bottom = std::max(0, std::min(Height, R.Bottom));
        return R;
    }
    static bool ValidStamps(const std::vector<Stamp>& Stamps)
    {
        for (const auto& S : Stamps)
            if (!(S.Code == 1 || (S.Code >= 101 && S.Code <= 199)))
                return false;
        return true;
    }
    void Apply(const std::vector<Stamp>& Stamps)
    {
        for (const auto& S : Stamps)
        {
            const Rect R = Clip(S.Bounds);
            for (int Y = R.Top; Y < R.Bottom; ++Y)
                for (int X = R.Left; X < R.Right; ++X)
                    Current[Y * Width + X] = S.Code;
        }
    }
};
}
