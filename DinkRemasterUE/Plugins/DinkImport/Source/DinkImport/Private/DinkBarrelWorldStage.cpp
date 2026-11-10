#include "DinkHardnessFoundationLibrary.h"
#include "DinkInstanceOriginsComponent.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/Level.h"
#include "Engine/LevelStreaming.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Editor.h"
#include "Editor/UnrealEdEngine.h"
#include "UnrealEdGlobals.h"
#include "GameFramework/WorldSettings.h"
#include "GameFramework/DefaultPhysicsVolume.h"
#include "Engine/LevelScriptActor.h"
#include "Engine/Brush.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Misc/SecureHash.h"
#include "Serialization/ArchiveReplaceObjectRef.h"
#include "Serialization/ObjectWriter.h"
#include "Serialization/StructuredArchive.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/SavePackage.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/SoftObjectPtr.h"
#include "UObject/LazyObjectPtr.h"
#include "UObject/UObjectHash.h"
#include "UObject/UnrealType.h"

namespace
{
constexpr const TCHAR* TargetName=TEXT("/Game/Dink/RuntimeHardnessV1/Worlds/L_Barrel031209V1");
bool Selected(int32 S){return S==31||S==209;}
FString Key(const AActor& A)
{for(FName T:A.Tags){FString V=T.ToString();if(V.StartsWith(TEXT("DinkKey=")))return V.Mid(8);}return {};}
FString Reply(bool OK,const FString& Error,const TArray<FString>& Saved,int32 Actors)
{
 auto O=MakeShared<FJsonObject>();O->SetBoolField(TEXT("ok"),OK);O->SetStringField(TEXT("error"),Error);
 O->SetStringField(TEXT("world"),TargetName);O->SetNumberField(TEXT("actor_controls"),Actors);
 O->SetStringField(TEXT("scope"),TEXT("actual_full_generated_controls_only_two_new_foundations_not_gameplay_acceptance"));
 TArray<TSharedPtr<FJsonValue>> Files;for(const auto& F:Saved)Files.Add(MakeShared<FJsonValueString>(F));O->SetArrayField(TEXT("saved_new_packages"),Files);
 FString S;FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&S));return S;
}
// Only nontransient reflected state, with scene object references canonicalized
// to source identities. Asset references remain exact asset paths. No setters.
class FStateWriter final:public FObjectWriter
{
 const TMap<const UObject*,FString>& IDs;const TSet<const UPackage*>& Forbidden;bool Target;
public:
 bool SourceReference=false;
 FStateWriter(TArray<uint8>& B,const TMap<const UObject*,FString>& I,const TSet<const UPackage*>& F,bool T)
 :FObjectWriter(B),IDs(I),Forbidden(F),Target(T){ArNoDelta=true;ArIgnoreClassRef=true;ArIgnoreArchetypeRef=true;}
 using FObjectWriter::operator<<;
 FArchive& operator<<(UObject*& O)override
 {if(Target&&O&&Forbidden.Contains(O->GetOutermost()))SourceReference=true;FString S=O?(IDs.Contains(O)?IDs[O]:O->GetPathName()):TEXT("None");FArchive& A=*this;A<<S;return A;}
 FArchive& operator<<(FObjectPtr& O)override{UObject* P=O.Get();return *this<<P;}
 FArchive& operator<<(FWeakObjectPtr& O)override{UObject* P=O.Get();return *this<<P;}
 FArchive& operator<<(FSoftObjectPath& O)override{FSoftObjectPtr P(O);return *this<<P;}
 FArchive& operator<<(FLazyObjectPtr& O)override{UObject* P=O.Get();return *this<<P;}
 FArchive& operator<<(FSoftObjectPtr& O)override
 {if(UObject* P=O.Get())return *this<<P;FString S=O.ToSoftObjectPath().ToString();for(const auto* P:Forbidden)if(S.StartsWith(P->GetName()+TEXT(".")))SourceReference|=Target;FArchive& A=*this;A<<S;return A;}
};
bool TrackedProperty(const FProperty& P,const UObject& O)
{
 return (!O.IsA<AWorldSettings>()||P.GetOwnerClass()==AWorldSettings::StaticClass())&&
  !P.HasAnyPropertyFlags(CPF_Transient|CPF_DuplicateTransient|CPF_NonPIEDuplicateTransient|CPF_SkipSerialization|CPF_Deprecated);
}
FString FirstStateDifference(UObject& Source,UObject& Target,const TMap<const UObject*,FString>& IDs,
 const TSet<const UPackage*>& Forbidden)
{
 if(Source.GetClass()!=Target.GetClass())return TEXT("class mismatch ")+Source.GetClass()->GetPathName()+TEXT(" / ")+Target.GetClass()->GetPathName();
 for(TFieldIterator<FProperty> It(Source.GetClass());It;++It)
 {
  auto* P=*It;if(!TrackedProperty(*P,Source))continue;
  TArray<uint8> A,B;FStateWriter SA(A,IDs,Forbidden,false),SB(B,IDs,Forbidden,true);
  P->SerializeItem(FStructuredArchiveFromArchive(SA).GetSlot(),P->ContainerPtrToValuePtr<void>(&Source),nullptr);
  P->SerializeItem(FStructuredArchiveFromArchive(SB).GetSlot(),P->ContainerPtrToValuePtr<void>(&Target),nullptr);
  if(A!=B||SB.SourceReference||SA.IsError()||SB.IsError())
  {
   FString X,Y;P->ExportTextItem_Direct(X,P->ContainerPtrToValuePtr<void>(&Source),nullptr,&Source,PPF_None);
   P->ExportTextItem_Direct(Y,P->ContainerPtrToValuePtr<void>(&Target),nullptr,&Target,PPF_None);
   return FString::Printf(TEXT("firstProperty=%s flags=0x%llx ownerClass=%s propertyClass=%s canonicalBytes=%d/%d targetSourceReference=%d source={%s} target={%s}"),
    *P->GetName(),static_cast<unsigned long long>(P->GetPropertyFlags()),*P->GetOwnerClass()->GetPathName(),
    *P->GetClass()->GetName(),A.Num(),B.Num(),int32(SB.SourceReference),*X.Left(384),*Y.Left(384));
  }
 }
 if(auto* A=Cast<AActor>(&Source))
 {auto* B=CastChecked<AActor>(&Target);return FString::Printf(TEXT("nonpropertyActorState sourceTRS={%s} targetTRS={%s} hidden=%d/%d collision=%d/%d"),
  *A->GetActorTransform().ToString(),*B->GetActorTransform().ToString(),int32(A->IsHidden()),int32(B->IsHidden()),int32(A->GetActorEnableCollision()),int32(B->GetActorEnableCollision()));}
 if(auto* A=Cast<UInstancedStaticMeshComponent>(&Source))
 {
  auto* B=CastChecked<UInstancedStaticMeshComponent>(&Target);
  if(A->GetInstanceCount()!=B->GetInstanceCount())return FString::Printf(TEXT("ISM count %d/%d"),A->GetInstanceCount(),B->GetInstanceCount());
  for(int32 I=0;I<A->GetInstanceCount();++I){FTransform X,Y;A->GetInstanceTransform(I,X,false);B->GetInstanceTransform(I,Y,false);
   if(!X.Equals(Y,0))return FString::Printf(TEXT("ISM firstIndex=%d source={%s} target={%s}"),I,*X.ToString(),*Y.ToString());}
 }
 if(auto* A=Cast<USceneComponent>(&Source))return TEXT("nonpropertyComponentTRS source={")+A->GetComponentTransform().ToString()+TEXT("} target={")+CastChecked<USceneComponent>(&Target)->GetComponentTransform().ToString()+TEXT("}");
 return TEXT("state serialization differs outside filtered properties; no comparison waived");
}
bool State(UObject& O,const TMap<const UObject*,FString>& IDs,const TSet<const UPackage*>& Forbidden,bool Target,TArray<uint8>& Out)
{
 FStateWriter W(Out,IDs,Forbidden,Target);FString Class=O.GetClass()->GetPathName();W<<Class;
 for(TFieldIterator<FProperty> It(O.GetClass());It;++It)
 {
  auto* P=*It;if(!TrackedProperty(*P,O))continue;
  FString Name=P->GetName();W<<Name;P->SerializeItem(FStructuredArchiveFromArchive(W).GetSlot(),P->ContainerPtrToValuePtr<void>(&O),nullptr);
 }
 if(auto* A=Cast<AActor>(&O)){FTransform T=A->GetActorTransform();W<<T;bool H=A->IsHidden(),C=A->GetActorEnableCollision();W<<H<<C;}
 if(auto* C=Cast<USceneComponent>(&O)){FTransform T=C->GetComponentTransform();W<<T;}
 if(auto* C=Cast<UInstancedStaticMeshComponent>(&O))
 {int32 N=C->GetInstanceCount();W<<N;for(int32 I=0;I<N;++I){FTransform T;if(!C->GetInstanceTransform(I,T,false))return false;W<<T;}}
 return !W.SourceReference&&!W.IsError();
}
void AddObjects(AActor& A,const FString& K,TMap<const UObject*,FString>& IDs,TMap<FString,UObject*>& ByRelative)
{
 IDs.Add(&A,K);ByRelative.Add(TEXT(""),&A);
 ForEachObjectWithOuter(&A,[&](UObject* O){const FString R=O->GetPathName(&A);IDs.Add(O,K+TEXT("/")+R);ByRelative.Add(R,O);},EGetObjectsFlags::IncludeNestedObjects);
}
bool Fresh(const FString& P){return !FindPackage(nullptr,*P)&&!FPackageName::DoesPackageExist(P);}
}

