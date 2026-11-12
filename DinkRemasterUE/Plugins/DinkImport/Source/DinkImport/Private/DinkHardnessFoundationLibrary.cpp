#include "DinkHardnessFoundationLibrary.h"
#include "DinkHardnessFoundationBuilder.h"
#include "Hardness/DinkHardnessAuthority.h"
#include "DinkImportBundle.h"
#include "Hardness/DinkHardnessFoundationSource.h"
#include "DinkArtSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "DinkCollision.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"
#include "HAL/FileManager.h"
#include "Serialization/JsonReader.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace
{
FString Result(bool OK,const FString& Error,const TCHAR* Scope,const FDinkHardnessFoundationCandidate* Candidate=nullptr)
{
    auto O=MakeShared<FJsonObject>();O->SetBoolField(TEXT("ok"),OK);O->SetStringField(TEXT("error"),Error);
    O->SetStringField(TEXT("scope"),Scope);O->SetBoolField(TEXT("saved"),false);O->SetBoolField(TEXT("world_changed"),false);
    if(Candidate){O->SetNumberField(TEXT("screen"),Candidate->Screen);
        O->SetStringField(TEXT("solid"),Candidate->FixedSolid?Candidate->FixedSolid->GetPathName():FString());
        O->SetStringField(TEXT("low"),Candidate->FixedLow?Candidate->FixedLow->GetPathName():FString());}
    FString Text;FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&Text));return Text;
}
}
FString UDinkHardnessFoundationLibrary::PrepareFoundationV1(const FString& BundleDir,int32 Screen)
{
    FDinkBundle Bundle;FString Error;
    if(BundleDir.IsEmpty() || !Bundle.Load(BundleDir,Error))return Result(false,Error,TEXT("source_prepare_unsaved"));
    FDinkHardnessFoundationCandidate Candidate;
    const bool OK=DinkGreybox::BuildRuntimeHardnessFoundationV1(Bundle,Screen,Candidate,Error);
    return Result(OK,Error,TEXT("source_prepare_unsaved_not_native_acceptance"),OK?&Candidate:nullptr);
}
FString UDinkHardnessFoundationLibrary::VerifyFoundationInstanceV1(const FString& BundleDir,AActor* Actor)
{
    auto* Host=Cast<ADinkGreyboxScreen>(Actor);FDinkBundle Bundle;FString Error;
    if(!Host || BundleDir.IsEmpty() || !Bundle.Load(BundleDir,Error))return Result(false,Error,TEXT("read_only_registered_foundation"));
    const auto* Screen=Bundle.FindScreen(Host->ScreenNumber);
    if(!Screen)return Result(false,TEXT("source screen missing"),TEXT("read_only_registered_foundation"));
    FDinkHardnessFoundationCandidate Candidate;
    Candidate.Screen=Host->ScreenNumber;
    Candidate.Pivot=DinkLayout::MapPixelToUnreal(Screen->Corners,300,200);
    Candidate.CollisionSourceHash=Screen->CollisionHash;
    Candidate.FixedSolid=Host->CollisionSolid?Host->CollisionSolid->GetStaticMesh():nullptr;
    Candidate.FixedLow=Host->CollisionLow?Host->CollisionLow->GetStaticMesh():nullptr;
    const bool OK=Host->CollisionSolid && DinkGreybox::VerifyRuntimeHardnessFoundationInstanceV1(
        Bundle,Candidate,*Host->CollisionSolid.Get(),Host->CollisionLow.Get(),Error);
    return Result(OK,Error,TEXT("read_only_registered_foundation_not_mutable_gameplay_acceptance"),&Candidate);
}

