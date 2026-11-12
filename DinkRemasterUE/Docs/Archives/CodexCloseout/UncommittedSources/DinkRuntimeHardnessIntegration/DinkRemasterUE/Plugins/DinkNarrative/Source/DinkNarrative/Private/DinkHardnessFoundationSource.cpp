#include "Hardness/DinkHardnessFoundationSource.h"
#include "Hardness/DinkHardnessShell.h"
#include "DinkGameplay.h"
#include "DinkCollision.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/CollisionProfile.h"
#include "PhysicsEngine/BodySetup.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Physics/PhysicsInterfaceCore.h"
#include "Chaos/TriangleMeshImplicitObject.h"

namespace
{
bool Number(const TSharedPtr<FJsonValue>& V,double& N)
{ if(!V || V->Type!=EJson::Number) return false; N=V->AsNumber(); return FMath::IsFinite(N); }
bool Integer(const TSharedPtr<FJsonValue>& V,int32& N)
{ double D=0; if(!Number(V,D)||D<MIN_int32||D>MAX_int32||FMath::FloorToDouble(D)!=D)return false;N=int32(D);return true; }
FString Hash(const TArray<uint8>& Bytes) { return FSHA1::HashBuffer(Bytes.GetData(),Bytes.Num()).ToString().ToLower(); }
FString Signature(const FVector3f& A,const FVector3f& B,const FVector3f& C)
{
    const FVector3f V[3]={A,B,C};FString Best;
    for(int32 R=0;R<3;++R) { FString S;
        for(int32 I=0;I<3;++I) {const auto& P=V[(I+R)%3];S+=FString::Printf(TEXT("%.9g,%.9g,%.9g;"),P.X==0?0.f:P.X,P.Y==0?0.f:P.Y,P.Z==0?0.f:P.Z);}
        if(R==0||S<Best)Best=MoveTemp(S); }
    return Best;
}
}

