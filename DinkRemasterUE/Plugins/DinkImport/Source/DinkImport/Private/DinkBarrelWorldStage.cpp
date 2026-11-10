#include "DinkHardnessFoundationLibrary.h"
#include "DinkInstanceOriginsComponent.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/BoxComponent.h"
#include "PhysicsEngine/BodySetup.h"
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
#include "Hash/CityHash.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Misc/OutputDeviceNull.h"
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
#include "UObject/NoExportTypes.h"
#include <limits>
#include <cmath>

namespace
{
constexpr const TCHAR* TargetName=TEXT("/Game/Dink/RuntimeHardnessV1/Worlds/L_Barrel031209V1");
bool Selected(int32 S){return S==31||S==209;}
FString Key(const AActor& A)
{for(FName T:A.Tags){FString V=T.ToString();if(V.StartsWith(TEXT("DinkKey=")))return V.Mid(8);}return {};}
FString Reply(bool OK,const FString& Error,const TArray<FString>& Saved,int32 Actors,const TArray<FString>& Equivalences)
{
 auto O=MakeShared<FJsonObject>();O->SetBoolField(TEXT("ok"),OK);O->SetStringField(TEXT("error"),Error);
 TArray<TSharedPtr<FJsonValue>> E;for(const auto& V:Equivalences)E.Add(MakeShared<FJsonValueString>(V));O->SetArrayField(TEXT("measured_representation_equivalences"),E);
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
bool RotationProperty(const FProperty& P,const UObject& O)
{
 const auto* Struct=CastField<FStructProperty>(&P);
 return O.IsA<USceneComponent>()&&P.GetFName()==TEXT("RelativeRotation")&&
  P.GetOwnerClass()==USceneComponent::StaticClass()&&Struct&&Struct->Struct==TBaseStructure<FRotator>::Get();
}
bool MeasuredNearZeroRotation(UObject& A,UObject& B,FRotator& Canonical,FString& Evidence)
{
 if(!A.IsA<USceneComponent>()||A.GetClass()!=B.GetClass())return false;
 auto* P=FindFProperty<FStructProperty>(A.GetClass(),TEXT("RelativeRotation"));
 if(!P||!RotationProperty(*P,A))return false;
 const auto& X=*P->ContainerPtrToValuePtr<FRotator>(&A);const auto& Y=*P->ContainerPtrToValuePtr<FRotator>(&B);
 const double XS[]={X.Pitch,X.Yaw,X.Roll},YS[]={Y.Pitch,Y.Yaw,Y.Roll};double Scale=1;
 for(int I=0;I<3;++I){if(!FMath::IsFinite(XS[I])||!FMath::IsFinite(YS[I]))return false;Scale=FMath::Max(Scale,FMath::Max(FMath::Abs(XS[I]),FMath::Abs(YS[I])));}
 const double Budget=16*std::numeric_limits<double>::epsilon()*Scale;
 Canonical=X;double* C[]={&Canonical.Pitch,&Canonical.Yaw,&Canonical.Roll};bool Difference=false;
 for(int I=0;I<3;++I)
 {
  if(FMemory::Memcmp(&XS[I],&YS[I],sizeof(double))==0)continue;
  if(FMath::Abs(XS[I])>Budget||FMath::Abs(YS[I])>Budget)return false;
  *C[I]=0;Difference=true;
 }
 if(!Difference)return false;
 Evidence=FString::Printf(TEXT("RelativeRotation machine-zero ONLY source=(%.17g,%.17g,%.17g) target=(%.17g,%.17g,%.17g) budgetDeg=%.17g; nonzeroangles/nonspatialbytes unchanged"),XS[0],XS[1],XS[2],YS[0],YS[1],YS[2],Budget);
 return true;
}
bool ExactQuaternion(const FQuat& A,const FQuat& B)
{
 const double X[]={A.X,A.Y,A.Z,A.W},Y[]={B.X,B.Y,B.Z,B.W};
 for(int I=0;I<4;++I)if(!FMath::IsFinite(X[I])||!FMath::IsFinite(Y[I]))return false;
 return FMemory::Memcmp(X,Y,sizeof(X))==0;
}
bool MeasuredAdjacentRotation(UObject& Source,UObject& Target,FRotator& Canonical,FString& Evidence)
{
 auto* A=Cast<USceneComponent>(&Source);auto* B=Cast<USceneComponent>(&Target);
 if(!A||!B||A->GetClass()!=B->GetClass())return false;
 const FRotator S=A->GetRelativeRotation(),T=B->GetRelativeRotation();
 const double X[]={S.Pitch,S.Yaw,S.Roll},Y[]={T.Pitch,T.Yaw,T.Roll};int Changed=0;
 for(int I=0;I<3;++I){if(!FMath::IsFinite(X[I])||!FMath::IsFinite(Y[I]))return false;
  if(FMemory::Memcmp(&X[I],&Y[I],sizeof(double))==0)continue;
  if(X[I]==0||Y[I]==0||std::nextafter(X[I],Y[I])!=Y[I])return false;
  ++Changed;
 }
 if(Changed!=1||!ExactQuaternion(S.Quaternion(),T.Quaternion())||
    !ExactQuaternion(A->GetRelativeRotationCache().RotatorToQuat_ReadOnly(S),B->GetRelativeRotationCache().RotatorToQuat_ReadOnly(T))||
    !ExactQuaternion(A->GetComponentQuat(),B->GetComponentQuat()))return false;
 Canonical=S;
 Evidence=FString::Printf(TEXT("RelativeRotation ONLY ONE adjacent nonzero scalar source=(%.17g,%.17g,%.17g) target=(%.17g,%.17g,%.17g); directEuler/cache/world quaternions BITEXACT; sourcebytes unchanged"),X[0],X[1],X[2],Y[0],Y[1],Y[2]);
 return true;
}
bool MeasuredRotation(UObject& A,UObject& B,FRotator& Canonical,FString& Evidence)
{
 return MeasuredNearZeroRotation(A,B,Canonical,Evidence)||MeasuredAdjacentRotation(A,B,Canonical,Evidence);
}
bool AdjacentTranslationValues(const double (&A)[3],const double (&B)[3])
{
 bool Difference=false;
 for(int I=0;I<3;++I)
 {
  if(!FMath::IsFinite(A[I])||!FMath::IsFinite(B[I]))return false;
  if(FMemory::Memcmp(&A[I],&B[I],sizeof(double))==0)continue;
  if(std::nextafter(A[I],B[I])!=B[I])return false;
  Difference=true;
 }
 return Difference;
}
bool MeasuredWorldTranslation(const FTransform& S,const FTransform& T,FTransform& Canonical,FString& Evidence)
{
 if(S.ContainsNaN()||T.ContainsNaN())return false;
 const FQuat SQ=S.GetRotation(),TQ=T.GetRotation();const FVector SS=S.GetScale3D(),TS=T.GetScale3D();
 const double Q1[]={SQ.X,SQ.Y,SQ.Z,SQ.W},Q2[]={TQ.X,TQ.Y,TQ.Z,TQ.W};
 const double K1[]={SS.X,SS.Y,SS.Z},K2[]={TS.X,TS.Y,TS.Z};
 if(FMemory::Memcmp(Q1,Q2,sizeof(Q1))||FMemory::Memcmp(K1,K2,sizeof(K1)))return false;
 const FVector X=S.GetTranslation(),Y=T.GetTranslation();const double V1[]={X.X,X.Y,X.Z},V2[]={Y.X,Y.Y,Y.Z};
 if(!AdjacentTranslationValues(V1,V2))return false;
 Canonical=S;
 Evidence=FString::Printf(TEXT("ACTOR-world translation ONLY maxONE adjacent-double peraxis source=(%.17g,%.17g,%.17g) target=(%.17g,%.17g,%.17g) deltaCm=(%.17g,%.17g,%.17g); Q/scale/nonspatial/sourcebytes strict"),V1[0],V1[1],V1[2],V2[0],V2[1],V2[2],V2[0]-V1[0],V2[1]-V1[1],V2[2]-V1[2]);
 return true;
}
bool MeasuredActorTranslation(UObject& Source,UObject& Target,FTransform& Canonical,FString& Evidence)
{
 auto* A=Cast<AActor>(&Source);auto* B=Cast<AActor>(&Target);
 return A&&B&&A->GetClass()==B->GetClass()&&MeasuredWorldTranslation(A->GetActorTransform(),B->GetActorTransform(),Canonical,Evidence);
}
bool RootLocationProperty(const FProperty& P,const UObject& O)
{
 const auto* S=CastField<FStructProperty>(&P);
 return O.IsA<USceneComponent>()&&P.GetOwnerClass()==USceneComponent::StaticClass()&&P.GetFName()==TEXT("RelativeLocation")&&S&&S->Struct==TBaseStructure<FVector>::Get();
}
bool MeasuredRootTranslation(UObject& Source,UObject& Target,AActor* ExpectedSource,AActor* ExpectedTarget,FTransform& Canonical,FString& Evidence)
{
 auto* A=Cast<USceneComponent>(&Source);auto* B=Cast<USceneComponent>(&Target);
 if(!A||!B||!ExpectedSource||!ExpectedTarget||A->GetClass()!=B->GetClass()||
    A->GetOwner()!=ExpectedSource||B->GetOwner()!=ExpectedTarget||
    ExpectedSource->GetRootComponent()!=A||ExpectedTarget->GetRootComponent()!=B||
    A->GetAttachParent()||B->GetAttachParent())return false;
 FTransform OwnerCanonical;FString OwnerEvidence;
 if(!MeasuredActorTranslation(*ExpectedSource,*ExpectedTarget,OwnerCanonical,OwnerEvidence)||
    !MeasuredWorldTranslation(A->GetComponentTransform(),B->GetComponentTransform(),Canonical,Evidence))return false;
 // Both local values must be the EXACT corresponding actor-world translation:
 // this admits only the already measured root manifestation of the same delta.
 const FVector X=A->GetRelativeLocation(),Y=B->GetRelativeLocation();
 const FVector AX=ExpectedSource->GetActorLocation(),BY=ExpectedTarget->GetActorLocation();
 const double V[]={X.X,X.Y,X.Z,Y.X,Y.Y,Y.Z},W[]={AX.X,AX.Y,AX.Z,BY.X,BY.Y,BY.Z};
 if(FMemory::Memcmp(V,W,sizeof(V))||!Canonical.Equals(OwnerCanonical,0))return false;
 Evidence=TEXT("ROOT/noattach RelativeLocation+world ONLY correspondingowner ")+OwnerEvidence;
 return true;
}
bool DerivedWorldDelta(const FTransform& S,const FTransform& T,const FTransform& OwnerS,const FTransform& OwnerT)
{
 if(S.ContainsNaN()||T.ContainsNaN())return false;
 const FQuat Q=S.GetRotation(),R=T.GetRotation();const FVector K=S.GetScale3D(),L=T.GetScale3D();
 const double QR[]={Q.X,Q.Y,Q.Z,Q.W,K.X,K.Y,K.Z},RR[]={R.X,R.Y,R.Z,R.W,L.X,L.Y,L.Z};
 if(FMemory::Memcmp(QR,RR,sizeof(QR)))return false;
 const FVector A=S.GetTranslation(),B=T.GetTranslation(),X=OwnerS.GetTranslation(),Y=OwnerT.GetTranslation();
 const double V[]={A.X,A.Y,A.Z},W[]={B.X,B.Y,B.Z},OS[]={X.X,X.Y,X.Z},OT[]={Y.X,Y.Y,Y.Z};
 bool Difference=false;
 for(int I=0;I<3;++I){if(!FMath::IsFinite(V[I])||!FMath::IsFinite(W[I]))return false;
  const double D=OT[I]-OS[I];
  if(D==0){if(FMemory::Memcmp(&V[I],&W[I],sizeof(double)))return false;}
  else if(W[I]-V[I]!=D)return false;
  Difference|=FMemory::Memcmp(&V[I],&W[I],sizeof(double))!=0;
 }
 return Difference;
}
bool MeasuredChildTranslation(UObject& Source,UObject& Target,AActor* ExpectedSource,AActor* ExpectedTarget,
 const TMap<UObject*,UObject*>& Remap,FTransform& Canonical,FString& Evidence)
{
 auto* A=Cast<USceneComponent>(&Source);auto* B=Cast<USceneComponent>(&Target);
 if(!A||!B||
    !ExpectedSource||!ExpectedTarget||A->GetClass()!=B->GetClass()||A->GetOwner()!=ExpectedSource||B->GetOwner()!=ExpectedTarget||
    A==ExpectedSource->GetRootComponent()||B==ExpectedTarget->GetRootComponent())return false;
 FTransform RootCanonical;FString RootEvidence;
 if(!ExpectedSource->GetRootComponent()||!ExpectedTarget->GetRootComponent()||
    !MeasuredRootTranslation(*ExpectedSource->GetRootComponent(),*ExpectedTarget->GetRootComponent(),ExpectedSource,ExpectedTarget,RootCanonical,RootEvidence))return false;
 TSet<const USceneComponent*> Seen;
 for(auto* P=A,*Q=B;P!=ExpectedSource->GetRootComponent();)
 {
  if(!P||!Q||Seen.Contains(P)||P->GetOwner()!=ExpectedSource||Q->GetOwner()!=ExpectedTarget||P->GetClass()!=Q->GetClass())return false;
  Seen.Add(P);
  // Exact local reflected TRS plus socket; every other reflected field remains
  // checked by State. Never normalize local transforms or instance transforms.
  FVector PL=P->GetRelativeLocation(),QL=Q->GetRelativeLocation(),PS=P->GetRelativeScale3D(),QS=Q->GetRelativeScale3D();
  FRotator PR=P->GetRelativeRotation(),QR=Q->GetRelativeRotation(),QualifiedRotation;FString RotationEvidence;
  if(MeasuredRotation(*P,*Q,QualifiedRotation,RotationEvidence))PR=QR=QualifiedRotation;
  TArray<uint8> Left,Right;FObjectWriter LW(Left),RW(Right);LW<<PL<<PR<<PS;RW<<QL<<QR<<QS;
  if(Left!=Right||P->GetAttachSocketName()!=Q->GetAttachSocketName()||!P->GetAttachParent()||
     Remap.FindRef(P->GetAttachParent())!=Q->GetAttachParent())return false;
  P=P->GetAttachParent();Q=Q->GetAttachParent();
  if(P==ExpectedSource->GetRootComponent()&&Q!=ExpectedTarget->GetRootComponent())return false;
 }
 if(!DerivedWorldDelta(A->GetComponentTransform(),B->GetComponentTransform(),ExpectedSource->GetActorTransform(),ExpectedTarget->GetActorTransform()))return false;
 Canonical=A->GetComponentTransform();const FVector From=Canonical.GetTranslation(),To=B->GetComponentLocation();
 Evidence=FString::Printf(TEXT("DERIVED CHILD world ONLY source=(%.17g,%.17g,%.17g) target=(%.17g,%.17g,%.17g) delta=(%.17g,%.17g,%.17g); exact owner delta; mapped attachment chain/local TRS/Q/scale strict; "),From.X,From.Y,From.Z,To.X,To.Y,To.Z,To.X-From.X,To.Y-From.Y,To.Z-From.Z)+RootEvidence;
 return true;
}
bool AggregateProperty(const FProperty& P,const UObject& O)
{
 const auto* S=CastField<FStructProperty>(&P);
 return O.IsA<UBodySetup>()&&P.GetOwnerClass()==UBodySetup::StaticClass()&&P.GetFName()==TEXT("AggGeom")&&S&&S->Struct==FKAggregateGeom::StaticStruct();
}
bool MeasuredBoxRotationZero(UObject& Source,UObject& Target,AActor* ExpectedSource,AActor* ExpectedTarget,
 const TMap<UObject*,UObject*>& Remap,const TMap<const UObject*,FString>& IDs,const TSet<const UPackage*>& Forbidden,
 FKAggregateGeom& Canonical,FString& Evidence)
{
 auto* A=Cast<UBodySetup>(&Source);auto* B=Cast<UBodySetup>(&Target);
 auto* BoxA=A?Cast<UBoxComponent>(A->GetOuter()):nullptr;auto* BoxB=B?Cast<UBoxComponent>(B->GetOuter()):nullptr;
 if(!A||!B||A->GetClass()!=B->GetClass()||!BoxA||!BoxB||BoxA->GetClass()!=BoxB->GetClass()||
    BoxA->GetOwner()!=ExpectedSource||BoxB->GetOwner()!=ExpectedTarget||!ExpectedSource||!ExpectedTarget||
    Remap.FindRef(BoxA)!=BoxB||Remap.FindRef(A)!=B||A->AggGeom.BoxElems.Num()!=B->AggGeom.BoxElems.Num())return false;
 FKAggregateGeom Left=A->AggGeom,Right=B->AggGeom;bool Changed=false;Evidence.Reset();
 for(int I=0;I<Left.BoxElems.Num();++I)
 {
  FRotator& L=Left.BoxElems[I].Rotation;FRotator& R=Right.BoxElems[I].Rotation;
  double* X[]={&L.Pitch,&L.Yaw,&L.Roll};double* Y[]={&R.Pitch,&R.Yaw,&R.Roll};
  for(int Axis=0;Axis<3;++Axis)if(*X[Axis]==0&&*Y[Axis]==0&&FMemory::Memcmp(X[Axis],Y[Axis],sizeof(double)))
  {Evidence+=FString::Printf(TEXT(" box[%d].Rotation axis%d source=%.17g target=%.17g SIGNEDZERO ONLY;"),I,Axis,*X[Axis],*Y[Axis]);*X[Axis]=*Y[Axis]=0;Changed=true;}
 }
 if(!Changed)return false;
 auto* P=FindFProperty<FStructProperty>(UBodySetup::StaticClass(),TEXT("AggGeom"));if(!P||!AggregateProperty(*P,Source))return false;
 TArray<uint8> L,R;FStateWriter LW(L,IDs,Forbidden,false),RW(R,IDs,Forbidden,true);
 P->SerializeItem(FStructuredArchiveFromArchive(LW).GetSlot(),&Left,nullptr);P->SerializeItem(FStructuredArchiveFromArchive(RW).GetSlot(),&Right,nullptr);
 if(L!=R||LW.IsError()||RW.IsError()||RW.SourceReference)return false;
 Canonical=Left;Evidence+=TEXT(" entire canonical aggregate exact; mapped UBoxComponent-owned body; original source bytes unchanged");return true;
}
bool RestoreNewTargetRootTranslation(AActor& Source,AActor& Target,UWorld* NewWorld,
 const TMap<UObject*,UObject*>& Remap,bool& Restored,FString& Evidence)
{
 Restored=false;Evidence.Reset();
 if(&Source==&Target||!NewWorld||Target.GetWorld()!=NewWorld||Source.GetWorld()==NewWorld||
    Source.GetClass()!=Target.GetClass()||Remap.FindRef(&Source)!=&Target)
 {Evidence=TEXT("root restoration requires exact mapped actor in distinct NEW world");return false;}
 auto* A=Source.GetRootComponent();auto* B=Target.GetRootComponent();
 if(!A||!B)return true;
 FTransform Canonical;FString Proof;
 // Ineligible changes remain untouched and fail the later strict comparison.
 if(!MeasuredRootTranslation(*A,*B,&Source,&Target,Canonical,Proof))return true;
 if(Remap.FindRef(A)!=B){Evidence=TEXT("root restoration requires exact root mapping");return false;}
 B->SetRelativeLocation_Direct(A->GetRelativeLocation());
 B->UpdateComponentToWorld(EUpdateTransformFlags::None,ETeleportType::TeleportPhysics);
 auto ExactTransform=[](FTransform L,FTransform R){TArray<uint8> X,Y;FObjectWriter LX(X),RY(Y);LX<<L;RY<<R;return X==Y;};
 const FVector L=A->GetRelativeLocation(),R=B->GetRelativeLocation();const double X[]={L.X,L.Y,L.Z},Y[]={R.X,R.Y,R.Z};
 if(FMemory::Memcmp(X,Y,sizeof(X))||!ExactTransform(Source.GetActorTransform(),Target.GetActorTransform())||
    !ExactTransform(A->GetComponentTransform(),B->GetComponentTransform()))
 {Evidence=TEXT("target root exact source-local/world postcondition failed");return false;}
 Restored=true;Evidence=TEXT("RESTORED NEW TARGET root exact source position via Direct+TeleportPhysics; ")+Proof;return true;
}
bool ExactTransformBytes(FTransform A,FTransform B)
{
 TArray<uint8> L,R;FObjectWriter LW(L),RW(R);LW<<A;RW<<B;return L==R;
}
bool ExactVectorBytes(const FVector& A,const FVector& B)
{
 const double L[]={A.X,A.Y,A.Z},R[]={B.X,B.Y,B.Z};return FMemory::Memcmp(L,R,sizeof(L))==0;
}
FString TransformDifference(const FTransform& Source,const FTransform& Target);
bool RestoreNewTargetChildLocation(USceneComponent& Source,USceneComponent& Target,AActor* ExpectedSource,AActor* ExpectedTarget,
 UWorld* NewWorld,const TMap<UObject*,UObject*>& Remap,bool& Restored,FString& Evidence)
{
 Restored=false;Evidence.Reset();const FVector SourceLocation=Source.GetRelativeLocation(),TargetLocation=Target.GetRelativeLocation();
 if(ExactVectorBytes(SourceLocation,TargetLocation))return true;
 if(!ExpectedSource||!ExpectedTarget||!NewWorld||&Source==&Target||Source.GetOwner()!=ExpectedSource||Target.GetOwner()!=ExpectedTarget||
    Source.GetWorld()==NewWorld||Target.GetWorld()!=NewWorld||Source.GetClass()!=Target.GetClass()||
    Remap.FindRef(ExpectedSource)!=ExpectedTarget||Remap.FindRef(&Source)!=&Target||
    &Source==ExpectedSource->GetRootComponent()||&Target==ExpectedTarget->GetRootComponent()||!Source.IsRegistered()||!Target.IsRegistered()||
    SourceLocation.ContainsNaN()||TargetLocation.ContainsNaN())
 {Evidence=TEXT("child local repair requires exact registered mapped NEW-world component/actor pair and finite vectors");return false;}
 auto* SourceParent=Source.GetAttachParent();auto* TargetParent=Target.GetAttachParent();
 TSet<const USceneComponent*> Ancestors;
 for(auto* P=SourceParent,*Q=TargetParent;P||Q;)
 {if(!P||!Q||Ancestors.Contains(P)||P->GetOwner()!=ExpectedSource||Q->GetOwner()!=ExpectedTarget||P->GetClass()!=Q->GetClass()||
     !P->IsRegistered()||!Q->IsRegistered()||Remap.FindRef(P)!=Q||P->GetAttachSocketName()!=Q->GetAttachSocketName())
  {Evidence=TEXT("child local repair requires complete exact mapped registered attachment hierarchy");return false;}
  Ancestors.Add(P);if((P==ExpectedSource->GetRootComponent())!=(Q==ExpectedTarget->GetRootComponent()))return false;
  P=P->GetAttachParent();Q=Q->GetAttachParent();}

 if(!SourceParent||!TargetParent||SourceParent->GetOwner()!=ExpectedSource||TargetParent->GetOwner()!=ExpectedTarget||
    Remap.FindRef(SourceParent)!=TargetParent||Source.GetAttachSocketName()!=Target.GetAttachSocketName()||
    !ExactTransformBytes(SourceParent->GetComponentTransform(),TargetParent->GetComponentTransform())||
    !ExactTransformBytes(SourceParent->GetSocketTransform(Source.GetAttachSocketName()),TargetParent->GetSocketTransform(Target.GetAttachSocketName()))||
    !ExactVectorBytes(Source.GetRelativeScale3D(),Target.GetRelativeScale3D())||
    Source.IsUsingAbsoluteLocation()!=Target.IsUsingAbsoluteLocation()||Source.IsUsingAbsoluteRotation()!=Target.IsUsingAbsoluteRotation()||Source.IsUsingAbsoluteScale()!=Target.IsUsingAbsoluteScale())
 {Evidence=TEXT("child local repair parent/socket/frame/scale/absolute policy differs");return false;}
 const FRotator SR=Source.GetRelativeRotation(),TR=Target.GetRelativeRotation();
 const double A[]={SR.Pitch,SR.Yaw,SR.Roll},B[]={TR.Pitch,TR.Yaw,TR.Roll};FRotator Qualified;FString RotationProof;
 if(FMemory::Memcmp(A,B,sizeof(A))&&!MeasuredRotation(Source,Target,Qualified,RotationProof))
 {
  const FQuat SQ=SR.Quaternion(),TQ=TR.Quaternion();
  const FQuat SC=Source.GetRelativeRotationCache().RotatorToQuat_ReadOnly(SR),TC=Target.GetRelativeRotationCache().RotatorToQuat_ReadOnly(TR);
  Evidence=FString::Printf(TEXT("child local repair rotation differs beyond existing qualification; sourceLoc=(%.17g,%.17g,%.17g) targetLoc=(%.17g,%.17g,%.17g) relativeEuler17 source=(%.17g,%.17g,%.17g) target=(%.17g,%.17g,%.17g) directQ source=(%.17g,%.17g,%.17g,%.17g) target=(%.17g,%.17g,%.17g,%.17g) readonlyCacheQ source=(%.17g,%.17g,%.17g,%.17g) target=(%.17g,%.17g,%.17g,%.17g)"),
   SourceLocation.X,SourceLocation.Y,SourceLocation.Z,TargetLocation.X,TargetLocation.Y,TargetLocation.Z,SR.Pitch,SR.Yaw,SR.Roll,TR.Pitch,TR.Yaw,TR.Roll,
   SQ.X,SQ.Y,SQ.Z,SQ.W,TQ.X,TQ.Y,TQ.Z,TQ.W,SC.X,SC.Y,SC.Z,SC.W,TC.X,TC.Y,TC.Z,TC.W);
  constexpr int Flags=PPF_DeepCompareInstances|PPF_ExportsNotFullyQualified|PPF_Copy|PPF_Delimited;
  if(auto* RotationProperty=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),TEXT("RelativeRotation")))
  {FString Text;RotationProperty->ExportTextItem_Direct(Text,RotationProperty->ContainerPtrToValuePtr<void>(&Source),nullptr,&Source,Flags);
   FRotator Expected=FRotator::ZeroRotator;FOutputDeviceNull Errors;const TCHAR* Tail=RotationProperty->ImportText_Direct(*Text,&Expected,&Target,Flags,&Errors);
   Evidence+=FString::Printf(TEXT(" stockRotatorExport={%s} parsed=%d expectedEuler17=(%.17g,%.17g,%.17g) flags=%d"),*Text,int32(Tail!=nullptr),Expected.Pitch,Expected.Yaw,Expected.Roll,Flags);}
  Evidence+=TEXT(" WORLD ")+TransformDifference(Source.GetComponentTransform(),Target.GetComponentTransform());return false;
 }
 auto* Property=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),TEXT("RelativeLocation"));
 if(!Property||Property->Struct!=TBaseStructure<FVector>::Get()||Property->ArrayDim!=1)return false;
 // Exact stock CopyActors -> LevelExporterT3D COPY -> ExportProperties flags:
 // EditorActor.cpp423, EditorExporters.cpp637, UnrealExporter.cpp1142.
 constexpr int Flags=PPF_DeepCompareInstances|PPF_ExportsNotFullyQualified|PPF_Copy|PPF_Delimited;
 FString Text;Property->ExportTextItem_Direct(Text,Property->ContainerPtrToValuePtr<void>(&Source),nullptr,&Source,Flags);
 FVector Expected=FVector::ZeroVector;FOutputDeviceNull Errors;
 const TCHAR* Tail=Property->ImportText_Direct(*Text,&Expected,&Target,Flags,&Errors);
 if(Tail)while(*Tail&&FChar::IsWhitespace(*Tail))++Tail;
 if(!Tail||*Tail||!ExactVectorBytes(Expected,TargetLocation))
 {Evidence=TEXT("child local difference is NOT exact stock TEXT roundtrip: ")+Text;return false;}
 Target.SetRelativeLocation_Direct(SourceLocation);
 Target.UpdateComponentToWorld(EUpdateTransformFlags::None,ETeleportType::TeleportPhysics);
 if(!ExactVectorBytes(SourceLocation,Target.GetRelativeLocation())||!ExactTransformBytes(Source.GetComponentTransform(),Target.GetComponentTransform()))
 {Evidence=TEXT("child local exact source/world postcondition failed");return false;}
 Restored=true;Evidence=FString::Printf(TEXT("RESTORED NEW TARGET child sourceRelative=(%.17g,%.17g,%.17g) TEXTtarget=(%.17g,%.17g,%.17g) exactStockFlags=%d export={%s}; exactworld/localpostcondition; source untouched"),SourceLocation.X,SourceLocation.Y,SourceLocation.Z,TargetLocation.X,TargetLocation.Y,TargetLocation.Z,Flags,*Text);return true;
}
bool RestoreNewTargetRawInstances(UInstancedStaticMeshComponent& Source,UInstancedStaticMeshComponent& Target,
 AActor* ExpectedSource,AActor* ExpectedTarget,UWorld* NewWorld,const TMap<UObject*,UObject*>& Remap,FString& Evidence,bool bRootRestored=false)
{
 Evidence.Reset();
 if(&Source==&Target||!ExpectedSource||!ExpectedTarget||!NewWorld||Source.GetOwner()!=ExpectedSource||Target.GetOwner()!=ExpectedTarget||
    Target.GetWorld()!=NewWorld||Source.GetWorld()==NewWorld||Remap.FindRef(&Source)!=&Target||
    Source.GetClass()!=UInstancedStaticMeshComponent::StaticClass()||Target.GetClass()!=Source.GetClass()||
    !Source.GetStaticMesh()||Source.GetStaticMesh()!=Target.GetStaticMesh()||Source.PerInstanceSMData.Num()!=Target.PerInstanceSMData.Num())
 {Evidence=TEXT("raw instance repair requires exact mapped base-ISM/new-world owners, mesh and indexed count");return false;}
 bool Different=false;
 for(int I=0;I<Source.PerInstanceSMData.Num();++I)for(int R=0;R<4;++R)for(int C=0;C<4;++C)
 {
  const auto& A=Source.PerInstanceSMData[I].Transform.M[R][C];const auto& B=Target.PerInstanceSMData[I].Transform.M[R][C];
  if(!FMath::IsFinite(A)||!FMath::IsFinite(B)){Evidence=TEXT("nonfinite raw instance scalar");return false;}
  Different|=FMemory::Memcmp(&A,&B,sizeof(A))!=0;
 }
 // TEXT duplication can round a valid cached payload while retaining its hash,
 // even when raw matrices and root transform already match. Always rebuild
 // NEW-target derived caches through the same stock raw-data update path.
 // Stock DuplicateActors is TEXT export/import. Restore authored indexed raw
 // records only on NEW target; never reconstruct FTransform or touch source.
 TArray<FInstancedStaticMeshInstanceData> Copy=Source.PerInstanceSMData;
 if(Copy.Num()>0&&!Target.BatchUpdateInstancesData(0,Copy.Num(),Copy.GetData(),true,true))
 {Evidence=TEXT("stock raw instance update refused");return false;}
 Target.UpdateBounds(); // normal target-only derived cache refresh
 auto* CacheProperty=FindFProperty<FStructProperty>(UInstancedStaticMeshComponent::StaticClass(),TEXT("CachedBounds"));
 if(!CacheProperty||CacheProperty->ArrayDim!=3||CacheProperty->Struct!=FBoundsCacheElement::StaticStruct())
 {Evidence=TEXT("installed three-slot bounds cache schema differs");return false;}
 // Read source validity ONLY. Stock APIs recompute NEW-target slots invalidated
 // by BatchUpdateInstancesData; source cached hash/value/payload remain untouched.
 if(CacheProperty->ContainerPtrToValuePtr<FBoundsCacheElement>(&Source,1)->IsValid())Target.GetNavigationBounds();
 if(CacheProperty->ContainerPtrToValuePtr<FBoundsCacheElement>(&Source,2)->IsValid())Target.CalcBounds(FTransform::Identity);
 for(int I=0;I<Copy.Num();++I)for(int R=0;R<4;++R)for(int C=0;C<4;++C)
 {const auto& A=Source.PerInstanceSMData[I].Transform.M[R][C];const auto& B=Target.PerInstanceSMData[I].Transform.M[R][C];
  if(FMemory::Memcmp(&A,&B,sizeof(A))){Evidence=TEXT("stock raw instance update failed exact scalar postcondition");return false;}}
 Evidence=Different?FString::Printf(TEXT("RESTORED NEW TARGET %d indexed raw instance records through stock BatchUpdateInstancesData; exact16scalarpostcondition/source untouched; target normal bounds refresh"),Copy.Num()):FString::Printf(TEXT("REFRESHED NEW TARGET normal bounds after TEXT duplication (rootRestored=%d); all raw16scalars unchanged"),int32(bRootRestored));return true;
}
FString TransformDifference(const FTransform& Source,const FTransform& Target)
{
 FTransform S=Source,T=Target;TArray<uint8> A,B;FObjectWriter WA(A),WB(B);WA<<S;WB<<T;
 const FVector SP=S.GetTranslation(),TP=T.GetTranslation(),SS=S.GetScale3D(),TS=T.GetScale3D();
 const FQuat SQ=S.GetRotation(),TQ=T.GetRotation();
 return FString::Printf(TEXT("TRS17 sourceP=(%.17g,%.17g,%.17g) targetP=(%.17g,%.17g,%.17g) deltaP=(%.17g,%.17g,%.17g) sourceQ=(%.17g,%.17g,%.17g,%.17g) targetQ=(%.17g,%.17g,%.17g,%.17g) deltaQ=(%.17g,%.17g,%.17g,%.17g) sourceS=(%.17g,%.17g,%.17g) targetS=(%.17g,%.17g,%.17g) deltaS=(%.17g,%.17g,%.17g) finite=%d/%d Qnorm2=%.17g/%.17g bytes=%d/%d hexA=%s hexB=%s"),
  SP.X,SP.Y,SP.Z,TP.X,TP.Y,TP.Z,TP.X-SP.X,TP.Y-SP.Y,TP.Z-SP.Z,
  SQ.X,SQ.Y,SQ.Z,SQ.W,TQ.X,TQ.Y,TQ.Z,TQ.W,TQ.X-SQ.X,TQ.Y-SQ.Y,TQ.Z-SQ.Z,TQ.W-SQ.W,
  SS.X,SS.Y,SS.Z,TS.X,TS.Y,TS.Z,TS.X-SS.X,TS.Y-SS.Y,TS.Z-SS.Z,
  int32(!S.ContainsNaN()),int32(!T.ContainsNaN()),double(SQ.SizeSquared()),double(TQ.SizeSquared()),A.Num(),B.Num(),
  *BytesToHex(A.GetData(),A.Num()),*BytesToHex(B.GetData(),B.Num()));
}
FString NestedPropertyDifference(FProperty& P,void* SourceValue,void* TargetValue,UObject& Source,UObject& Target,
 const TMap<const UObject*,FString>& IDs,const TSet<const UPackage*>& Forbidden,const FString& Path,int Depth)
{
 TArray<uint8> A,B;FStateWriter SA(A,IDs,Forbidden,false),SB(B,IDs,Forbidden,true);
 P.SerializeItem(FStructuredArchiveFromArchive(SA).GetSlot(),SourceValue,nullptr);
 P.SerializeItem(FStructuredArchiveFromArchive(SB).GetSlot(),TargetValue,nullptr);
 if(A==B&&!SA.IsError()&&!SB.IsError()&&!SB.SourceReference)return FString();
 if(Depth<6)
 {
  if(auto* S=CastField<FStructProperty>(&P))
   for(TFieldIterator<FProperty> It(S->Struct);It;++It)
   {auto* Child=*It;if(!Child->ShouldSerializeValue(SA))continue;for(int I=0;I<Child->ArrayDim;++I)
    {FString D=NestedPropertyDifference(*Child,Child->ContainerPtrToValuePtr<void>(SourceValue,I),Child->ContainerPtrToValuePtr<void>(TargetValue,I),Source,Target,IDs,Forbidden,Path+TEXT(".")+Child->GetName()+FString::Printf(TEXT("[%d]"),I),Depth+1);if(!D.IsEmpty())return D;}}
  if(auto* Array=CastField<FArrayProperty>(&P))
  {FScriptArrayHelper Left(Array,SourceValue),Right(Array,TargetValue);
   if(Left.Num()==Right.Num())for(int I=0;I<Left.Num();++I)
   {FString D=NestedPropertyDifference(*Array->Inner,Left.GetRawPtr(I),Right.GetRawPtr(I),Source,Target,IDs,Forbidden,Path+FString::Printf(TEXT("[%d]"),I),Depth+1);if(!D.IsEmpty())return D;}}
 }
 int Offset=0;while(Offset<FMath::Min(A.Num(),B.Num())&&A[Offset]==B[Offset])++Offset;
 const int Start=FMath::Max(0,Offset-32),AN=FMath::Max(0,FMath::Min(A.Num()-Start,65)),BN=FMath::Max(0,FMath::Min(B.Num()-Start,65));
 const FString AH=AN?BytesToHex(A.GetData()+Start,AN):TEXT("empty"),BH=BN?BytesToHex(B.GetData()+Start,BN):TEXT("empty");
 FString X,Y;P.ExportTextItem_Direct(X,SourceValue,nullptr,&Source,PPF_None);P.ExportTextItem_Direct(Y,TargetValue,nullptr,&Target,PPF_None);
 FString Numeric;if(auto* N=CastField<FNumericProperty>(&P);N&&N->IsFloatingPoint())
 {const double L=N->GetFloatingPointPropertyValue(SourceValue),R=N->GetFloatingPointPropertyValue(TargetValue);Numeric=FString::Printf(TEXT(" numeric17=%.17g/%.17g delta=%.17g"),L,R,R-L);}
 return FString::Printf(TEXT(" nestedFirst=%s depth=%d propertyClass=%s flags=0x%llx canonicalBytes=%d/%d firstByte=%d hexStart=%d hexA=%s hexB=%s source={%s} target={%s}%s"),*Path,Depth,*P.GetClass()->GetName(),static_cast<unsigned long long>(P.GetPropertyFlags()),A.Num(),B.Num(),Offset,Start,*AH,*BH,*X.Left(384),*Y.Left(384),*Numeric);
}
FString BoundsCacheDiagnostic(UObject& O,FProperty& Property,int Index)
{
 auto* ISM=Cast<UInstancedStaticMeshComponent>(&O);auto* P=CastField<FStructProperty>(&Property);
 if(!ISM||!P||P->GetFName()!=TEXT("CachedBounds")||P->Struct!=FBoundsCacheElement::StaticStruct())return FString();
 const auto* Cache=P->ContainerPtrToValuePtr<FBoundsCacheElement>(ISM,Index);
 auto* HashProperty=FindFProperty<FUInt32Property>(P->Struct,TEXT("Hash"));
 if(!HashProperty)return TEXT(" cache diagnostic missing reflected Hash");
 const uint32 StoredHash=HashProperty->GetPropertyValue_InContainer(Cache);
 const FBoxSphereBounds Stored=Cache->GetValue(false);
 auto Values=[](const FBoxSphereBounds& V,TArray<uint8>& Raw)
 {const double D[]={V.Origin.X,V.Origin.Y,V.Origin.Z,V.BoxExtent.X,V.BoxExtent.Y,V.BoxExtent.Z,double(V.SphereRadius)};Raw.Append(reinterpret_cast<const uint8*>(D),sizeof(D));};
 TArray<uint8> StoredBytes;Values(Stored,StoredBytes);
 FString Result=FString::Printf(TEXT(" ISMCache[%d] valid=%d storedHash=%u storedValue17 origin=(%.17g,%.17g,%.17g) extent=(%.17g,%.17g,%.17g) radius=%.17g valueHex=%s"),Index,int32(Cache->IsValid()),StoredHash,Stored.Origin.X,Stored.Origin.Y,Stored.Origin.Z,Stored.BoxExtent.X,Stored.BoxExtent.Y,Stored.BoxExtent.Z,double(Stored.SphereRadius),*BytesToHex(StoredBytes.GetData(),StoredBytes.Num()));
 if(!ISM->GetStaticMesh()||ISM->PerInstanceSMData.Num()==0)return Result+TEXT(" noMeshOrInstances");
 // Exact installed InstancedStaticMesh.cpp3032-45/3133-44, READ ONLY.
 // Never CalcBounds/GetOrCalcBounds: those mutate source cache.
 const FTransform World=ISM->GetComponentTransform();FVector Translation=World.GetTranslation(),Scale=World.GetScale3D();FQuat Rotation=World.GetRotation();
 const FBox MeshBounds=ISM->GetStaticMesh()->GetBounds().GetBox();uint64 Hash=0;
 Hash=CityHash64WithSeed(reinterpret_cast<const char*>(&Translation),sizeof(Translation),Hash);
 Hash=CityHash64WithSeed(reinterpret_cast<const char*>(&Rotation),sizeof(Rotation),Hash);
 Hash=CityHash64WithSeed(reinterpret_cast<const char*>(&Scale),sizeof(Scale),Hash);
 Hash=CityHash64WithSeed(reinterpret_cast<const char*>(&MeshBounds.Min),sizeof(MeshBounds.Min),Hash);
 Hash=CityHash64WithSeed(reinterpret_cast<const char*>(&MeshBounds.Max),sizeof(MeshBounds.Max),Hash);
 const uint32 ExpectedHash=uint32(Hash)^uint32(Hash>>32);
 const FMatrix WorldMatrix=World.ToMatrixWithScale();FBoxSphereBounds::Builder Builder;FSHA1 Matrices;
 for(const auto& Instance:ISM->PerInstanceSMData){Builder+=MeshBounds.TransformBy(Instance.Transform*WorldMatrix);Matrices.Update(reinterpret_cast<const uint8*>(&Instance.Transform),sizeof(Instance.Transform));}
 Matrices.Final();uint8 MatrixDigest[20];Matrices.GetHash(MatrixDigest);
 const FBoxSphereBounds Expected=Builder;TArray<uint8> ExpectedBytes;Values(Expected,ExpectedBytes);
 Result+=FString::Printf(TEXT(" mesh=%s meshBounds17=(%.17g,%.17g,%.17g)/(%.17g,%.17g,%.17g) rawInstanceMatrices=%d SHA1=%s ownComponentHash=%u hashMatch=%d ownValue17 origin=(%.17g,%.17g,%.17g) extent=(%.17g,%.17g,%.17g) radius=%.17g ownValueHex=%s ownValueBitMatch=%d"),*ISM->GetStaticMesh()->GetPathName(),MeshBounds.Min.X,MeshBounds.Min.Y,MeshBounds.Min.Z,MeshBounds.Max.X,MeshBounds.Max.Y,MeshBounds.Max.Z,ISM->PerInstanceSMData.Num(),*BytesToHex(MatrixDigest,20),ExpectedHash,int32(ExpectedHash==StoredHash),Expected.Origin.X,Expected.Origin.Y,Expected.Origin.Z,Expected.BoxExtent.X,Expected.BoxExtent.Y,Expected.BoxExtent.Z,double(Expected.SphereRadius),*BytesToHex(ExpectedBytes.GetData(),ExpectedBytes.Num()),int32(ExpectedBytes==StoredBytes));
 return Result;
}
FString RawInstanceMatrixDifference(UObject& Source,UObject& Target)
{
 auto* A=Cast<UInstancedStaticMeshComponent>(&Source);auto* B=Cast<UInstancedStaticMeshComponent>(&Target);
 if(!A||!B)return FString();
 if(A->PerInstanceSMData.Num()!=B->PerInstanceSMData.Num())return FString::Printf(TEXT(" rawMatrixCounts=%d/%d"),A->PerInstanceSMData.Num(),B->PerInstanceSMData.Num());
 int Changed=0,ChangedMatrices=0,FirstInstance=INDEX_NONE;double MaxDelta=0;FString First;
 for(int I=0;I<A->PerInstanceSMData.Num();++I)
 {
  bool MatrixChanged=false;
  for(int R=0;R<4;++R)for(int C=0;C<4;++C)
  {
   const auto& X=A->PerInstanceSMData[I].Transform.M[R][C];const auto& Y=B->PerInstanceSMData[I].Transform.M[R][C];
   if(FMemory::Memcmp(&X,&Y,sizeof(X))==0)continue;
   ++Changed;MatrixChanged=true;MaxDelta=FMath::Max(MaxDelta,FMath::Abs(double(Y)-double(X)));
   if(FirstInstance==INDEX_NONE)
   {FirstInstance=I;
    First=FString::Printf(TEXT(" firstRawMatrix instance=%d row=%d col=%d scalarBytes=%d source=%.17g target=%.17g delta=%.17g signedzero=%d/%d sourceHex=%s targetHex=%s"),I,R,C,int(sizeof(X)),double(X),double(Y),double(Y)-double(X),int32(X==0&&std::signbit(double(X))),int32(Y==0&&std::signbit(double(Y))),*BytesToHex(reinterpret_cast<const uint8*>(&X),sizeof(X)),*BytesToHex(reinterpret_cast<const uint8*>(&Y),sizeof(Y)));}
  }
  ChangedMatrices+=MatrixChanged?1:0;
 }
 FString Result=FString::Printf(TEXT(" rawInstanceMatrixDiff instances=%d differingMatrices=%d differingScalars=%d maxAbsDelta=%.17g"),A->PerInstanceSMData.Num(),ChangedMatrices,Changed,MaxDelta)+First;
 int CanonicalDifferences=0;
 for(int InstanceIndex=0;InstanceIndex<A->PerInstanceSMData.Num();++InstanceIndex)
 {
  FTransform X,Y;const bool AX=A->GetInstanceTransform(InstanceIndex,X,false),BY=B->GetInstanceTransform(InstanceIndex,Y,false);
  TArray<uint8> L,R;if(AX&&BY){FObjectWriter LW(L),RW(R);LW<<X;RW<<Y;}
  CanonicalDifferences+=(!AX||!BY||L!=R)?1:0;
  if(InstanceIndex<8)Result+=FString::Printf(TEXT(" reconstructedLocalTransform instance=%d available=%d/%d canonicalBytes=%d/%d exactByteEqual=%d hexA=%s hexB=%s"),InstanceIndex,int32(AX),int32(BY),L.Num(),R.Num(),int32(AX&&BY&&L==R),*BytesToHex(L.GetData(),L.Num()),*BytesToHex(R.GetData(),R.Num()));
 }
 Result+=FString::Printf(TEXT(" reconstructedCanonicalDifferingInstances=%d first8HexReported"),CanonicalDifferences);
 return Result;
}
FString FirstStateDifference(UObject& Source,UObject& Target,const TMap<const UObject*,FString>& IDs,
 const TSet<const UPackage*>& Forbidden,FRotator* ComparisonRotation=nullptr)
{
 if(Source.GetClass()!=Target.GetClass())return TEXT("class mismatch ")+Source.GetClass()->GetPathName()+TEXT(" / ")+Target.GetClass()->GetPathName();
 for(TFieldIterator<FProperty> It(Source.GetClass());It;++It)
 {
  auto* P=*It;if(!TrackedProperty(*P,Source))continue;
  for(int StaticIndex=0;StaticIndex<P->ArrayDim;++StaticIndex)
  {
  TArray<uint8> A,B;FStateWriter SA(A,IDs,Forbidden,false),SB(B,IDs,Forbidden,true);
  P->SerializeItem(FStructuredArchiveFromArchive(SA).GetSlot(),ComparisonRotation&&RotationProperty(*P,Source)?static_cast<void*>(ComparisonRotation):P->ContainerPtrToValuePtr<void>(&Source,StaticIndex),nullptr);
  P->SerializeItem(FStructuredArchiveFromArchive(SB).GetSlot(),ComparisonRotation&&RotationProperty(*P,Target)?static_cast<void*>(ComparisonRotation):P->ContainerPtrToValuePtr<void>(&Target,StaticIndex),nullptr);
  if(A!=B||SB.SourceReference||SA.IsError()||SB.IsError())
  {
   FString X,Y;P->ExportTextItem_Direct(X,P->ContainerPtrToValuePtr<void>(&Source,StaticIndex),nullptr,&Source,PPF_None);
   P->ExportTextItem_Direct(Y,P->ContainerPtrToValuePtr<void>(&Target,StaticIndex),nullptr,&Target,PPF_None);
   const FString AH=A.Num()<=128?BytesToHex(A.GetData(),A.Num()):TEXT("over128bytes");
   const FString BH=B.Num()<=128?BytesToHex(B.GetData(),B.Num()):TEXT("over128bytes");
   FString Numeric=NestedPropertyDifference(*P,P->ContainerPtrToValuePtr<void>(&Source,StaticIndex),P->ContainerPtrToValuePtr<void>(&Target,StaticIndex),Source,Target,IDs,Forbidden,P->GetName()+FString::Printf(TEXT("[%d]"),StaticIndex),0);
   Numeric+=RawInstanceMatrixDifference(Source,Target);
   Numeric+=TEXT(" sourceCache:")+BoundsCacheDiagnostic(Source,*P,StaticIndex)+TEXT(" targetCache:")+BoundsCacheDiagnostic(Target,*P,StaticIndex);
   if(const auto* Struct=CastField<FStructProperty>(P);Struct&&Struct->Struct==TBaseStructure<FRotator>::Get())
   {
    const auto* R=P->ContainerPtrToValuePtr<FRotator>(&Source);const auto* T=P->ContainerPtrToValuePtr<FRotator>(&Target);
    Numeric+=FString::Printf(TEXT(" rotator17 source=(%.17g,%.17g,%.17g) target=(%.17g,%.17g,%.17g) delta=(%.17g,%.17g,%.17g)"),
     double(R->Pitch),double(R->Yaw),double(R->Roll),double(T->Pitch),double(T->Yaw),double(T->Roll),
     double(T->Pitch-R->Pitch),double(T->Yaw-R->Yaw),double(T->Roll-R->Roll));
    if(auto* SC=Cast<USceneComponent>(&Source))
    {
    auto* TC=CastChecked<USceneComponent>(&Target);
    const FQuat SQ=R->Quaternion(),TQ=T->Quaternion();
    const FQuat CachedS=SC->GetRelativeRotationCache().RotatorToQuat_ReadOnly(*R),CachedT=TC->GetRelativeRotationCache().RotatorToQuat_ReadOnly(*T);
    Numeric+=FString::Printf(TEXT(" localEulerQuat17 source=(%.17g,%.17g,%.17g,%.17g) target=(%.17g,%.17g,%.17g,%.17g) readonlyCacheQuat17 source=(%.17g,%.17g,%.17g,%.17g) target=(%.17g,%.17g,%.17g,%.17g) world "),
     SQ.X,SQ.Y,SQ.Z,SQ.W,TQ.X,TQ.Y,TQ.Z,TQ.W,CachedS.X,CachedS.Y,CachedS.Z,CachedS.W,CachedT.X,CachedT.Y,CachedT.Z,CachedT.W);
    Numeric+=TransformDifference(SC->GetComponentTransform(),TC->GetComponentTransform());
    }
   }
   return FString::Printf(TEXT("firstProperty=%s staticIndex=%d flags=0x%llx ownerClass=%s propertyClass=%s canonicalBytes=%d/%d targetSourceReference=%d source={%s} target={%s} canonicalHexA=%s canonicalHexB=%s%s"),
    *P->GetName(),StaticIndex,static_cast<unsigned long long>(P->GetPropertyFlags()),*P->GetOwnerClass()->GetPathName(),
    *P->GetClass()->GetName(),A.Num(),B.Num(),int32(SB.SourceReference),*X.Left(384),*Y.Left(384),*AH,*BH,*Numeric);
  }
  }
 }
 if(auto* A=Cast<AActor>(&Source))
 {auto* B=CastChecked<AActor>(&Target);return FString::Printf(TEXT("nonpropertyActorState hidden=%d/%d collision=%d/%d "),
  int32(A->IsHidden()),int32(B->IsHidden()),int32(A->GetActorEnableCollision()),int32(B->GetActorEnableCollision()))+TransformDifference(A->GetActorTransform(),B->GetActorTransform());}
 if(auto* A=Cast<UInstancedStaticMeshComponent>(&Source))
 {
  auto* B=CastChecked<UInstancedStaticMeshComponent>(&Target);
  if(A->GetInstanceCount()!=B->GetInstanceCount())return FString::Printf(TEXT("ISM count %d/%d"),A->GetInstanceCount(),B->GetInstanceCount());
  for(int32 I=0;I<A->GetInstanceCount();++I){FTransform X,Y;A->GetInstanceTransform(I,X,false);B->GetInstanceTransform(I,Y,false);
   if(!X.Equals(Y,0))return FString::Printf(TEXT("ISM firstIndex=%d "),I)+TransformDifference(X,Y);}
 }
 if(auto* A=Cast<USceneComponent>(&Source))return TEXT("nonpropertyComponentTRS ")+TransformDifference(A->GetComponentTransform(),CastChecked<USceneComponent>(&Target)->GetComponentTransform());
 return TEXT("state serialization differs outside filtered properties; no comparison waived");
}
bool State(UObject& O,const TMap<const UObject*,FString>& IDs,const TSet<const UPackage*>& Forbidden,bool Target,TArray<uint8>& Out,FRotator* ComparisonRotation=nullptr,FTransform* ActorComparisonTransform=nullptr,FTransform* RootComparisonTransform=nullptr,FTransform* ChildComparisonTransform=nullptr,FKAggregateGeom* AggregateComparison=nullptr)
{
 FStateWriter W(Out,IDs,Forbidden,Target);FString Class=O.GetClass()->GetPathName();W<<Class;
 for(TFieldIterator<FProperty> It(O.GetClass());It;++It)
 {
  auto* P=*It;if(!TrackedProperty(*P,O))continue;
  FVector RootLocation=RootComparisonTransform?RootComparisonTransform->GetTranslation():FVector::ZeroVector;
  FString Name=P->GetName();W<<Name;int32 StaticCount=P->ArrayDim;W<<StaticCount;
  for(int StaticIndex=0;StaticIndex<StaticCount;++StaticIndex)P->SerializeItem(FStructuredArchiveFromArchive(W).GetSlot(),ComparisonRotation&&RotationProperty(*P,O)?static_cast<void*>(ComparisonRotation):RootComparisonTransform&&RootLocationProperty(*P,O)?static_cast<void*>(&RootLocation):AggregateComparison&&AggregateProperty(*P,O)?static_cast<void*>(AggregateComparison):P->ContainerPtrToValuePtr<void>(&O,StaticIndex),nullptr);
 }
 if(auto* A=Cast<AActor>(&O)){FTransform T=ActorComparisonTransform?*ActorComparisonTransform:A->GetActorTransform();W<<T;bool H=A->IsHidden(),C=A->GetActorEnableCollision();W<<H<<C;}
 if(auto* C=Cast<USceneComponent>(&O)){FTransform T=RootComparisonTransform?*RootComparisonTransform:ChildComparisonTransform?*ChildComparisonTransform:C->GetComponentTransform();W<<T;}
 if(auto* C=Cast<UInstancedStaticMeshComponent>(&O))
 {int32 N=C->GetInstanceCount();W<<N;for(int32 I=0;I<N;++I){FTransform T;if(!C->GetInstanceTransform(I,T,false))return false;W<<T;
  for(int Row=0;Row<4;++Row)for(int Column=0;Column<4;++Column){auto Scalar=C->PerInstanceSMData[I].Transform.M[Row][Column];W.Serialize(&Scalar,sizeof(Scalar));}}}
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
 TArray<FString> Saved,Equivalences;int32 Count=0;auto Fail=[&](const FString& E){return Reply(false,E,Saved,Count,Equivalences);};
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
 TSet<AActor*> RestoredActors;
 // Restore every measured target root BEFORE any target State comparison.
 for(const auto& Pair:Targets)
 {AActor* Src=Sources[Pair.Key];AActor* Dst=Pair.Value;
  const bool Host=Cast<ADinkGreyboxScreen>(Src)&&Selected(CastChecked<ADinkGreyboxScreen>(Src)->ScreenNumber);
  if(Host)continue;bool Restored=false;FString Repair;
  if(!RestoreNewTargetRootTranslation(*Src,*Dst,World.Get(),Remap,Restored,Repair))return Fail(Pair.Key+TEXT(" ")+Repair);
  if(Restored){RestoredActors.Add(Dst);Equivalences.Add(Pair.Key+TEXT(" ")+Repair);}}
 TArray<USceneComponent*> OrderedChildren;
 for(const auto& Pair:Targets)
 {AActor* Src=Sources[Pair.Key];if(auto* Host=Cast<ADinkGreyboxScreen>(Src);Host&&Selected(Host->ScreenNumber))continue;
  for(const auto& Object:SourceObjects[Src])if(auto* Component=Cast<USceneComponent>(Object.Value);Component&&Component!=Src->GetRootComponent())OrderedChildren.Add(Component);}
 auto Depth=[](const USceneComponent* Component){int D=0;TSet<const USceneComponent*> Seen;for(auto* P=Component;P;P=P->GetAttachParent()){if(Seen.Contains(P))return MAX_int32;Seen.Add(P);++D;}return D;};
 OrderedChildren.Sort([&](const USceneComponent& A,const USceneComponent& B){const int X=Depth(&A),Y=Depth(&B);return X==Y?A.GetPathName()<B.GetPathName():X<Y;});
 for(auto* Src:OrderedChildren)
 {auto* Dst=Cast<USceneComponent>(Remap.FindRef(Src));auto* Owner=Src->GetOwner();auto* NewOwner=Cast<AActor>(Remap.FindRef(Owner));
  if(!Dst||!NewOwner||Depth(Src)==MAX_int32)return Fail(TEXT("child local repair missing mapping or cyclic attachment"));
  bool Restored=false;FString Repair;if(!RestoreNewTargetChildLocation(*Src,*Dst,Owner,NewOwner,World.Get(),Remap,Restored,Repair))return Fail(Src->GetPathName()+TEXT(" ")+Repair);
  if(Restored){RestoredActors.Add(NewOwner);Equivalences.Add(Repair);}}


 for(const auto& P:Targets)
 {
  AActor* Src=Sources[P.Key];AActor* Dst=P.Value;const bool Host=Cast<ADinkGreyboxScreen>(Src)&&Selected(CastChecked<ADinkGreyboxScreen>(Src)->ScreenNumber);
  TMap<FString,UObject*> Objects;AddObjects(*Dst,P.Key,IDs,Objects);
  for(const auto& O:SourceObjects[Src])
  {
   UObject* New=Remap.FindRef(O.Value);if(!New){if(Host)continue;return Fail(TEXT("candidate reference map incomplete"));}
   if(Host&&O.Value!=OldHosts[CastChecked<ADinkGreyboxScreen>(Src)->ScreenNumber]->Visual&&
      !Cast<UInstancedStaticMeshComponent>(O.Value)&&O.Value!=CastChecked<ADinkGreyboxScreen>(Src)->InstanceOrigins)continue;
   if(auto* SourceISM=Cast<UInstancedStaticMeshComponent>(O.Value))
   {auto* TargetISM=CastChecked<UInstancedStaticMeshComponent>(New);FString Repair;
    if(!RestoreNewTargetRawInstances(*SourceISM,*TargetISM,Src,Dst,World.Get(),Remap,Repair,RestoredActors.Contains(Dst)))return Fail(TEXT("raw instance repair refused: ")+P.Key+TEXT("/")+O.Key+TEXT(" ")+Repair);
    if(!Repair.IsEmpty())Equivalences.Add(P.Key+TEXT("/")+O.Key+TEXT(" ")+Repair);}
   TArray<uint8> A,B;if(!State(*O.Value,IDs,SourcePackages,false,A)||!State(*New,IDs,SourcePackages,true,B))return Fail(TEXT("candidate source-reference/state serialization refused: ")+P.Key+TEXT("/")+O.Key);
   if(A!=B)
   {
    FRotator Rotation;FTransform ActorTransform,RootTransform,ChildTransform;FString REvidence,TEvidence,RootEvidence,ChildEvidence,AggregateEvidence;FKAggregateGeom Aggregate;
    const bool R=MeasuredRotation(*O.Value,*New,Rotation,REvidence);
    const bool T=MeasuredActorTranslation(*O.Value,*New,ActorTransform,TEvidence);
    const bool Root=MeasuredRootTranslation(*O.Value,*New,Src,Dst,RootTransform,RootEvidence);
    const bool Child=MeasuredChildTranslation(*O.Value,*New,Src,Dst,Remap,ChildTransform,ChildEvidence);
    const bool BoxZero=MeasuredBoxRotationZero(*O.Value,*New,Src,Dst,Remap,IDs,SourcePackages,Aggregate,AggregateEvidence);
    if(!R&&!T&&!Root&&!Child&&!BoxZero)return Fail(TEXT("copied control/component mismatch: ")+P.Key+TEXT("/")+O.Key+TEXT(" ")+FirstStateDifference(*O.Value,*New,IDs,SourcePackages));
    // Pair comparison ONLY; only qualified root location/world share the owner delta.
    // Source before/after, local/instance transforms and Q/scale remain strict;
    // derived component-world translation only may share the exact owner delta.
    if(R)Equivalences.Add(P.Key+TEXT("/")+O.Key+TEXT(" ")+REvidence);
    if(T)Equivalences.Add(P.Key+TEXT("/")+O.Key+TEXT(" ")+TEvidence);
    if(Root)Equivalences.Add(P.Key+TEXT("/")+O.Key+TEXT(" ")+RootEvidence);
    if(Child)Equivalences.Add(P.Key+TEXT("/")+O.Key+TEXT(" ")+ChildEvidence);
    if(BoxZero)Equivalences.Add(P.Key+TEXT("/")+O.Key+TEXT(" ")+AggregateEvidence);
    A.Reset();B.Reset();
    if(!State(*O.Value,IDs,SourcePackages,false,A,R?&Rotation:nullptr,T?&ActorTransform:nullptr,Root?&RootTransform:nullptr,Child?&ChildTransform:nullptr,BoxZero?&Aggregate:nullptr)||
       !State(*New,IDs,SourcePackages,true,B,R?&Rotation:nullptr,T?&ActorTransform:nullptr,Root?&RootTransform:nullptr,Child?&ChildTransform:nullptr,BoxZero?&Aggregate:nullptr)||A!=B)
     return Fail(TEXT("copied control/component mismatch after measured representation: ")+P.Key+TEXT("/")+O.Key+TEXT(" ")+FirstStateDifference(*O.Value,*New,IDs,SourcePackages,R?&Rotation:nullptr));
   }
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
 Count=Targets.Num();return Reply(true,TEXT(""),Saved,Count,Equivalences);
}

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkStageActorTranslationRegression,
 "Dink.Import.Foundation.ActorTranslationRepresentation",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FDinkStageActorTranslationRegression::RunTest(const FString&)
{
 const double Y=-158083.09999999998;
 const double One=std::nextafter(Y,-std::numeric_limits<double>::infinity());
 const double Two=std::nextafter(One,-std::numeric_limits<double>::infinity());
 const FTransform Source(FQuat::Identity,FVector(5,Y,8),FVector::OneVector);
 FTransform Target=Source,Canonical;FString Evidence;
 Target.SetTranslation(FVector(5,One,8));
 TestTrue(TEXT("actual measured one-adjacent-double actorworld translation qualifies"),MeasuredWorldTranslation(Source,Target,Canonical,Evidence));
 TestTrue(TEXT("canonical is exactsource transform"),Canonical.Equals(Source,0));
 Target.SetTranslation(FVector(5,Two,8));
 TestFalse(TEXT("two adjacent doubles refuse"),MeasuredWorldTranslation(Source,Target,Canonical,Evidence));
 Target=Source;Target.SetTranslation(FVector(5,One,8));Target.SetRotation(FQuat(FVector::UpVector,.001));
 TestFalse(TEXT("rotation change refuses even with one-ULP translation"),MeasuredWorldTranslation(Source,Target,Canonical,Evidence));
 Target=Source;Target.SetTranslation(FVector(5,One,8));Target.SetScale3D(FVector(1,1,std::nextafter(1.,2.)));
 TestFalse(TEXT("one-bit scale change refuses"),MeasuredWorldTranslation(Source,Target,Canonical,Evidence));
 const double A[]={5,Y,8},NaN[]={5,std::numeric_limits<double>::quiet_NaN(),8},Infinity[]={5,std::numeric_limits<double>::infinity(),8};
 TestFalse(TEXT("nonfinite NaN translation refuses in actual production predicate"),AdjacentTranslationValues(A,NaN));
 TestFalse(TEXT("nonfinite infinity translation refuses in actual production predicate"),AdjacentTranslationValues(A,Infinity));
 auto* Component=NewObject<USceneComponent>();
 TestFalse(TEXT("component cannot use actorworld exception"),MeasuredActorTranslation(*Component,*Component,Canonical,Evidence));
 UWorld* World=UWorld::CreateWorld(EWorldType::Game,false);
 if(!TestNotNull(TEXT("owned root predicate scratch world"),World))return false;
 ON_SCOPE_EXIT{World->DestroyWorld(false);World->MarkObjectsPendingKill();};
 AActor* OwnerA=World->SpawnActor<AActor>();AActor* OwnerB=World->SpawnActor<AActor>();AActor* Wrong=World->SpawnActor<AActor>();
 auto* RootA=NewObject<USceneComponent>(OwnerA);auto* RootB=NewObject<USceneComponent>(OwnerB);
 OwnerA->SetRootComponent(RootA);OwnerB->SetRootComponent(RootB);
 RootA->SetWorldTransform(Source);Target=Source;Target.SetTranslation(FVector(5,One,8));RootB->SetWorldTransform(Target);
 TestTrue(TEXT("actual roots sharing corresponding owner one-ULP delta qualify"),MeasuredRootTranslation(*RootA,*RootB,OwnerA,OwnerB,Canonical,Evidence));
 TestFalse(TEXT("wrong corresponding target actor refuses"),MeasuredRootTranslation(*RootA,*RootB,OwnerA,Wrong,Canonical,Evidence));
 auto* Nonroot=NewObject<USceneComponent>(OwnerB);Nonroot->SetWorldTransform(Target);
 TestFalse(TEXT("nonroot component refuses"),MeasuredRootTranslation(*RootA,*Nonroot,OwnerA,OwnerB,Canonical,Evidence));
 RootB->SetupAttachment(Nonroot);
 TestFalse(TEXT("attached root refuses"),MeasuredRootTranslation(*RootA,*RootB,OwnerA,OwnerB,Canonical,Evidence));
 // Fresh root avoids SetWorldTransform's cached/nearly-equal early-out after
 // the preceding one-ULP case. Prove the stored inputs before testing refusal.
 AActor* OwnerTwo=World->SpawnActor<AActor>();auto* RootTwo=NewObject<USceneComponent>(OwnerTwo);
 OwnerTwo->SetRootComponent(RootTwo);RootTwo->SetRelativeLocation(FVector(5,Two,8));
 TestEqual(TEXT("two-ULP fixture stores exact relative scalar"),RootTwo->GetRelativeLocation().Y,Two);
 TestEqual(TEXT("two-ULP fixture stores exact world scalar"),RootTwo->GetComponentLocation().Y,Two);
 TestEqual(TEXT("two-ULP fixture stores exact owner scalar"),OwnerTwo->GetActorLocation().Y,Two);
 TestFalse(TEXT("two-ULP actual root and owner refuse"),MeasuredRootTranslation(*RootA,*RootTwo,OwnerA,OwnerTwo,Canonical,Evidence));
 RootB->SetupAttachment(nullptr);
 auto* ChildA=NewObject<USceneComponent>(OwnerA);auto* ChildB=NewObject<USceneComponent>(OwnerB);
 ChildA->SetupAttachment(RootA);ChildB->SetupAttachment(RootB);
 ChildA->SetRelativeLocation(FVector(0,0,10));ChildB->SetRelativeLocation(FVector(0,0,10));
 TMap<UObject*,UObject*> Mapping;Mapping.Add(RootA,RootB);
 TestTrue(TEXT("mapped child exact owner delta qualifies"),MeasuredChildTranslation(*ChildA,*ChildB,OwnerA,OwnerB,Mapping,Canonical,Evidence));
 TestFalse(TEXT("child wrong corresponding owner refuses"),MeasuredChildTranslation(*ChildA,*ChildB,OwnerA,Wrong,Mapping,Canonical,Evidence));
 TMap<UObject*,UObject*> WrongMapping;WrongMapping.Add(RootA,RootTwo);
 TestFalse(TEXT("child mismatched attachment mapping refuses"),MeasuredChildTranslation(*ChildA,*ChildB,OwnerA,OwnerB,WrongMapping,Canonical,Evidence));
 ChildB->SetRelativeLocation(FVector(0,0,11));
 TestFalse(TEXT("child local change refuses"),MeasuredChildTranslation(*ChildA,*ChildB,OwnerA,OwnerB,Mapping,Canonical,Evidence));
 FTransform Different=ChildA->GetComponentTransform();Different.AddToTranslation(FVector(0,Two-Y,0));
 TestFalse(TEXT("derived child different world delta refuses"),DerivedWorldDelta(ChildA->GetComponentTransform(),Different,OwnerA->GetActorTransform(),OwnerB->GetActorTransform()));
 auto* ISMA=NewObject<UInstancedStaticMeshComponent>(OwnerA);auto* ISMB=NewObject<UInstancedStaticMeshComponent>(OwnerB);
 ISMA->SetupAttachment(RootA);ISMB->SetupAttachment(RootB);
 ISMA->SetRelativeLocation(FVector(0,0,10));ISMB->SetRelativeLocation(FVector(0,0,10));
 TestTrue(TEXT("ISM component derived world delta qualifies while instances remain raw"),MeasuredChildTranslation(*ISMA,*ISMB,OwnerA,OwnerB,Mapping,Canonical,Evidence));
 ISMA->AddInstance(FTransform::Identity,false);
 TestEqual(TEXT("actual raw-instance fixture has one instance"),ISMA->GetInstanceCount(),1);
 TMap<const UObject*,FString> TestIDs;TestIDs.Add(OwnerA,TEXT("owner"));TestIDs.Add(RootA,TEXT("root"));
 TSet<const UPackage*> NoForbidden;TArray<uint8> BeforeInstance,AfterInstance;
 TestTrue(TEXT("actual ISM state serializes before instance change"),State(*ISMA,TestIDs,NoForbidden,false,BeforeInstance,nullptr,nullptr,nullptr,&Canonical));
 TestTrue(TEXT("actual raw-instance mutation succeeds"),ISMA->UpdateInstanceTransform(0,FTransform(FVector(0,0,1)),false,false,false));
 TestTrue(TEXT("actual ISM state serializes after instance change"),State(*ISMA,TestIDs,NoForbidden,false,AfterInstance,nullptr,nullptr,nullptr,&Canonical));
 TestTrue(TEXT("changed instance bytes refuse even with identical component world override"),BeforeInstance!=AfterInstance);
 auto* CacheProperty=FindFProperty<FStructProperty>(UInstancedStaticMeshComponent::StaticClass(),TEXT("CachedBounds"));
 if(!TestNotNull(TEXT("actual ISM static cache property"),CacheProperty))return false;
 TestEqual(TEXT("installed Component Navigation Local cache slots"),CacheProperty->ArrayDim,3);
 for(int Index:{1,2})
 {
  auto* Cache=CacheProperty->ContainerPtrToValuePtr<FBoundsCacheElement>(ISMA,Index);const FBoundsCacheElement Original=*Cache;
  TArray<uint8> CacheBefore,CacheAfter;
  TestTrue(TEXT("all-slots source serialization before mutation"),State(*ISMA,TestIDs,NoForbidden,false,CacheBefore));
  Cache->CacheValue(FBoxSphereBounds(FVector(1,2,3),FVector(4,5,6),7),123+Index);
  TestTrue(TEXT("all-slots source serialization after mutation"),State(*ISMA,TestIDs,NoForbidden,false,CacheAfter));
  TestTrue(FString::Printf(TEXT("static cache index%d mutation is detected"),Index),CacheBefore!=CacheAfter);*Cache=Original;
 }

 auto* RotA=NewObject<USceneComponent>(OwnerA);auto* RotB=NewObject<USceneComponent>(OwnerB);
 RotA->SetRelativeRotation(FRotator(0,-90,0));RotB->SetRelativeRotation(FRotator(0,-90,0));
 // Reproduce the measured stored Euler representation without recomputing the
 // world/cache: both orientations are proven identical by production guards.
 auto* RP=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),TEXT("RelativeRotation"));
 if(!TestNotNull(TEXT("actual typed RelativeRotation property"),RP))return false;
 auto* Stored=RP->ContainerPtrToValuePtr<FRotator>(RotA);
 Stored->Yaw=std::nextafter(-90.,0.);RP->ContainerPtrToValuePtr<FRotator>(RotB)->Yaw=-90.;
 TestEqual(TEXT("Euler fixture stores exact measured source yaw"),RotA->GetRelativeRotation().Yaw,std::nextafter(-90.,0.));
 TestEqual(TEXT("Euler fixture stores exact measured target yaw"),RotB->GetRelativeRotation().Yaw,-90.);
 const FQuat FixtureS=RotA->GetRelativeRotation().Quaternion(),FixtureT=RotB->GetRelativeRotation().Quaternion();
 AddInfo(FString::Printf(TEXT("MeasuredEuler fixture sourceYaw=%.17g targetYaw=%.17g directQ source=(%.17g,%.17g,%.17g,%.17g) target=(%.17g,%.17g,%.17g,%.17g)"),RotA->GetRelativeRotation().Yaw,RotB->GetRelativeRotation().Yaw,FixtureS.X,FixtureS.Y,FixtureS.Z,FixtureS.W,FixtureT.X,FixtureT.Y,FixtureT.Z,FixtureT.W));
 FRotator RotationCanonical;FString RotationEvidence;
 TestTrue(TEXT("actual measured one-ULP Euler with bitidentical direct/cache/world Q qualifies"),MeasuredAdjacentRotation(*RotA,*RotB,RotationCanonical,RotationEvidence));
 Stored->Yaw=std::nextafter(Stored->Yaw,0.);
 TestFalse(TEXT("two-ULP Euler refuses"),MeasuredAdjacentRotation(*RotA,*RotB,RotationCanonical,RotationEvidence));
 Stored->Yaw=std::numeric_limits<double>::quiet_NaN();
 TestFalse(TEXT("nonfinite Euler refuses"),MeasuredAdjacentRotation(*RotA,*RotB,RotationCanonical,RotationEvidence));
 Stored->Yaw=std::nextafter(-90.,0.);RotB->SetAbsolute(false,true,false);RotB->SetWorldRotation(FQuat(FVector::UpVector,.01));
 // Restore just the stored target Euler; actual world remains deliberately different.
 RP->ContainerPtrToValuePtr<FRotator>(RotB)->Yaw=-90.;
 TestFalse(TEXT("changed actual world quaternion refuses despite adjacent stored Euler"),MeasuredAdjacentRotation(*RotA,*RotB,RotationCanonical,RotationEvidence));
 TestFalse(TEXT("nonScene objects cannot use Euler representation comparison"),MeasuredAdjacentRotation(*OwnerA,*OwnerB,RotationCanonical,RotationEvidence));
 auto* BoxA=NewObject<UBoxComponent>(OwnerA);auto* BoxB=NewObject<UBoxComponent>(OwnerB);
 auto* BodyA=NewObject<UBodySetup>(BoxA);auto* BodyB=NewObject<UBodySetup>(BoxB);
 BodyA->AggGeom.BoxElems.Add(FKBoxElem(10,20,30));BodyB->AggGeom.BoxElems.Add(FKBoxElem(10,20,30));
 BodyA->AggGeom.BoxElems[0].Rotation.Roll=-0.;BodyB->AggGeom.BoxElems[0].Rotation.Roll=0.;Mapping.Add(BoxA,BoxB);Mapping.Add(BodyA,BodyB);
 FKAggregateGeom Aggregate;FString AggregateEvidence;TArray<uint8> SourceBefore,SourceAfter;
 TestTrue(TEXT("raw body source fingerprint before qualification"),State(*BodyA,TestIDs,NoForbidden,false,SourceBefore));
 TestTrue(TEXT("mapped box body signedzero rotation qualifies"),MeasuredBoxRotationZero(*BodyA,*BodyB,OwnerA,OwnerB,Mapping,TestIDs,NoForbidden,Aggregate,AggregateEvidence));
 TestTrue(TEXT("raw body source fingerprint after qualification"),State(*BodyA,TestIDs,NoForbidden,false,SourceAfter));
 TestTrue(TEXT("source body bytes unchanged"),SourceBefore==SourceAfter);
 TMap<UObject*,UObject*> WrongBodyMapping=Mapping;WrongBodyMapping.Remove(BodyA);
 TestFalse(TEXT("owned typed body without exact body mapping refuses"),MeasuredBoxRotationZero(*BodyA,*BodyB,OwnerA,OwnerB,WrongBodyMapping,TestIDs,NoForbidden,Aggregate,AggregateEvidence));
 TestFalse(TEXT("box body wrong corresponding owner refuses"),MeasuredBoxRotationZero(*BodyA,*BodyB,OwnerA,Wrong,Mapping,TestIDs,NoForbidden,Aggregate,AggregateEvidence));
 BodyB->AggGeom.BoxElems[0].Rotation.Yaw=1;
 TestFalse(TEXT("nonzero box rotation change refuses"),MeasuredBoxRotationZero(*BodyA,*BodyB,OwnerA,OwnerB,Mapping,TestIDs,NoForbidden,Aggregate,AggregateEvidence));
 BodyB->AggGeom.BoxElems[0].Rotation.Yaw=0;BodyB->AggGeom.BoxElems[0].X+=1;
 TestFalse(TEXT("box dimension change refuses"),MeasuredBoxRotationZero(*BodyA,*BodyB,OwnerA,OwnerB,Mapping,TestIDs,NoForbidden,Aggregate,AggregateEvidence));
 BodyB->AggGeom.BoxElems[0].X-=1;BodyB->AggGeom.BoxElems.Add(FKBoxElem(10,20,30));
 TestFalse(TEXT("box count change refuses"),MeasuredBoxRotationZero(*BodyA,*BodyB,OwnerA,OwnerB,Mapping,TestIDs,NoForbidden,Aggregate,AggregateEvidence));
 BodyB->AggGeom.BoxElems.Pop();BodyB->AggGeom.SphereElems.Add(FKSphereElem(1));
 TestFalse(TEXT("other geometry type change refuses"),MeasuredBoxRotationZero(*BodyA,*BodyB,OwnerA,OwnerB,Mapping,TestIDs,NoForbidden,Aggregate,AggregateEvidence));
 UWorld* NewWorld=UWorld::CreateWorld(EWorldType::Game,false);
 if(!TestNotNull(TEXT("owned separate NEW target world"),NewWorld))return false;
 ON_SCOPE_EXIT{NewWorld->DestroyWorld(false);NewWorld->MarkObjectsPendingKill();};
 AActor* NewOwner=NewWorld->SpawnActor<AActor>();auto* NewISM=NewObject<UInstancedStaticMeshComponent>(NewOwner);NewOwner->SetRootComponent(NewISM);
 UStaticMesh* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
 if(!TestNotNull(TEXT("real mesh for stock raw-record update fixture"),Cube))return false;
 ISMA->SetStaticMesh(Cube);NewISM->SetStaticMesh(Cube);NewISM->AddInstance(FTransform::Identity,false);
 TArray<FInstancedStaticMeshInstanceData> DesiredSourceRecords=ISMA->PerInstanceSMData;
 DesiredSourceRecords[0].Transform.M[3][0]=205.62000000002445;
 TestTrue(TEXT("scratch-source raw authoring setup uses stock invalidation API before fingerprint"),ISMA->BatchUpdateInstancesData(0,DesiredSourceRecords.Num(),DesiredSourceRecords.GetData(),false,true));
 NewISM->PerInstanceSMData[0].Transform=ISMA->PerInstanceSMData[0].Transform;NewISM->PerInstanceSMData[0].Transform.M[3][0]=205.62;
 TMap<UObject*,UObject*> RepairMap;RepairMap.Add(ISMA,NewISM);FString RepairEvidence;
 // Fixture setup intentionally computes scratch-source caches BEFORE fingerprint;
 // production RestoreNewTargetRawInstances only reads these validity flags.
 ISMA->UpdateBounds();ISMA->GetNavigationBounds();ISMA->CalcBounds(FTransform::Identity);
 NewISM->SetWorldTransform(ISMA->GetComponentTransform());
 TestTrue(TEXT("scratch source navigation cache valid before repair"),CacheProperty->ContainerPtrToValuePtr<FBoundsCacheElement>(ISMA,1)->IsValid());
 TestTrue(TEXT("scratch source local cache valid before repair"),CacheProperty->ContainerPtrToValuePtr<FBoundsCacheElement>(ISMA,2)->IsValid());
 TArray<uint8> RawSourceBefore,RawSourceAfter;
 TestTrue(TEXT("raw source state before NEW-target restoration"),State(*ISMA,TestIDs,NoForbidden,false,RawSourceBefore));
 TestTrue(TEXT("measured indexed matrix drift restored through stock NEW-target API"),RestoreNewTargetRawInstances(*ISMA,*NewISM,OwnerA,NewOwner,NewWorld,RepairMap,RepairEvidence));
 TestEqual(TEXT("target raw scalar equals exact source authored value"),NewISM->PerInstanceSMData[0].Transform.M[3][0],ISMA->PerInstanceSMData[0].Transform.M[3][0]);
 TestTrue(TEXT("raw source state after NEW-target restoration"),State(*ISMA,TestIDs,NoForbidden,false,RawSourceAfter));
 TestTrue(TEXT("source all cache slots/raw matrices unchanged by target API"),RawSourceBefore==RawSourceAfter);
 // Seed a VALID correct-hash but wrong-value target cache: force refresh must
 // invalidate through the stock raw API even when every matrix is already exact.
 auto* SeededCache=CacheProperty->ContainerPtrToValuePtr<FBoundsCacheElement>(NewISM,1);
 auto* CacheHashProperty=FindFProperty<FUInt32Property>(FBoundsCacheElement::StaticStruct(),TEXT("Hash"));
 if(!TestNotNull(TEXT("actual cache Hash property for stale-valid fixture"),CacheHashProperty))return false;
 const uint32 CorrectHash=CacheHashProperty->GetPropertyValue_InContainer(SeededCache);
 FBoxSphereBounds WrongValue=SeededCache->GetValue(false);WrongValue.Origin.X=std::nextafter(WrongValue.Origin.X,std::numeric_limits<double>::infinity());
 SeededCache->CacheValue(WrongValue,CorrectHash);
 TestTrue(TEXT("scratch target seeded cache remains VALID with original hash"),SeededCache->IsValid()&&CacheHashProperty->GetPropertyValue_InContainer(SeededCache)==CorrectHash);
 TestTrue(TEXT("restored-actor flag refreshes bounds with already-exact raw matrices"),RestoreNewTargetRawInstances(*ISMA,*NewISM,OwnerA,NewOwner,NewWorld,RepairMap,RepairEvidence,true));
 SeededCache->CacheValue(WrongValue,CorrectHash);
 TestTrue(TEXT("rawsame no-root-restoration refresh repairs TEXT-rounded valid matching-hash cache"),RestoreNewTargetRawInstances(*ISMA,*NewISM,OwnerA,NewOwner,NewWorld,RepairMap,RepairEvidence,false));
 TestTrue(TEXT("source state after restored-actor refresh"),State(*ISMA,TestIDs,NoForbidden,false,RawSourceAfter));
 TestTrue(TEXT("restored-actor refresh leaves all source slots unchanged"),RawSourceBefore==RawSourceAfter);
 for(int CacheIndex:{1,2})
 {
  auto* SourceCache=CacheProperty->ContainerPtrToValuePtr<FBoundsCacheElement>(ISMA,CacheIndex);
  auto* TargetCache=CacheProperty->ContainerPtrToValuePtr<FBoundsCacheElement>(NewISM,CacheIndex);
  TestTrue(FString::Printf(TEXT("target cache%d refreshed valid through normal API"),CacheIndex),TargetCache->IsValid());
  TArray<uint8> ExpectedCache,ActualCache;FObjectWriter ExpectedWriter(ExpectedCache),ActualWriter(ActualCache);
  CacheProperty->SerializeItem(FStructuredArchiveFromArchive(ExpectedWriter).GetSlot(),SourceCache,nullptr);
  CacheProperty->SerializeItem(FStructuredArchiveFromArchive(ActualWriter).GetSlot(),TargetCache,nullptr);
  if(ExpectedCache!=ActualCache)
  {
   AddInfo(TEXT("Cache fixture SOURCE ")+BoundsCacheDiagnostic(*ISMA,*CacheProperty,CacheIndex));
   AddInfo(TEXT("Cache fixture TARGET ")+BoundsCacheDiagnostic(*NewISM,*CacheProperty,CacheIndex));
   AddInfo(TEXT("Cache fixture component world ")+TransformDifference(ISMA->GetComponentTransform(),NewISM->GetComponentTransform()));
   AddInfo(FString::Printf(TEXT("Cache fixture canonical bytes=%d/%d hexSource=%s hexTarget=%s"),ExpectedCache.Num(),ActualCache.Num(),*BytesToHex(ExpectedCache.GetData(),ExpectedCache.Num()),*BytesToHex(ActualCache.GetData(),ActualCache.Num())));
  }
  FTransform SourcePose=ISMA->GetComponentTransform(),TargetPose=NewISM->GetComponentTransform();TArray<uint8> SourcePoseBytes,TargetPoseBytes;
  FObjectWriter SourcePoseWriter(SourcePoseBytes),TargetPoseWriter(TargetPoseBytes);SourcePoseWriter<<SourcePose;TargetPoseWriter<<TargetPose;
  TestTrue(TEXT("cache fixture SOURCE and TARGET world TRS byteexact precondition"),SourcePoseBytes==TargetPoseBytes);
  TestTrue(FString::Printf(TEXT("target cache%d actual recomputed fields equal exact own source-aligned geometry"),CacheIndex),ExpectedCache==ActualCache);
 }

 TestFalse(TEXT("raw restoration wrong target owner refuses"),RestoreNewTargetRawInstances(*ISMA,*NewISM,OwnerA,Wrong,NewWorld,RepairMap,RepairEvidence));
 TestFalse(TEXT("raw restoration rejects source world as NEW world"),RestoreNewTargetRawInstances(*ISMA,*NewISM,OwnerA,NewOwner,World,RepairMap,RepairEvidence));
 NewISM->SetStaticMesh(nullptr);
 TestFalse(TEXT("raw restoration different mesh refuses"),RestoreNewTargetRawInstances(*ISMA,*NewISM,OwnerA,NewOwner,NewWorld,RepairMap,RepairEvidence));
 NewISM->SetStaticMesh(Cube);NewISM->AddInstance(FTransform::Identity,false);
 TestFalse(TEXT("raw restoration different indexed count refuses"),RestoreNewTargetRawInstances(*ISMA,*NewISM,OwnerA,NewOwner,NewWorld,RepairMap,RepairEvidence));
 ISMA->PerInstanceSMData[0].Transform.M[0][1]=0.;
 TArray<uint8> RawFingerprintBefore,RawFingerprintAfter;
 TestTrue(TEXT("raw matrix fingerprint before signedzero scalar mutation"),State(*ISMA,TestIDs,NoForbidden,false,RawFingerprintBefore));
 ISMA->PerInstanceSMData[0].Transform.M[0][1]=-0.;
 TestTrue(TEXT("raw matrix fingerprint after signedzero scalar mutation"),State(*ISMA,TestIDs,NoForbidden,false,RawFingerprintAfter));
 TestTrue(TEXT("raw16scalar State detects signedzero matrix mutation"),RawFingerprintBefore!=RawFingerprintAfter);
 AActor* RootSourceOwner=World->SpawnActor<AActor>();AActor* RootTargetOwner=NewWorld->SpawnActor<AActor>();
 auto* RepairSourceRoot=NewObject<USceneComponent>(RootSourceOwner);auto* RepairTargetRoot=NewObject<USceneComponent>(RootTargetOwner);
 RootSourceOwner->SetRootComponent(RepairSourceRoot);RootTargetOwner->SetRootComponent(RepairTargetRoot);
 auto SetExact=[](USceneComponent& C,const FVector& P){C.SetRelativeLocation_Direct(P);C.UpdateComponentToWorld(EUpdateTransformFlags::None,ETeleportType::TeleportPhysics);};
 SetExact(*RepairSourceRoot,FVector(5,Y,8));SetExact(*RepairTargetRoot,FVector(5,One,8));
 TestEqual(TEXT("root repair fixture stores exact source endpoint"),RootSourceOwner->GetActorLocation().Y,Y);
 TestEqual(TEXT("root repair fixture stores exact target endpoint"),RootTargetOwner->GetActorLocation().Y,One);
 TMap<UObject*,UObject*> RootMap;RootMap.Add(RootSourceOwner,RootTargetOwner);RootMap.Add(RepairSourceRoot,RepairTargetRoot);
 TArray<uint8> RootSourceBefore,RootSourceAfter;TestTrue(TEXT("root source state before repair serializes"),State(*RepairSourceRoot,TestIDs,NoForbidden,false,RootSourceBefore));
 bool RootRestored=false;FString RootRepairEvidence;
 TestTrue(TEXT("measured NEW-target root restoration succeeds"),RestoreNewTargetRootTranslation(*RootSourceOwner,*RootTargetOwner,NewWorld,RootMap,RootRestored,RootRepairEvidence));
 TestTrue(TEXT("measured NEW-target root actually restored"),RootRestored);
 TestEqual(TEXT("restored actual target actor endpoint exactsource"),RootTargetOwner->GetActorLocation().Y,Y);
 TestTrue(TEXT("root source state after repair serializes"),State(*RepairSourceRoot,TestIDs,NoForbidden,false,RootSourceAfter));TestTrue(TEXT("root source raw state unchanged"),RootSourceBefore==RootSourceAfter);
 SetExact(*RepairTargetRoot,FVector(5,One,8));TMap<UObject*,UObject*> BadRootMap=RootMap;BadRootMap.Remove(RepairSourceRoot);
 TestFalse(TEXT("root restoration wrong root mapping refuses"),RestoreNewTargetRootTranslation(*RootSourceOwner,*RootTargetOwner,NewWorld,BadRootMap,RootRestored,RootRepairEvidence));
 TMap<UObject*,UObject*> BadActorMap=RootMap;BadActorMap.Remove(RootSourceOwner);
 TestFalse(TEXT("root restoration wrong actor mapping refuses"),RestoreNewTargetRootTranslation(*RootSourceOwner,*RootTargetOwner,NewWorld,BadActorMap,RootRestored,RootRepairEvidence));
 TestFalse(TEXT("root restoration wrong NEW world refuses"),RestoreNewTargetRootTranslation(*RootSourceOwner,*RootTargetOwner,World,RootMap,RootRestored,RootRepairEvidence));
 auto* Attach=NewObject<USceneComponent>(RootTargetOwner);RepairTargetRoot->SetupAttachment(Attach);
 RestoreNewTargetRootTranslation(*RootSourceOwner,*RootTargetOwner,NewWorld,RootMap,RootRestored,RootRepairEvidence);
 TestFalse(TEXT("attached target root not restored"),RootRestored);RepairTargetRoot->SetupAttachment(nullptr);
 SetExact(*RepairTargetRoot,FVector(5,Two,8));
 RestoreNewTargetRootTranslation(*RootSourceOwner,*RootTargetOwner,NewWorld,RootMap,RootRestored,RootRepairEvidence);
 TestFalse(TEXT("two-ULP target root not restored"),RootRestored);TestEqual(TEXT("two-ULP target unchanged"),RootTargetOwner->GetActorLocation().Y,Two);
 SetExact(*RepairTargetRoot,FVector(5,One,8));RepairTargetRoot->SetRelativeScale3D(FVector(1,1,2));
 RestoreNewTargetRootTranslation(*RootSourceOwner,*RootTargetOwner,NewWorld,RootMap,RootRestored,RootRepairEvidence);
 TestFalse(TEXT("changed scale target root not restored"),RootRestored);
 RepairTargetRoot->SetRelativeScale3D(FVector::OneVector);RepairTargetRoot->SetRelativeRotation(FRotator(0,.01,0));
 RestoreNewTargetRootTranslation(*RootSourceOwner,*RootTargetOwner,NewWorld,RootMap,RootRestored,RootRepairEvidence);
 TestFalse(TEXT("changed quaternion target root not restored"),RootRestored);
 AActor* LocalOwnerS=World->SpawnActor<AActor>();AActor* LocalOwnerT=NewWorld->SpawnActor<AActor>();
 auto* ParentS=NewObject<USceneComponent>(LocalOwnerS);auto* ParentT=NewObject<USceneComponent>(LocalOwnerT);
 LocalOwnerS->SetRootComponent(ParentS);LocalOwnerT->SetRootComponent(ParentT);ParentS->RegisterComponent();ParentT->RegisterComponent();
 auto* LocalS=NewObject<USceneComponent>(LocalOwnerS);auto* LocalT=NewObject<USceneComponent>(LocalOwnerT);
 LocalS->SetupAttachment(ParentS);LocalT->SetupAttachment(ParentT);LocalS->RegisterComponent();LocalT->RegisterComponent();
 const FVector ObservedS(-116.95999999999185,3.25,1.5),ObservedT(-116.95999999999999,3.25,1.5);
 SetExact(*LocalS,ObservedS);SetExact(*LocalT,ObservedT);
 TMap<UObject*,UObject*> LocalMap;LocalMap.Add(LocalOwnerS,LocalOwnerT);LocalMap.Add(ParentS,ParentT);LocalMap.Add(LocalS,LocalT);
 TArray<uint8> LocalBefore,LocalAfter;TestTrue(TEXT("local source pre-repair raw state available"),State(*LocalS,TestIDs,NoForbidden,false,LocalBefore));
 bool LocalRestored=false;FString LocalProof;
 TestTrue(TEXT("actual Card TEXT-roundtrip >oneULP childlocal restoration succeeds"),RestoreNewTargetChildLocation(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 TestTrue(TEXT("actual Card childlocal restoration was performed"),LocalRestored);TestTrue(TEXT("actual Card source relative/world exact after repair"),ExactVectorBytes(LocalS->GetRelativeLocation(),LocalT->GetRelativeLocation())&&ExactTransformBytes(LocalS->GetComponentTransform(),LocalT->GetComponentTransform()));
 AddInfo(LocalProof);
 SetExact(*LocalT,ObservedT+FVector(1,0,0));
 TestFalse(TEXT("arbitrary child position is not repaired as TEXT drift"),RestoreNewTargetChildLocation(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 SetExact(*LocalT,ObservedT);TMap<UObject*,UObject*> BadLocalMap=LocalMap;BadLocalMap.Remove(LocalS);
 TestFalse(TEXT("child wrong component map refuses"),RestoreNewTargetChildLocation(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,BadLocalMap,LocalRestored,LocalProof));
 BadLocalMap=LocalMap;BadLocalMap.Remove(ParentS);
 TestFalse(TEXT("child wrong parent map refuses"),RestoreNewTargetChildLocation(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,BadLocalMap,LocalRestored,LocalProof));
 TestFalse(TEXT("child wrong NEW world refuses"),RestoreNewTargetChildLocation(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,World,LocalMap,LocalRestored,LocalProof));
 LocalT->AttachToComponent(ParentT,FAttachmentTransformRules::KeepRelativeTransform,TEXT("wrong_socket"));
 TestFalse(TEXT("child different attachment socket refuses"),RestoreNewTargetChildLocation(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 LocalT->AttachToComponent(ParentT,FAttachmentTransformRules::KeepRelativeTransform);
 LocalT->SetRelativeRotation(FRotator(0,1,0));
 TestFalse(TEXT("child changed rotation refuses"),RestoreNewTargetChildLocation(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 LocalT->SetRelativeRotation(FRotator::ZeroRotator);LocalT->SetRelativeScale3D(FVector(2,1,1));
 TestFalse(TEXT("child changed scale refuses"),RestoreNewTargetChildLocation(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 LocalT->SetRelativeScale3D(FVector::OneVector);
 auto* LocationProperty=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),TEXT("RelativeLocation"));
 LocationProperty->ContainerPtrToValuePtr<FVector>(LocalT)->X=std::numeric_limits<double>::quiet_NaN();
 TestFalse(TEXT("child nonfinite relative location refuses before setter"),RestoreNewTargetChildLocation(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 LocationProperty->ContainerPtrToValuePtr<FVector>(LocalT)->X=ObservedT.X;
 TestTrue(TEXT("local source post-repair raw state available"),State(*LocalS,TestIDs,NoForbidden,false,LocalAfter));TestTrue(TEXT("child source raw state never changed"),LocalBefore==LocalAfter);









 return true;
}
#endif
