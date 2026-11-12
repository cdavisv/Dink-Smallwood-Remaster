#pragma once
#include "DinkHardnessLayers.h"
#include <memory>
#include <type_traits>

namespace DinkHardness
{
struct SpriteState
{
    int Index; // original editor index for backgrounds; original runtime handle for live sort ties
    int EditorOwner; // 0 dynamic; 1..99 editor placement
    int Y;
    int Que;
    int Hard;
    bool Active;
    Rect Picture; // resolved getpic() stamp box, already map x-20
};

inline std::optional<std::vector<Stamp>> OrderedStamps(std::vector<SpriteState> Background,
                                      std::vector<SpriteState> Live)
{
    for (const auto& S : Background)
        if (S.Index < 1 || S.Index > 99 || S.EditorOwner != S.Index) return std::nullopt;
    for (const auto& S : Live)
        if (S.Index < 1 || S.EditorOwner < 0 || S.EditorOwner > 99) return std::nullopt;
    std::vector<Stamp> Result;
    auto Append = [&Result](std::vector<SpriteState>& Sprites, int Ceiling) {
        std::sort(Sprites.begin(), Sprites.end(), [](const auto& A, const auto& B) {
            const int AY = A.Que != 0 ? A.Que : A.Y, BY = B.Que != 0 ? B.Que : B.Y;
            return AY != BY ? AY < BY : A.Index < B.Index;
        });
        for (const auto& S : Sprites)
        {
            const int Key = S.Que != 0 ? S.Que : S.Y;
            if (!S.Active || S.Hard != 0 || Key >= Ceiling) continue;
            Result.push_back({S.Picture, static_cast<std::uint8_t>(S.EditorOwner ? 100 + S.EditorOwner : 1)});
        }
    };
    Append(Background, 20000); // original background ranking sentinel
    Append(Live, 22024);      // original live ranking sentinel
    return Result;
}

// Prepare constructs and validates REGISTERED inert bodies. Commit must acquire
// the scene transaction before changing shape filters, and invoke Publish once
// within that transaction only after the physical exchange succeeds. Refusal
// invokes no Publish and leaves old shapes active. UE body registration and
// preparation are allowed to allocate/fail; no infallible UObject toggle is assumed.
struct PreparedPhysics
{
    virtual ~PreparedPhysics() = default;
    using PublishFn = void(*)(void*) noexcept;
    virtual bool Commit(void* Context, PublishFn Publish) noexcept = 0;
};
struct PhysicsOwner
{
    virtual ~PhysicsOwner() = default;
    virtual int Version() const noexcept = 0;
    virtual void InvalidateForScreenRebuild() noexcept = 0;
    virtual bool HasAdmittedBaseline() const noexcept = 0;
    virtual std::uintptr_t GetWorldCookie() const noexcept = 0;
    virtual int GetScreen() const noexcept = 0;
    virtual int GetVision() const noexcept = 0;
    virtual bool IsAuthoredScreen() const noexcept = 0;
    virtual std::unique_ptr<PreparedPhysics> Prepare(const std::vector<OwnedRect>& Candidate) = 0;
};

// One instance per world/screen/vision. Never mutate FDinkGameplayData's source
// cache; reset/vision/reentry must explicitly create the appropriate session.
class Session
{
public:
    static std::optional<Session> Create(Layers::Pixels Base,
                                        const std::vector<Stamp>& Initial,
                                        int Screen, int Vision)
    {
        auto Map = Layers::Create(std::move(Base), Initial);
        if (!Map || Screen < 1 || Screen > 768) return std::nullopt;
        return Session(std::move(*Map), Screen, Vision);
    }
    static std::optional<Session> CreateProjected(Layers Projected, int Screen, int Vision)
    {
        if (Screen < 1 || Screen > 768) return std::nullopt;
        return Session(std::move(Projected), Screen, Vision);
    }
    static_assert(std::is_nothrow_move_assignable<Layers>::value, "logical publication must not fail");
    bool Redraw(Rect ClearPicture, const std::vector<Stamp>& Stamps, PhysicsOwner& Physics,
                void* ExternalContext = nullptr, PreparedPhysics::PublishFn ExternalPublish = nullptr)
    {
        if (Physics.Version() != 1 || !Physics.HasAdmittedBaseline() || Physics.IsAuthoredScreen() ||
            Physics.GetScreen() != Screen || Physics.GetVision() != Vision) return false;
        auto Candidate = Map; // all allocations and validation BEFORE physics commit
        if (!Candidate.Redraw(ClearPicture, Stamps)) return false;
        auto Rects = Candidate.CollisionRects();
        auto Prepared = Physics.Prepare(Rects);
        if (!Prepared) return false;
        struct Publication {
            Layers* Target; Layers* Candidate; bool Published;
            void* ExternalContext; PreparedPhysics::PublishFn ExternalPublish;
        };
        Publication P{&Map, &Candidate, false, ExternalContext, ExternalPublish};
        const bool Committed = Prepared->Commit(&P, [](void* Context) noexcept {
            auto& State = *static_cast<Publication*>(Context);
            if (State.Published) return;
            *State.Target = std::move(*State.Candidate);
            State.Published = true;
            if (State.ExternalPublish) State.ExternalPublish(State.ExternalContext);
        });
        return Committed && P.Published;
    }
    int Get(int X, int Y) const { return Map.Get(X, Y); }
    int GetScreen() const { return Screen; }
    int GetVision() const { return Vision; }
    const Layers::Pixels& Pixels() const { return Map.GetPixels(); }
private:
    Session(Layers M, int S, int V) : Map(std::move(M)), Screen(S), Vision(V) {}
    Layers Map;
    int Screen, Vision;
};
}