FString UDinkHardnessFoundationLibrary::StageTwoBarrelWorldV1(UWorld* SourceWorld,const FString& BundleDir,
 const FString& DescriptorDir,const FString& TargetWorldPackage,const TArray<FString>& ArtManifestFiles)
{
 TArray<FString> Saved;int32 Count=0;auto Fail=[&](const FString& E){return Reply(false,E,Saved,Count);};
 if(!IsInGameThread()||!GEditor||!GUnrealEd||GEditor->PlayWorld||!SourceWorld||SourceWorld->WorldType!=EWorldType::Editor||
    SourceWorld->GetPackage()->GetName()!=TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World")||TargetWorldPackage!=TargetName||!Fresh(TargetWorldPackage))
  return Fail(TEXT("requires actual loaded canonical generated editor world, no PIE, and absent exact candidate target"));
 for(const auto* S:SourceWorld->GetStreamingLevels())if(!S||!S->GetLoadedLevel())return Fail(TEXT("all actual source streaming levels must be loaded before staging"));
 TSet<const UPackage*> SourcePackages;for(const auto* L:SourceWorld->GetLevels())SourcePackages.Add(L->GetOutermost());
 SourcePackages.Add(SourceWorld->GetOutermost());
 TMap<const UPackage*,bool> Dirty;for(const auto* P:SourcePackages)Dirty.Add(P,P->IsDirty());
 TArray<AActor*> Controls;TMap<int32,ADinkGreyboxScreen*> OldHosts;TMap<int32,ADinkScreenVolume*> OldVolumes;
 TMap<FString,AActor*> Sources;TMap<const UObject*,FString> IDs;TMap<AActor*,TMap<FString,UObject*>> SourceObjects;
 for(TActorIterator<AActor> It(SourceWorld);It;++It)
 {
  AActor* A=*It;if(A->IsA<AWorldSettings>()||A==A->GetLevel()->GetDefaultBrush()||A->IsA<ADefaultPhysicsVolume>())continue;
  if(A->IsA<ALevelScriptActor>()){if(A->GetClass()!=ALevelScriptActor::StaticClass())return Fail(TEXT("custom level script requires explicit preservation"));continue;}
  if(A->HasAnyFlags(RF_Transient))continue;
  const FString K=Key(*A);if(K.IsEmpty()||Sources.Contains(K)||!A->GetClass()->HasAnyClassFlags(CLASS_Native))return Fail(TEXT("unidentified/duplicate/non-native source control actor"));
  Sources.Add(K,A);AddObjects(*A,K,IDs,SourceObjects.FindOrAdd(A));
  if(auto* H=Cast<ADinkGreyboxScreen>(A);H&&Selected(H->ScreenNumber))
  {if(OldHosts.Contains(H->ScreenNumber)||H->ActorHasTag(TEXT("DinkHardnessWorldV1")))return Fail(TEXT("duplicate/already migrated selected source host"));OldHosts.Add(H->ScreenNumber,H);continue;}
  if(auto* V=Cast<ADinkScreenVolume>(A);V&&Selected(V->ScreenNumber))
  {if(OldVolumes.Contains(V->ScreenNumber))return Fail(TEXT("duplicate selected volume"));OldVolumes.Add(V->ScreenNumber,V);}
  Controls.Add(A);
 }
 if(OldHosts.Num()!=2||OldVolumes.Num()!=2)return Fail(TEXT("actual031/209 hosts and volumes required"));
 const auto* Settings=SourceWorld->GetWorldSettings();
 IDs.Add(SourceWorld,TEXT("@World"));IDs.Add(Settings,TEXT("@WorldSettings"));
 for(const auto* L:SourceWorld->GetLevels())IDs.Add(L,TEXT("@Level"));
 TMap<UObject*,TArray<uint8>> Before;
 {TArray<uint8> B;if(!State(*const_cast<AWorldSettings*>(Settings),IDs,SourcePackages,false,B))return Fail(TEXT("source settings fingerprint failed"));Before.Add(const_cast<AWorldSettings*>(Settings),MoveTemp(B));}
 for(const auto& P:SourceObjects)for(const auto& O:P.Value)
 {TArray<uint8> B;if(!State(*O.Value,IDs,SourcePackages,false,B))return Fail(TEXT("source fingerprint failed"));Before.Add(O.Value,MoveTemp(B));}
 TArray<UStaticMesh*> Foundations;
 for(int32 S:{31,209})for(const TCHAR* Role:{TEXT("FixedSolidV1"),TEXT("FixedLowV1")})
  if(!Fresh(FString::Printf(TEXT("/Game/Dink/RuntimeHardnessV1/SCR_%03d/SM_SCR_%03d_%s"),S,S,Role)))return Fail(TEXT("foundation target already exists; no overwrite"));
 for(int32 S:{31,209})
 {
  const FString Result=PrepareFoundationV1(BundleDir,S);TSharedPtr<FJsonObject> O;
  if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Result),O)||!O||!O->GetBoolField(TEXT("ok")))return Fail(Result);
  for(const TCHAR* K:{TEXT("solid"),TEXT("low")}){const FString P=O->GetStringField(K);if(!P.IsEmpty()){auto* M=LoadObject<UStaticMesh>(nullptr,*P);if(!M)return Fail(TEXT("prepared foundation missing"));Foundations.Add(M);}}
 }
 UPackage* Package=CreatePackage(*TargetWorldPackage);Package->SetPackageFlags(PKG_ContainsMap);
 TStrongObjectPtr<UWorld> World(UWorld::CreateWorld(EWorldType::Editor,false,FName(*FPackageName::GetShortName(TargetWorldPackage)),Package,false));
 if(!World.IsValid())return Fail(TEXT("candidate world creation failed"));
 ON_SCOPE_EXIT{World->DestroyWorld(false);World->MarkObjectsPendingKill();};
 World->SetFlags(RF_Public|RF_Standalone);
 auto* NewSettings=World->GetWorldSettings();
 for(TFieldIterator<FProperty> It(Settings->GetClass());It;++It)
  if(It->GetOwnerClass()==AWorldSettings::StaticClass()&&!It->HasAnyPropertyFlags(CPF_Transient|CPF_DuplicateTransient|CPF_NonPIEDuplicateTransient|CPF_SkipSerialization))
   It->CopyCompleteValue(It->ContainerPtrToValuePtr<void>(NewSettings),It->ContainerPtrToValuePtr<void>(Settings));
 TArray<AActor*> Copies;GUnrealEd->DuplicateActors(Controls,Copies,World->PersistentLevel,FVector::ZeroVector);
 if(Copies.Num()!=Controls.Num())return Fail(TEXT("actual control duplication incomplete"));
 TMap<FString,AActor*> Targets;for(AActor* A:Copies){const FString K=Key(*A);if(!Sources.Contains(K)||Targets.Contains(K))return Fail(TEXT("copied control identity missing/duplicate"));if(A->GetWorld()!=World.Get()||SourcePackages.Contains(A->GetArchetype()->GetOutermost()))return Fail(TEXT("copied actor retained source world/archetype"));Targets.Add(K,A);A->SetActorLabel(Sources[K]->GetActorLabel(),false);}
 TMap<UObject*,UObject*> Remap;Remap.Add(SourceWorld,World.Get());Remap.Add(const_cast<AWorldSettings*>(Settings),NewSettings);
 for(const auto* L:SourceWorld->GetLevels())Remap.Add(const_cast<ULevel*>(L),World->PersistentLevel);
 TMap<int32,ADinkGreyboxScreen*> NewHosts;
 for(int32 S:{31,209})
 {
  auto* Old=OldHosts[S];auto* H=World->SpawnActor<ADinkGreyboxScreen>();if(!H)return Fail(TEXT("new empty host spawn failed"));
  H->ScreenNumber=S;H->SetActorTransform(Old->GetActorTransform());H->Tags=Old->Tags;H->Tags.AddUnique(TEXT("DinkHardnessEmptyStageV1"));H->SetActorLabel(Old->GetActorLabel(),false);
  if(H->CollisionSolid->GetStaticMesh()||H->CollisionLow->GetStaticMesh())return Fail(TEXT("fresh host was not empty"));
  H->Visual->UnregisterComponent();UEngine::CopyPropertiesForUnrelatedObjects(Old->Visual,H->Visual);
  H->InstanceOrigins->Origins=Old->InstanceOrigins->Origins;
  Remap.Add(Old,H);Remap.Add(Old->GetRootComponent(),H->GetRootComponent());Remap.Add(Old->Visual,H->Visual);Remap.Add(Old->InstanceOrigins,H->InstanceOrigins);
  TInlineComponentArray<UInstancedStaticMeshComponent*> Decor(Old);
  for(auto* D:Decor)
  {
   if(!D->GetName().StartsWith(TEXT("Decor_"))||D->GetCollisionEnabled()!=ECollisionEnabled::NoCollision)return Fail(TEXT("unexpected selected-host instanced component"));
   auto* C=NewObject<UInstancedStaticMeshComponent>(H,D->GetFName(),RF_Transactional);
   UEngine::CopyPropertiesForUnrelatedObjects(D,C);H->AddInstanceComponent(C);Remap.Add(D,C);
  }
  Targets.Add(Key(*Old),H);NewHosts.Add(S,H);
 }
 for(const auto& P:Targets)
 {
  AActor* Src=Sources[P.Key];AActor* Dst=P.Value;
  TMap<FString,UObject*> Objects;AddObjects(*Dst,P.Key,IDs,Objects);
  for(const auto& O:SourceObjects[Src])
  {
   if(auto* H=Cast<ADinkGreyboxScreen>(Src);H&&Selected(H->ScreenNumber))continue;
   UObject** New=Objects.Find(O.Key);if(!New||(*New)->GetClass()!=O.Value->GetClass())return Fail(TEXT("source descendant missing from candidate"));Remap.Add(O.Value,*New);
  }
 }
 for(const auto& P:Remap)if(const FString* Identity=IDs.Find(P.Key))IDs.Add(P.Value,*Identity);
 for(const auto& P:Targets)
 {
  FArchiveReplaceObjectRef<UObject> Fix(P.Value,Remap,EArchiveReplaceObjectFlags::IgnoreOuterRef|EArchiveReplaceObjectFlags::IgnoreArchetypeRef);
  TInlineComponentArray<USceneComponent*> Components(P.Value);
  for(auto* C:Components)if(!C->IsRegistered()){if(C!=P.Value->GetRootComponent()&&!C->GetAttachParent())C->SetupAttachment(P.Value->GetRootComponent());C->RegisterComponent();}
 }
 FArchiveReplaceObjectRef<UObject> FixSettings(NewSettings,Remap,EArchiveReplaceObjectFlags::IgnoreOuterRef|EArchiveReplaceObjectFlags::IgnoreArchetypeRef);
 for(const auto& P:Targets)
 {
  AActor* Src=Sources[P.Key];AActor* Dst=P.Value;const bool Host=Cast<ADinkGreyboxScreen>(Src)&&Selected(CastChecked<ADinkGreyboxScreen>(Src)->ScreenNumber);
  TMap<FString,UObject*> Objects;AddObjects(*Dst,P.Key,IDs,Objects);
  for(const auto& O:SourceObjects[Src])
  {
   UObject* New=Remap.FindRef(O.Value);if(!New){if(Host)continue;return Fail(TEXT("candidate reference map incomplete"));}
   if(Host&&O.Value!=OldHosts[CastChecked<ADinkGreyboxScreen>(Src)->ScreenNumber]->Visual&&
      !Cast<UInstancedStaticMeshComponent>(O.Value)&&O.Value!=CastChecked<ADinkGreyboxScreen>(Src)->InstanceOrigins)continue;
   TArray<uint8> A,B;if(!State(*O.Value,IDs,SourcePackages,false,A)||!State(*New,IDs,SourcePackages,true,B)||A!=B)return Fail(TEXT("copied control/component properties or scene reference mismatch: ")+P.Key+TEXT("/")+O.Key+TEXT(" ")+FirstStateDifference(*O.Value,*New,IDs,SourcePackages));
   if(auto* C=Cast<UActorComponent>(New);C&&(!C->IsIn(Dst)||C->GetOwner()!=Dst))return Fail(TEXT("component ownership escaped candidate"));
  }
 }
 for(int32 S:{31,209})
 {
  auto* Volume=Cast<ADinkScreenVolume>(Remap.FindRef(OldVolumes[S]));
  const FString R=StageFoundationHostV1(BundleDir,DescriptorDir/FString::Printf(TEXT("SCR_%03d.json"),S),NewHosts[S],Volume,ArtManifestFiles);
  TSharedPtr<FJsonObject> O;if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(R),O)||!O||!O->GetBoolField(TEXT("ok")))return Fail(R);
  const FString V=VerifyFoundationInstanceV1(BundleDir,NewHosts[S]);if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(V),O)||!O||!O->GetBoolField(TEXT("ok")))return Fail(V);
 }
 for(const auto& P:Before){TArray<uint8> B;if(!State(*P.Key,IDs,SourcePackages,false,B)||B!=P.Value)return Fail(TEXT("source actor/component changed during staging"));}
 for(const auto& P:Dirty)if(P.Key->IsDirty()!=P.Value)return Fail(TEXT("source package dirty state changed"));
 TArray<uint8> SA,SB;if(!State(*const_cast<AWorldSettings*>(Settings),IDs,SourcePackages,false,SA)||!State(*NewSettings,IDs,SourcePackages,true,SB)||SA!=SB)return Fail(TEXT("world settings or source-world references changed"));
 // All source/control/native proofs precede any save. Only newly owned paths.
 for(UStaticMesh* M:Foundations)
 {
  const FString File=FPackageName::LongPackageNameToFilename(M->GetOutermost()->GetName(),FPackageName::GetAssetPackageExtension());
  if(IFileManager::Get().FileExists(*File))return Fail(TEXT("new foundation save target appeared"));
  IFileManager::Get().MakeDirectory(*FPaths::GetPath(File),true);
 FSavePackageArgs A;A.TopLevelFlags=RF_Public|RF_Standalone;A.SaveFlags=SAVE_NoError;
  if(!UPackage::SavePackage(M->GetOutermost(),M,*File,A))return Fail(TEXT("new foundation save failed; retain listed partial candidate only"));
  Saved.Add(File);
 }
 const FString File=FPackageName::LongPackageNameToFilename(TargetWorldPackage,FPackageName::GetMapPackageExtension());
 if(IFileManager::Get().FileExists(*File))return Fail(TEXT("new world save target appeared"));
 IFileManager::Get().MakeDirectory(*FPaths::GetPath(File),true);
 FSavePackageArgs A;A.TopLevelFlags=RF_Public|RF_Standalone;A.SaveFlags=SAVE_NoError;
 if(!UPackage::SavePackage(Package,World.Get(),*File,A))return Fail(TEXT("new world save failed; preserve listed candidate packages"));
  Saved.Add(File);
 Count=Targets.Num();return Reply(true,TEXT(""),Saved,Count);
}