FString UDinkHardnessFoundationLibrary::StageFoundationHostV1(const FString& BundleDir,const FString& DescriptorFile,
    AActor* Actor,AActor* VolumeActor,const TArray<FString>& ArtManifestFiles)
{
    auto Fail=[](const FString& Why){return Result(false,Why,TEXT("staging_host_refused_no_marker"));};
    auto* Host=Cast<ADinkGreyboxScreen>(Actor);auto* Volume=Cast<ADinkScreenVolume>(VolumeActor);
    if(!IsInGameThread()||!Host||!Volume||Host->GetWorld()!=Volume->GetWorld()||!Host->GetWorld()||
        Host->GetWorld()->WorldType!=EWorldType::Editor||
        !Host->GetWorld()->GetPackage()->GetName().StartsWith(TEXT("/Game/Dink/RuntimeHardnessV1/Worlds/"))||
        !Host->ActorHasTag(TEXT("DinkHardnessEmptyStageV1"))||Host->ActorHasTag(TEXT("DinkHardnessWorldV1"))||
        !Host->CollisionSolid||!Host->CollisionLow||Host->CollisionSolid->GetStaticMesh()||Host->CollisionLow->GetStaticMesh())
        return Fail(TEXT("requires an explicitly empty new-stage editor host; existing/tagged worlds cannot be replaced"));
    for(TActorIterator<ADinkGreyboxScreen> It(Host->GetWorld());It;++It)
        if(*It!=Host&&It->ScreenNumber==Host->ScreenNumber)return Fail(TEXT("duplicate staging host"));
    for(TActorIterator<ADinkScreenVolume> It(Host->GetWorld());It;++It)
        if(*It!=Volume&&It->ScreenNumber==Host->ScreenNumber)return Fail(TEXT("duplicate staging volume"));
    const FString ArtDir=FPaths::ConvertRelativePathToFull(FPaths::ProjectContentDir()/TEXT("Dink/Data/Art"));
    TArray<FString> Names;IFileManager::Get().FindFiles(Names,*(ArtDir/TEXT("*.json")),true,false);Names.Sort();
    TArray<FString> Expected,Supplied;for(const FString& Name:Names)Expected.Add(ArtDir/Name);
    for(const FString& File:ArtManifestFiles){FString Full=FPaths::ConvertRelativePathToFull(File);FPaths::CollapseRelativeDirectories(Full);Supplied.Add(Full);}Supplied.Sort();Expected.Sort();
    std::vector<FString> ActualPaths,RequestedPaths;for(const auto& P:Expected)ActualPaths.push_back(P);for(const auto& P:Supplied)RequestedPaths.push_back(P);
    if(!DinkHardness::ExactAuthorityPaths(ActualPaths,RequestedPaths))return Fail(TEXT("art authority must equal ALL actual sorted Content/Dink/Data/Art/*.json paths, no omission or duplicates"));
    TMap<FString,TArray<uint8>> ArtBytes;
    for(const FString& File:Expected){FString Text;TSharedPtr<FJsonObject> O;FString Schema;
        TArray<uint8> Raw;if(!FFileHelper::LoadFileToArray(Raw,*File))return Fail(TEXT("art authority read failed"));ArtBytes.Add(File,Raw);
        if(!FFileHelper::LoadFileToString(Text,*File)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),O)||!O||
            !O->TryGetStringField(TEXT("schema"),Schema))return Fail(TEXT("invalid art authority"));
        if(Schema!=TEXT("dink-art/1"))continue;
        const TArray<TSharedPtr<FJsonValue>>* Screens=nullptr;
        if(O->HasField(TEXT("authored_collision_screens"))){if(!O->TryGetArrayField(TEXT("authored_collision_screens"),Screens))return Fail(TEXT("invalid authored list"));
            for(const auto& V:*Screens){double N;if(!V->TryGetNumber(N)||!FMath::IsFinite(N)||N!=FMath::FloorToDouble(N)||N<1||N>768)return Fail(TEXT("invalid authored screen"));
                if(int32(N)==Host->ScreenNumber)return Fail(TEXT("authored screen excluded: retain legacy authored ordering and no marker"));}}}
    if(auto* Art=Host->GetWorld()->GetSubsystem<UDinkArtSubsystem>();Art&&Art->UsesAuthoredCollision(Host->ScreenNumber))
        return Fail(TEXT("actually applied authored collision excludes staging"));
    FDinkBundle Bundle;FDinkHardnessFoundationSource Source;FString Error;
    if(!Bundle.Load(BundleDir,Error)||!FDinkHardnessFoundationSource::Load(DescriptorFile,Host->ScreenNumber,Source,Error)||
        !Source.VerifyGameplayInputs(Error))return Fail(Error);
    FDinkHardnessFoundationCandidate Candidate;Candidate.Screen=Host->ScreenNumber;
    Candidate.CollisionSourceHash=Source.CollisionSourceHash;Candidate.Pivot=DinkLayout::MapPixelToUnreal(Source.Corners,300,200);
    Candidate.FixedSolid=LoadObject<UStaticMesh>(nullptr,*Source.SolidMesh);
    Candidate.FixedLow=Source.LowMesh.IsEmpty()?nullptr:LoadObject<UStaticMesh>(nullptr,*Source.LowMesh);
    if(!DinkGreybox::VerifyRuntimeHardnessFoundationSourceV1(Bundle,Candidate,Error))return Fail(Error);
    // Only this previously empty staging host is mutated. No legacy component,
    // warp, render card or source-world package is touched. Failures clear it.
    const FTransform OldTransform=Host->GetActorTransform();
    const auto OldSolidTags=Host->CollisionSolid->ComponentTags,OldLowTags=Host->CollisionLow->ComponentTags;
    Host->SetActorTransform(FTransform(Candidate.Pivot));
    Host->CollisionSolid->SetStaticMesh(Candidate.FixedSolid);Host->CollisionLow->SetStaticMesh(Candidate.FixedLow);
    Host->CollisionSolid->ComponentTags.AddUnique(TEXT("DinkHardnessFixedFloorFillV1"));
    Host->CollisionLow->ComponentTags.AddUnique(TEXT("DinkHardnessFixedWaterV1"));
    if(!DinkGreybox::VerifyRuntimeHardnessFoundationInstanceV1(Bundle,Candidate,*Host->CollisionSolid,Host->CollisionLow.Get(),Error)||
        !Source.VerifyInstances(*Volume,*Host,Error,false)){
        Host->CollisionSolid->SetStaticMesh(nullptr);Host->CollisionLow->SetStaticMesh(nullptr);
        Host->CollisionSolid->ComponentTags=OldSolidTags;Host->CollisionLow->ComponentTags=OldLowTags;
        Host->SetActorTransform(OldTransform);return Fail(Error);}
    for(const auto& Pair:ArtBytes){TArray<uint8> Current;if(!FFileHelper::LoadFileToArray(Current,*Pair.Key)||Current!=Pair.Value){
        Host->CollisionSolid->SetStaticMesh(nullptr);Host->CollisionLow->SetStaticMesh(nullptr);
        Host->CollisionSolid->ComponentTags=OldSolidTags;Host->CollisionLow->ComponentTags=OldLowTags;
        Host->SetActorTransform(OldTransform);return Fail(TEXT("art authority changed during staging"));}}
    Host->Tags.AddUnique(TEXT("DinkHardnessWorldV1"));Host->Tags.Remove(TEXT("DinkHardnessEmptyStageV1"));
    auto O=MakeShared<FJsonObject>();O->SetBoolField(TEXT("ok"),true);O->SetBoolField(TEXT("world_changed"),true);
    O->SetBoolField(TEXT("saved"),false);O->SetStringField(TEXT("scope"),TEXT("isolated_staging_host_native_foundation_only_not_gameplay_acceptance"));
    auto Authority=MakeShared<FJsonObject>();for(const auto& Pair:ArtBytes){uint8 Hash[20];FSHA1::HashBuffer(Pair.Value.GetData(),Pair.Value.Num(),Hash);
        auto Entry=MakeShared<FJsonObject>();Entry->SetStringField(TEXT("sha1"),BytesToHex(Hash,20).ToLower());Entry->SetNumberField(TEXT("size"),Pair.Value.Num());Authority->SetObjectField(Pair.Key,Entry);}
    O->SetObjectField(TEXT("exact_art_authority"),Authority);
    FString Text;FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&Text));return Text;
}
