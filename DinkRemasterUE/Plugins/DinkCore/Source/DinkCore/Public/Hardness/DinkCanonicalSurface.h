#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <vector>

/** Versioned exact oriented surface encoding. IEEE float bits (including signed zero),
 * material indices, duplicate triangles and winding are retained. Only triangle order
 * and cyclic vertex numbering are removed. All integer bytes are explicitly little endian. */
namespace DinkCanonicalSurface
{
using Point = std::array<float, 3>;
struct Triangle { std::array<Point, 3> Points; std::uint16_t Material = 0; };
using Record = std::array<std::uint8_t, 38>;
inline std::vector<std::uint8_t> Bytes(const std::vector<Triangle>& Triangles, bool EffectiveCull)
{
    static_assert(sizeof(float) == 4, "surface contract requires float32");
    std::vector<Record> Records;
    Records.reserve(Triangles.size());
    for (const auto& Triangle : Triangles)
    {
        Record Best{};
        for (unsigned Rotation = 0; Rotation < 3; ++Rotation)
        {
            Record Candidate{};
            unsigned Offset = 0;
            for (unsigned Vertex = 0; Vertex < 3; ++Vertex)
                for (float Value : Triangle.Points[(Vertex + Rotation) % 3])
                {
                    std::uint32_t Bits;
                    std::memcpy(&Bits, &Value, sizeof(Bits));
                    for (unsigned Byte = 0; Byte < 4; ++Byte)
                        Candidate[Offset++] = std::uint8_t(Bits >> (8 * Byte));
                }
            Candidate[36] = std::uint8_t(Triangle.Material);
            Candidate[37] = std::uint8_t(Triangle.Material >> 8);
            if (Rotation == 0 || Candidate < Best) Best = Candidate;
        }
        Records.push_back(Best);
    }
    std::sort(Records.begin(), Records.end());
    constexpr char Domain[] = "DinkOrientedTrianglesF32LEMaterialU16LE/1";
    std::vector<std::uint8_t> Result(Domain, Domain + sizeof(Domain)); // includes exactly one NUL
    Result.push_back(EffectiveCull ? 1 : 0);
    const auto Count = static_cast<std::uint32_t>(Records.size());
    for (unsigned Byte = 0; Byte < 4; ++Byte) Result.push_back(std::uint8_t(Count >> (8 * Byte)));
    for (const auto& Record : Records) Result.insert(Result.end(), Record.begin(), Record.end());
    return Result;
}
}
