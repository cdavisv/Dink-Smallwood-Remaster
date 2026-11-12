#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <vector>
#include <optional>
#include <utility>

/** Exact indexed geometry values; independent of Chaos's internal face ordering.
 * Particle float bits stay indexed and exact. Faces retain winding, material,
 * external-face association (including -1) and duplicate multiplicity. */
namespace DinkCookedMeshIdentity
{
using ParticleBits = std::array<std::uint32_t, 3>;
struct Face
{
    std::array<std::uint32_t, 3> Indices{};
    std::uint16_t Material = 0;
    std::int32_t ExternalFace = -1;
    bool operator==(const Face& Other) const
    { return Indices == Other.Indices && Material == Other.Material && ExternalFace == Other.ExternalFace; }
};
struct Snapshot
{
    bool LargeIndices = false;
    std::vector<ParticleBits> Particles;
    std::vector<Face> Faces;
    bool operator==(const Snapshot& Other) const
    { return LargeIndices == Other.LargeIndices && Particles == Other.Particles && Faces == Other.Faces; }
};
using Association = std::array<std::uint8_t, 18>;
inline std::vector<Association> Associations(const Snapshot& Value)
{
    std::vector<Association> Result;
    Result.reserve(Value.Faces.size());
    for (const auto& Item : Value.Faces)
    {
        Association Best{};
        for (unsigned Rotation = 0; Rotation < 3; ++Rotation)
        {
            Association Encoded{};
            unsigned Offset = 0;
            for (unsigned Corner = 0; Corner < 3; ++Corner)
            {
                const auto Index = Item.Indices[(Corner + Rotation) % 3];
                for (unsigned Byte = 0; Byte < 4; ++Byte) Encoded[Offset++] = std::uint8_t(Index >> (8 * Byte));
            }
            Encoded[12] = std::uint8_t(Item.Material); Encoded[13] = std::uint8_t(Item.Material >> 8);
            const auto External = static_cast<std::uint32_t>(Item.ExternalFace);
            for (unsigned Byte = 0; Byte < 4; ++Byte) Encoded[14 + Byte] = std::uint8_t(External >> (8 * Byte));
            if (Rotation == 0 || Encoded < Best) Best = Encoded;
        }
        Result.push_back(Best);
    }
    std::sort(Result.begin(), Result.end());
    return Result;
}
inline bool ValidIndices(const Snapshot& Value)
{
    if (Value.Particles.empty() || Value.Faces.empty()) return false;
    for (const auto& Item : Value.Faces)
        for (auto Index : Item.Indices) if (Index >= Value.Particles.size()) return false;
    return true;
}
inline bool SameAssociations(const Snapshot& A, const Snapshot& B)
{
    return ValidIndices(A) && ValidIndices(B) && A.LargeIndices == B.LargeIndices &&
        A.Particles == B.Particles && A.Faces.size() == B.Faces.size() && Associations(A) == Associations(B);
}
struct Admission
{
    Snapshot Source, Owned;
};
inline std::optional<Admission> Admit(Snapshot Source, Snapshot Owned)
{
    if (!SameAssociations(Source, Owned)) return std::nullopt;
    return Admission{std::move(Source), std::move(Owned)};
}
inline bool MatchesOrdered(const std::optional<Admission>& Prepared, const Snapshot& Source, const Snapshot& Owned)
{
    return Prepared && Prepared->Source == Source && Prepared->Owned == Owned;
}

}
