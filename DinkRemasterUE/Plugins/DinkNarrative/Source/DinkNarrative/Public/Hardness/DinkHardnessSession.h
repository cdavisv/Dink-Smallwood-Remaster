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
    std::vector<Stamp> FittedStamps; // optional exact row-runs for THIS instance, kept in sorted order
    bool bFittedStamp=false; // explicit empty replacement must not fall back to old rectangle
    SpriteState(int I,int O,int YIn,int Q,int H,bool A,Rect R,std::vector<Stamp> F={})
        :Index(I),EditorOwner(O),Y(YIn),Que(Q),Hard(H),Active(A),Picture(R),FittedStamps(std::move(F)){}
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
            if (S.bFittedStamp || !S.FittedStamps.empty()) Result.insert(Result.end(), S.FittedStamps.begin(), S.FittedStamps.end());
            else Result.push_back({S.Picture, static_cast<std::uint8_t>(S.EditorOwner ? 100 + S.EditorOwner : 1)});
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
struct FittedGeometry
{
    virtual ~FittedGeometry() = default;
    virtual bool Current() const noexcept = 0;
    virtual const void* BackendTag() const noexcept = 0;
};
struct FittedOwner
{
    std::uint8_t Code;
    std::uintptr_t InstanceId; // actor instance identity, NOT editor code
    std::shared_ptr<const FittedGeometry> Geometry;
    std::vector<int> Cells; // sorted unique Y*600+X cell-centre footprint
};
// Remove only the fitted footprint of a code, never unrelated same-code cells.
// Geometry/body validation is the backend's separate obligation.
inline std::optional<std::vector<OwnedRect>> FittedRasterRects(
    const std::vector<OwnedRect>& Rects,const std::vector<FittedOwner>& Fits,
    const std::vector<std::uint8_t>& Suppressed)
{
    std::vector<std::pair<std::uint8_t,std::vector<std::uint8_t>>> Masks;
    for(const auto& F:Fits)
    {
        if(F.Code<101 || F.Code>199 || F.Cells.empty())return std::nullopt;
        auto Found=std::find_if(Masks.begin(),Masks.end(),[&](const auto& M){return M.first==F.Code;});
        if(Found==Masks.end()){Masks.emplace_back(F.Code,std::vector<std::uint8_t>(240000,0));Found=Masks.end()-1;}
        int Previous=-1;
        for(int Cell:F.Cells)
        {
            if(Cell<=Previous || Cell>=Layers::Width*Layers::Height)return std::nullopt;
            // Different codes can overlap; retain a per-code mask below rather
            // than claiming the top owner's byte tells us all contributors.
            Previous=Cell;Found->second[Cell]=1;
        }
    }
    for(auto Code:Suppressed)if(Code<101 || Code>199)return std::nullopt;
    std::vector<OwnedRect> Out;
    for(const auto& R:Rects)
    {
        if(R.Bounds.Left<0 || R.Bounds.Top<0 || R.Bounds.Right>600 || R.Bounds.Bottom>400 ||
           R.Bounds.Left>=R.Bounds.Right || R.Bounds.Top>=R.Bounds.Bottom)return std::nullopt;
        if(std::find(Suppressed.begin(),Suppressed.end(),R.Code)!=Suppressed.end())continue;
        const auto Found=std::find_if(Masks.begin(),Masks.end(),[&](const auto& M){return M.first==R.Code;});
        if(Found==Masks.end()){Out.push_back(R);continue;}
        const auto& Mask=Found->second;
        for(int Y=R.Bounds.Top;Y<R.Bounds.Bottom;++Y)
            for(int X=R.Bounds.Left;X<R.Bounds.Right;)
            {
                if(Mask[Y*600+X]){++X;continue;}
                const int Begin=X++;while(X<R.Bounds.Right && !Mask[Y*600+X])++X;
                Out.push_back({{Begin,Y,X,Y+1},R.Code});
            }
    }
    return Out;
}
struct PhysicsOwner
{
    virtual ~PhysicsOwner() = default;
    virtual int Version() const noexcept = 0;
    virtual const void* BackendTag() const noexcept { return nullptr; }
    virtual void InvalidateForScreenRebuild() noexcept = 0;
    virtual bool HasAdmittedBaseline() const noexcept = 0;
    virtual std::uintptr_t GetWorldCookie() const noexcept = 0;
    virtual int GetScreen() const noexcept = 0;
    virtual int GetVision() const noexcept = 0;
    virtual bool IsAuthoredScreen() const noexcept = 0;
    virtual std::unique_ptr<PreparedPhysics> Prepare(const std::vector<OwnedRect>& Candidate) = 0;
    virtual std::unique_ptr<PreparedPhysics> PrepareFitted(const std::vector<OwnedRect>& Candidate,
        const std::vector<FittedOwner>& Fits, const std::vector<std::uint8_t>& SuppressedCodes)
    { return Fits.empty() && SuppressedCodes.empty() ? Prepare(Candidate) : nullptr; }
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
    bool RedrawFitted(const std::vector<int>& ClearCells, const std::vector<Stamp>& Stamps,
                      PhysicsOwner& Physics, const std::vector<FittedOwner>& Fits,
                      const std::vector<std::uint8_t>& SuppressedCodes,
                      void* ExternalContext = nullptr, PreparedPhysics::PublishFn ExternalPublish = nullptr)
    {
        if (Physics.Version()!=1 || !Physics.HasAdmittedBaseline() || Physics.IsAuthoredScreen() ||
            Physics.GetScreen()!=Screen || Physics.GetVision()!=Vision) return false;
        auto Candidate=Map;
        if (!Candidate.RedrawCells(ClearCells,Stamps)) return false;
        auto Prepared=Physics.PrepareFitted(Candidate.CollisionRects(),Fits,SuppressedCodes);
        if (!Prepared) return false;
        struct Publication { Layers* Target; Layers* Candidate; bool Published;
            void* Context; PreparedPhysics::PublishFn Publish; };
        Publication P{&Map,&Candidate,false,ExternalContext,ExternalPublish};
        const bool Committed=Prepared->Commit(&P,[](void* C) noexcept {
            auto& S=*static_cast<Publication*>(C); if(S.Published)return;
            *S.Target=std::move(*S.Candidate);S.Published=true;if(S.Publish)S.Publish(S.Context);
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