bool FDinkHardnessFoundationSource::Load(const FString& File,int32 ExpectedScreen,
                                        FDinkHardnessFoundationSource& Out,FString& Error)
{
    auto Fail=[&Error](const TCHAR* Why){Error=Why;return false;};
    TArray<uint8> Bytes;FString Text;TSharedPtr<FJsonObject> O;
    if(!FFileHelper::LoadFileToArray(Bytes,*File))return Fail(TEXT("foundation descriptor missing"));
    FFileHelper::BufferToString(Text,Bytes.GetData(),Bytes.Num());
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),O)||!O.IsValid())return Fail(TEXT("foundation descriptor invalid"));
    FDinkHardnessFoundationSource N;FString Schema;double Height=0;
    if(!O->TryGetStringField(TEXT("schema"),Schema)||Schema!=TEXT("dink-runtime-hardness-foundation/1")||
        !Integer(O->TryGetField(TEXT("screen")),N.Screen)||N.Screen!=ExpectedScreen||N.Screen<1||N.Screen>768||
        !Number(O->TryGetField(TEXT("height_cm")),Height)||Height!=300||
        !O->TryGetStringField(TEXT("collision_source_hash"),N.CollisionSourceHash)||N.CollisionSourceHash.IsEmpty())return Fail(TEXT("foundation schema/identity/height/source invalid"));
    N.HeightCm=float(Height);N.SourceTextSha1=Hash(Bytes);
    const TSharedPtr<FJsonObject>* Corners=nullptr;
    if(!O->TryGetObjectField(TEXT("corners"),Corners)||!Corners||!Corners->IsValid())return Fail(TEXT("foundation corners missing"));
    auto Corner=[&](const TCHAR* Key,FVector2D& Value){
        const TArray<TSharedPtr<FJsonValue>>* A=nullptr;double X=0,Y=0;
        if(!(*Corners)->TryGetArrayField(Key,A)||A->Num()!=2||!Number((*A)[0],X)||!Number((*A)[1],Y))return false;
        Value=FVector2D(X,Y);return true;};
    if(!Corner(TEXT("nw"),N.Corners.NW)||!Corner(TEXT("ne"),N.Corners.NE)||!Corner(TEXT("sw"),N.Corners.SW)||!Corner(TEXT("se"),N.Corners.SE))return Fail(TEXT("foundation corners invalid"));
    auto Rects=[&](const TCHAR* Key,TArray<FIntRect>& Values){
        const TArray<TSharedPtr<FJsonValue>>* A=nullptr;if(!O->TryGetArrayField(Key,A))return false;
        for(const auto& V:*A) { if(!V||V->Type!=EJson::Array||V->AsArray().Num()!=4)return false;
            int32 L=0,T=0,R=0,B=0;const auto& C=V->AsArray();
            if(!Integer(C[0],L)||!Integer(C[1],T)||!Integer(C[2],R)||!Integer(C[3],B)||L<0||L>=R||R>600||T<0||T>=B||B>400)return false;
            Values.Add(FIntRect(L,T,R,B)); }return true;};
    if(!Rects(TEXT("fill_solid"),N.SolidFill)||!Rects(TEXT("fill_water"),N.WaterFill)||!O->TryGetStringField(TEXT("solid_mesh"),N.SolidMesh))return Fail(TEXT("foundation fill/mesh authority invalid"));
    const FString Prefix=FString::Printf(TEXT("/Game/Dink/RuntimeHardnessV1/SCR_%03d/SM_SCR_%03d_"),N.Screen,N.Screen);
    auto Path=[&](const TCHAR* Suffix){const FString P=Prefix+Suffix;return P+TEXT(".")+FPaths::GetCleanFilename(P);};
    if(N.SolidMesh!=Path(TEXT("FixedSolidV1")))return Fail(TEXT("foundation solid path is not versioned authority"));
    const auto Low=O->TryGetField(TEXT("low_mesh"));
    if(N.WaterFill.IsEmpty()) {if(!Low||Low->Type!=EJson::Null)return Fail(TEXT("unexpected low foundation mesh"));}
    else if(!O->TryGetStringField(TEXT("low_mesh"),N.LowMesh)||N.LowMesh!=Path(TEXT("FixedLowV1")))return Fail(TEXT("low foundation path invalid"));
    const TSharedPtr<FJsonObject>* Inputs=nullptr;
    if(!O->TryGetObjectField(TEXT("gameplay_files_sha1"),Inputs)||!Inputs||!Inputs->IsValid()||(*Inputs)->Values.Num()!=3)return Fail(TEXT("foundation gameplay bindings missing"));
    for(const FString& Key:{FString(TEXT("frames.csv")),FString(TEXT("placements.csv")),FString::Printf(TEXT("Hardness/SCR_%03d_layers.json"),N.Screen)})
    {FString Digest;if(!(*Inputs)->TryGetStringField(Key,Digest)||Digest.Len()!=40)return Fail(TEXT("gameplay digest invalid"));
     for(TCHAR C:Digest)if(!FChar::IsHexDigit(C))return Fail(TEXT("gameplay digest invalid"));N.GameplaySha1.Add(Key,Digest.ToLower());}
    Out=MoveTemp(N);Error.Reset();return true;
}

bool FDinkHardnessFoundationSource::VerifyGameplayInputs(FString& Error) const
{
    for(const auto& Pair:GameplaySha1) {TArray<uint8> B;
        if(!FFileHelper::LoadFileToArray(B,*FDinkGameplayData::GetDataPath(*Pair.Key))||Hash(B)!=Pair.Value)
        {Error=TEXT("foundation and gameplay source snapshot differ: ")+Pair.Key;return false;}}
    Error.Reset();return true;
}

bool FDinkHardnessFoundationSource::VerifyInstances(ADinkScreenVolume& Volume,ADinkGreyboxScreen& Host,FString& Error,bool RequireMarker) const
{
    if(Volume.ScreenNumber!=Screen||Host.ScreenNumber!=Screen||!(Volume.Corners==Corners)||(RequireMarker&&!Host.ActorHasTag(TEXT("DinkHardnessWorldV1"))))
    {Error=TEXT("foundation world identity/corners invalid");return false;}
    const FVector Pivot=DinkLayout::MapPixelToUnreal(Corners,300,200);
    auto At=[&](double X,double Y,double Z){return FVector3f(DinkLayout::MapPixelToUnreal(Corners,X,Y,Z)-Pivot);};
    auto Verify=[&](UStaticMeshComponent* C,const FString& MeshPath,const TArray<FIntRect>& Fill,bool Floor,FName Profile,ECollisionChannel Channel,const TCHAR* Role){
        FCollisionResponseTemplate Template;
        if(!C||!C->ComponentHasTag(Role)||!UCollisionProfile::Get()->GetProfileTemplate(Profile,Template)||Template.ObjectType!=Channel||
            C->GetCollisionProfileName()!=Profile||C->GetCollisionObjectType()!=Channel||C->GetCollisionEnabled()!=ECollisionEnabled::QueryAndPhysics||
            C->GetCollisionResponseToChannels()!=Template.ResponseToChannels||C->GetGenerateOverlapEvents()||!C->CanEverAffectNavigation())return false;
        if(MeshPath.IsEmpty())return !C->GetStaticMesh()&&(!C->GetBodyInstance()||!C->GetBodyInstance()->IsValidBodyInstance());
        if(!C->GetStaticMesh()||C->GetStaticMesh()->GetPathName()!=MeshPath||!C->GetStaticMesh()->GetBodySetup()||
            C->GetStaticMesh()->GetBodySetup()->CollisionTraceFlag!=CTF_UseComplexAsSimple||C->GetStaticMesh()->GetBodySetup()->bDoubleSidedGeometry||!C->IsRegistered()||!C->IsPhysicsStateCreated()||
            !C->GetComponentTransform().Equals(FTransform(Pivot),0)||!C->GetBodyInstance()||!C->GetBodyInstance()->IsValidBodyInstance()||C->GetBodyInstance()->bSimulatePhysics)return false;
        TArray<FString> Expected;
        if(Floor){FVector3f P[4]={At(0,0,0),At(600,0,0),At(600,400,0),At(0,400,0)};
            if(FVector3f::CrossProduct(P[1]-P[0],P[3]-P[0]).Z<0)Swap(P[1],P[3]);
            Expected.Add(Signature(P[2],P[0],P[1]));Expected.Add(Signature(P[3],P[0],P[2]));}
        for(const auto& R:Fill){std::array<DinkHardness::ShellPoint,8>P;const FVector3f B[4]={At(R.Min.X,R.Min.Y,0),At(R.Max.X,R.Min.Y,0),At(R.Max.X,R.Max.Y,0),At(R.Min.X,R.Max.Y,0)};
            for(int32 I=0;I<4;++I){P[I]={B[I].X,B[I].Y,B[I].Z};P[I+4]={B[I].X,B[I].Y,B[I].Z+HeightCm};}
            const auto Shell=DinkHardness::OpenPrismShell(P);if(!Shell)return false;
            for(const auto& T:*Shell)Expected.Add(Signature(FVector3f(T[0].X,T[0].Y,T[0].Z),FVector3f(T[1].X,T[1].Y,T[1].Z),FVector3f(T[2].X,T[2].Y,T[2].Z)));}
        TArray<FString> Actual;bool Read=false;
        FPhysicsCommand::ExecuteRead(C->GetBodyInstance()->GetPhysicsActorHandle(),[&](const FPhysicsActorHandle& Actor){
            if(!FPhysicsInterface::GetGlobalPose_AssumesLocked(Actor).Equals(C->GetComponentTransform(),1e-4))return;
            TArray<FPhysicsShapeHandle> Shapes;if(FPhysicsInterface::GetAllShapes_AssumedLocked(Actor,Shapes)!=1||FPhysicsInterface::GetShapeType(Shapes[0])!=ECollisionShapeType::Trimesh||
                !FPhysicsInterface::IsQueryShape(Shapes[0])||!FPhysicsInterface::IsSimulationShape(Shapes[0]))return;
            const auto Geometry=FPhysicsInterface::GetGeometryCollection(Shapes[0]);const auto& Mesh=Geometry.GetTriMeshGeometry();
            auto Indices=[&](const auto& Rows){for(const auto& I:Rows)Actual.Add(Signature(FVector3f(Mesh.Particles().GetX(I[0])),FVector3f(Mesh.Particles().GetX(I[1])),FVector3f(Mesh.Particles().GetX(I[2]))));};
            if(Mesh.Elements().RequiresLargeIndices())Indices(Mesh.Elements().GetLargeIndexBuffer());else Indices(Mesh.Elements().GetSmallIndexBuffer());Read=true;});
        Expected.Sort();Actual.Sort();return Read&&Actual==Expected;};
    if(!Verify(Host.CollisionSolid,SolidMesh,SolidFill,true,DinkCollision::ProfileHardSolid,DinkCollision::HardSolid,TEXT("DinkHardnessFixedFloorFillV1"))||
        !Verify(Host.CollisionLow,LowMesh,WaterFill,false,DinkCollision::ProfileHardLow,DinkCollision::HardLow,TEXT("DinkHardnessFixedWaterV1")))
    {Error=TEXT("actual cooked foundation triangles/profiles/channels/nav/overlap differ");return false;}
    Error.Reset();return true;
}
