#include "DinkHardnessFoundationLibrary.h"
#include "DinkInstanceOriginsComponent.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkWarpComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/BoxComponent.h"
#include "PhysicsEngine/BodySetup.h"
#include "PhysicsEngine/BodyInstance.h"
#include "Engine/Level.h"
#include "Engine/LevelStreaming.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Editor.h"
#include "Editor/UnrealEdEngine.h"
#include "UnrealEdGlobals.h"
#include "GameFramework/WorldSettings.h"
#include "Engine/DirectionalLight.h"
#include "Components/LightComponentBase.h"
#include "Components/LightComponent.h"
#include "UObject/GarbageCollection.h"
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
#include "UObject/UObjectThreadContext.h"
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
bool ExactTransformBytes(FTransform A,FTransform B);
bool ExactVectorBytes(const FVector& A,const FVector& B);
FString TransformDifference(const FTransform& Source,const FTransform& Target);
bool RestoreNewTargetRootTranslation(AActor& Source,AActor& Target,UWorld* NewWorld,
 const TMap<UObject*,UObject*>& Remap,bool& Restored,FString& Evidence)
{
 Restored=false;Evidence.Reset();
 if(&Source==&Target||!NewWorld||Target.GetWorld()!=NewWorld||Source.GetWorld()==NewWorld||
    Source.GetClass()!=Target.GetClass()||Remap.FindRef(&Source)!=&Target)
 {Evidence=TEXT("root restoration requires exact mapped actor in distinct NEW world");return false;}
 auto* A=Source.GetRootComponent();auto* B=Target.GetRootComponent();
 if(!A||!B)return true;
 const FRotator SR=A->GetRelativeRotation(),TR=B->GetRelativeRotation();
 const double EulerSource[]={SR.Pitch,SR.Yaw,SR.Roll},EulerTarget[]={TR.Pitch,TR.Yaw,TR.Roll};
 FRotator QualifiedRotation;FString RotationProof;
 const bool RotationDiff=FMemory::Memcmp(EulerSource,EulerTarget,sizeof(EulerSource))!=0;
 // Genuine Euler loss may accompany an independently proven stock-TEXT
 // position roundtrip (Stage27 S144_P01); restore both exact source fields.
 if(RotationDiff&&!MeasuredRotation(*A,*B,QualifiedRotation,RotationProof))
 {
  const FVector SL=A->GetRelativeLocation(),TL=B->GetRelativeLocation();
  if(A->GetOwner()!=&Source||B->GetOwner()!=&Target||A->GetClass()!=B->GetClass()||Remap.FindRef(A)!=B||
     A->GetAttachParent()||B->GetAttachParent()||!A->IsRegistered()||!B->IsRegistered()||
     SR.ContainsNaN()||TR.ContainsNaN()||SL.ContainsNaN()||TL.ContainsNaN()||
     A->GetRelativeScale3D().ContainsNaN()||B->GetRelativeScale3D().ContainsNaN()||
     !ExactVectorBytes(SL,Source.GetActorLocation())||!ExactVectorBytes(TL,Target.GetActorLocation())||
     !ExactVectorBytes(A->GetRelativeScale3D(),B->GetRelativeScale3D())||
     A->IsUsingAbsoluteLocation()!=B->IsUsingAbsoluteLocation()||A->IsUsingAbsoluteRotation()!=B->IsUsingAbsoluteRotation()||A->IsUsingAbsoluteScale()!=B->IsUsingAbsoluteScale())
  {
   const FVector SS=A->GetRelativeScale3D(),TS=B->GetRelativeScale3D();
   Evidence=FString::Printf(TEXT("root Euler guard DIFFERENCE ownerMatch=%d classSame=%d rootMap=%d unattached=%d registered=%d finitePose=%d positionExact=%d sourceLocalWorldP=%d targetLocalWorldP=%d scaleExact=%d absoluteExact=%d rootSource=%s rootTarget=%s parents=%s/%s localP17=(%.17g,%.17g,%.17g)/(%.17g,%.17g,%.17g) localEuler17=(%.17g,%.17g,%.17g)/(%.17g,%.17g,%.17g) localScale17=(%.17g,%.17g,%.17g)/(%.17g,%.17g,%.17g) absoluteSource=%d/%d/%d absoluteTarget=%d/%d/%d"),
    int32(A->GetOwner()==&Source&&B->GetOwner()==&Target),int32(A->GetClass()==B->GetClass()),int32(Remap.FindRef(A)==B),int32(!A->GetAttachParent()&&!B->GetAttachParent()),int32(A->IsRegistered()&&B->IsRegistered()),
    int32(!SR.ContainsNaN()&&!TR.ContainsNaN()&&!SL.ContainsNaN()&&!TL.ContainsNaN()&&!SS.ContainsNaN()&&!TS.ContainsNaN()),
    int32(ExactVectorBytes(SL,TL)),int32(ExactVectorBytes(SL,Source.GetActorLocation())),int32(ExactVectorBytes(TL,Target.GetActorLocation())),int32(ExactVectorBytes(SS,TS)),
    int32(A->IsUsingAbsoluteLocation()==B->IsUsingAbsoluteLocation()&&A->IsUsingAbsoluteRotation()==B->IsUsingAbsoluteRotation()&&A->IsUsingAbsoluteScale()==B->IsUsingAbsoluteScale()),
    *GetPathNameSafe(A),*GetPathNameSafe(B),*GetPathNameSafe(A->GetAttachParent()),*GetPathNameSafe(B->GetAttachParent()),SL.X,SL.Y,SL.Z,TL.X,TL.Y,TL.Z,SR.Pitch,SR.Yaw,SR.Roll,TR.Pitch,TR.Yaw,TR.Roll,SS.X,SS.Y,SS.Z,TS.X,TS.Y,TS.Z,
    int32(A->IsUsingAbsoluteLocation()),int32(A->IsUsingAbsoluteRotation()),int32(A->IsUsingAbsoluteScale()),int32(B->IsUsingAbsoluteLocation()),int32(B->IsUsingAbsoluteRotation()),int32(B->IsUsingAbsoluteScale()));
   Evidence+=TEXT(" ROOT WORLD ")+TransformDifference(A->GetComponentTransform(),B->GetComponentTransform());
   constexpr int Flags=PPF_DeepCompareInstances|PPF_ExportsNotFullyQualified|PPF_Copy|PPF_Delimited;
   for(const TCHAR* Name:{TEXT("RelativeLocation"),TEXT("RelativeRotation"),TEXT("RelativeScale3D")})
   {auto* P=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),Name);if(!P)continue;FString Text;P->ExportTextItem_Direct(Text,P->ContainerPtrToValuePtr<void>(A),nullptr,A,Flags);FOutputDeviceNull Errors;
    if(P->Struct==TBaseStructure<FRotator>::Get())
    {FRotator Expected=FRotator::ZeroRotator;const TCHAR* Tail=P->ImportText_Direct(*Text,&Expected,B,Flags,&Errors);if(Tail)while(*Tail&&FChar::IsWhitespace(*Tail))++Tail;const double X[]={Expected.Pitch,Expected.Yaw,Expected.Roll};
     Evidence+=FString::Printf(TEXT(" stock%s source={%s} parseComplete=%d matchesActualTarget=%d expected17=(%.17g,%.17g,%.17g) flags=%d"),Name,*Text,int32(Tail&&!*Tail),int32(Tail&&!*Tail&&!FMemory::Memcmp(X,EulerTarget,sizeof(X))),Expected.Pitch,Expected.Yaw,Expected.Roll,Flags);}
    else if(P->Struct==TBaseStructure<FVector>::Get())
    {FVector Expected=FVector::ZeroVector;const TCHAR* Tail=P->ImportText_Direct(*Text,&Expected,B,Flags,&Errors);if(Tail)while(*Tail&&FChar::IsWhitespace(*Tail))++Tail;const FVector Actual=FString(Name)==TEXT("RelativeLocation")?TL:TS;
     Evidence+=FString::Printf(TEXT(" stock%s source={%s} parseComplete=%d matchesActualTarget=%d expected17=(%.17g,%.17g,%.17g) flags=%d"),Name,*Text,int32(Tail&&!*Tail),int32(Tail&&!*Tail&&ExactVectorBytes(Expected,Actual)),Expected.X,Expected.Y,Expected.Z,Flags);}}
   return false;
  }
  auto* Property=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),TEXT("RelativeRotation"));
  if(!Property||Property->Struct!=TBaseStructure<FRotator>::Get()||Property->ArrayDim!=1)return false;
  constexpr int Flags=PPF_DeepCompareInstances|PPF_ExportsNotFullyQualified|PPF_Copy|PPF_Delimited;
  FString Text;Property->ExportTextItem_Direct(Text,Property->ContainerPtrToValuePtr<void>(A),nullptr,A,Flags);
  FRotator Expected=FRotator::ZeroRotator;FOutputDeviceNull Errors;
  const TCHAR* Tail=Property->ImportText_Direct(*Text,&Expected,B,Flags,&Errors);
  if(Tail)while(*Tail&&FChar::IsWhitespace(*Tail))++Tail;
  const double Parsed[]={Expected.Pitch,Expected.Yaw,Expected.Roll};
  if(!Tail||*Tail||FMemory::Memcmp(Parsed,EulerTarget,sizeof(Parsed)))
  {Evidence=TEXT("root Euler difference is NOT exact stock TEXT roundtrip: ")+Text;return false;}
  FString LocationText;
  if(!ExactVectorBytes(SL,TL))
  {
   auto* LocationProperty=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),TEXT("RelativeLocation"));
   if(!LocationProperty||LocationProperty->Struct!=TBaseStructure<FVector>::Get()||LocationProperty->ArrayDim!=1)return false;
   LocationProperty->ExportTextItem_Direct(LocationText,LocationProperty->ContainerPtrToValuePtr<void>(A),nullptr,A,Flags);
   FVector ExpectedLocation=FVector::ZeroVector;
   const TCHAR* LocationTail=LocationProperty->ImportText_Direct(*LocationText,&ExpectedLocation,B,Flags,&Errors);
   if(LocationTail)while(*LocationTail&&FChar::IsWhitespace(*LocationTail))++LocationTail;
   if(!LocationTail||*LocationTail||!ExactVectorBytes(ExpectedLocation,TL))
   {Evidence=TEXT("root combined position difference is NOT exact stock TEXT roundtrip: ")+LocationText;return false;}
  }
  const FQuat Direct=SR.Quaternion(),Cached=A->GetRelativeRotationCache().RotatorToQuat_ReadOnly(SR);
  B->SetRelativeLocation_Direct(SL);
  B->SetRelativeRotation_Direct(SR);
  B->UpdateComponentToWorld(EUpdateTransformFlags::None,ETeleportType::TeleportPhysics);
  const FRotator After=B->GetRelativeRotation();const double Actual[]={After.Pitch,After.Yaw,After.Roll};
  if(FMemory::Memcmp(EulerSource,Actual,sizeof(Actual))||!ExactVectorBytes(SL,B->GetRelativeLocation())||
     !ExactTransformBytes(Source.GetActorTransform(),Target.GetActorTransform())||!ExactTransformBytes(A->GetComponentTransform(),B->GetComponentTransform()))
  {Evidence=TEXT("root Euler exact source-local/actor/world postcondition failed WORLD ")+TransformDifference(A->GetComponentTransform(),B->GetComponentTransform());return false;}
  Restored=true;Evidence=FString::Printf(TEXT("RESTORED NEW TARGET root Euler and source position via independently exact stock TEXT proof location={%s} flags=%d export={%s} sourceEuler=(%.17g,%.17g,%.17g) targetBefore=(%.17g,%.17g,%.17g) sourceDirectQ=(%.17g,%.17g,%.17g,%.17g) sourceReadonlyCacheQ=(%.17g,%.17g,%.17g,%.17g); exactlocal/actor/worldpostconditions; source untouched"),*LocationText,Flags,*Text,SR.Pitch,SR.Yaw,SR.Roll,TR.Pitch,TR.Yaw,TR.Roll,Direct.X,Direct.Y,Direct.Z,Direct.W,Cached.X,Cached.Y,Cached.Z,Cached.W);return true;
 }
 FTransform Canonical;FString Proof;
 // Keep the original ONE-ULP predicate unchanged. A separate position-only
 // path admits only the actual stock TEXT roundtrip measured at Stage29.
 if(!MeasuredRootTranslation(*A,*B,&Source,&Target,Canonical,Proof))
 {
  const FVector SL=A->GetRelativeLocation(),TL=B->GetRelativeLocation();
  if(RotationDiff||ExactVectorBytes(SL,TL))return true;
  if(A->GetOwner()!=&Source||B->GetOwner()!=&Target||A->GetClass()!=B->GetClass()||Remap.FindRef(A)!=B||
     A->GetAttachParent()||B->GetAttachParent()||!A->IsRegistered()||!B->IsRegistered()||
     SR.ContainsNaN()||TR.ContainsNaN()||SL.ContainsNaN()||TL.ContainsNaN()||
     A->GetRelativeScale3D().ContainsNaN()||B->GetRelativeScale3D().ContainsNaN()||
     !ExactVectorBytes(SL,Source.GetActorLocation())||!ExactVectorBytes(TL,Target.GetActorLocation())||
     !ExactTransformBytes(A->GetComponentTransform(),Source.GetActorTransform())||!ExactTransformBytes(B->GetComponentTransform(),Target.GetActorTransform())||
     !ExactTransformBytes(A->GetRelativeTransform(),A->GetComponentTransform())||!ExactTransformBytes(B->GetRelativeTransform(),B->GetComponentTransform())||
     !ExactQuaternion(A->GetComponentQuat(),B->GetComponentQuat())||
     !ExactQuaternion(A->GetRelativeRotationCache().RotatorToQuat_ReadOnly(SR),B->GetRelativeRotationCache().RotatorToQuat_ReadOnly(TR))||
     !ExactVectorBytes(A->GetRelativeScale3D(),B->GetRelativeScale3D())||
     A->IsUsingAbsoluteLocation()!=B->IsUsingAbsoluteLocation()||A->IsUsingAbsoluteRotation()!=B->IsUsingAbsoluteRotation()||A->IsUsingAbsoluteScale()!=B->IsUsingAbsoluteScale())
  {Evidence=TEXT("position-only stock TEXT root repair requires exact mapped registered unattached finite local/actor/world Q/Euler/scale/absolute proof");return false;}
  auto* RootPositionProperty=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),TEXT("RelativeLocation"));
  if(!RootPositionProperty||RootPositionProperty->Struct!=TBaseStructure<FVector>::Get()||RootPositionProperty->ArrayDim!=1)return false;
  constexpr int RootPositionFlags=PPF_DeepCompareInstances|PPF_ExportsNotFullyQualified|PPF_Copy|PPF_Delimited;
  FString RootPositionText;RootPositionProperty->ExportTextItem_Direct(RootPositionText,RootPositionProperty->ContainerPtrToValuePtr<void>(A),nullptr,A,RootPositionFlags);
  FVector ExpectedRootPosition=FVector::ZeroVector;FOutputDeviceNull RootPositionErrors;
  const TCHAR* RootPositionTail=RootPositionProperty->ImportText_Direct(*RootPositionText,&ExpectedRootPosition,B,RootPositionFlags,&RootPositionErrors);
  if(RootPositionTail)while(*RootPositionTail&&FChar::IsWhitespace(*RootPositionTail))++RootPositionTail;
  if(!RootPositionTail||*RootPositionTail||!ExactVectorBytes(ExpectedRootPosition,TL))
  {Evidence=TEXT("position-only root difference is NOT exact stock TEXT roundtrip: ")+RootPositionText;return false;}
  Proof=FString::Printf(TEXT("POSITION-only exact stock TEXT flags=%d export={%s} sourceP=(%.17g,%.17g,%.17g) targetBefore=(%.17g,%.17g,%.17g); exactQ/Euler/scale/absolute/local-actor-world guards; no ULP-budget extension"),RootPositionFlags,*RootPositionText,SL.X,SL.Y,SL.Z,TL.X,TL.Y,TL.Z);
 }
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
bool RestoreNewTargetChildPose(USceneComponent& Source,USceneComponent& Target,AActor* ExpectedSource,AActor* ExpectedTarget,
 UWorld* NewWorld,const TMap<UObject*,UObject*>& Remap,bool& Restored,FString& Evidence)
{
 Restored=false;Evidence.Reset();const FVector SourceLocation=Source.GetRelativeLocation(),TargetLocation=Target.GetRelativeLocation();
 const FRotator SR=Source.GetRelativeRotation(),TR=Target.GetRelativeRotation();
 const double A[]={SR.Pitch,SR.Yaw,SR.Roll},B[]={TR.Pitch,TR.Yaw,TR.Roll};
 const bool LocationDiff=!ExactVectorBytes(SourceLocation,TargetLocation),RotationDiff=FMemory::Memcmp(A,B,sizeof(A))!=0;
 FRotator Qualified;FString RotationProof;const bool QualifiedRotation=RotationDiff&&MeasuredRotation(Source,Target,Qualified,RotationProof);
 const bool RepairRotation=RotationDiff&&!QualifiedRotation;
 // Preserve the prior proven representation-only rule, but do not miss actual
 // rotation-only TEXT drift merely because the local position already matches.
 if(!LocationDiff&&!RepairRotation)return true;
 if(!ExpectedSource||!ExpectedTarget||!NewWorld||&Source==&Target||Source.GetOwner()!=ExpectedSource||Target.GetOwner()!=ExpectedTarget||
    Source.GetWorld()==NewWorld||Target.GetWorld()!=NewWorld||Source.GetClass()!=Target.GetClass()||
    Remap.FindRef(ExpectedSource)!=ExpectedTarget||Remap.FindRef(&Source)!=&Target||
    &Source==ExpectedSource->GetRootComponent()||&Target==ExpectedTarget->GetRootComponent()||!Source.IsRegistered()||!Target.IsRegistered()||
    SourceLocation.ContainsNaN()||TargetLocation.ContainsNaN()||SR.ContainsNaN()||TR.ContainsNaN())
 {Evidence=TEXT("child pose repair requires exact registered mapped NEW-world component/actor pair and finite pose");return false;}
 auto* SourceParent=Source.GetAttachParent();auto* TargetParent=Target.GetAttachParent();TSet<const USceneComponent*> Ancestors;
 for(auto* P=SourceParent,*Q=TargetParent;P||Q;)
 {if(!P||!Q||Ancestors.Contains(P)||P->GetOwner()!=ExpectedSource||Q->GetOwner()!=ExpectedTarget||P->GetClass()!=Q->GetClass()||
     !P->IsRegistered()||!Q->IsRegistered()||Remap.FindRef(P)!=Q||P->GetAttachSocketName()!=Q->GetAttachSocketName())
  {Evidence=TEXT("child pose repair requires complete exact mapped registered attachment hierarchy");return false;}
  Ancestors.Add(P);if((P==ExpectedSource->GetRootComponent())!=(Q==ExpectedTarget->GetRootComponent()))return false;
  P=P->GetAttachParent();Q=Q->GetAttachParent();}
 if(!SourceParent||!TargetParent||SourceParent->GetOwner()!=ExpectedSource||TargetParent->GetOwner()!=ExpectedTarget||
    Remap.FindRef(SourceParent)!=TargetParent||Source.GetAttachSocketName()!=Target.GetAttachSocketName()||
    !ExactTransformBytes(SourceParent->GetComponentTransform(),TargetParent->GetComponentTransform())||
    !ExactTransformBytes(SourceParent->GetSocketTransform(Source.GetAttachSocketName()),TargetParent->GetSocketTransform(Target.GetAttachSocketName()))||
    !ExactVectorBytes(Source.GetRelativeScale3D(),Target.GetRelativeScale3D())||
    Source.IsUsingAbsoluteLocation()!=Target.IsUsingAbsoluteLocation()||Source.IsUsingAbsoluteRotation()!=Target.IsUsingAbsoluteRotation()||Source.IsUsingAbsoluteScale()!=Target.IsUsingAbsoluteScale())
 {
  const FVector SS=Source.GetRelativeScale3D(),TS=Target.GetRelativeScale3D();
  Evidence=FString::Printf(TEXT("child pose guard DIFFERENCE parentPresent=%d ownerMatch=%d parentMap=%d socketSame=%d parentWorldExact=%d socketWorldExact=%d scaleExact=%d absoluteExact=%d sourceOwner=%s targetOwner=%s expectedOwners=%s/%s sourceParent=%s targetParent=%s sockets=%s/%s localScale17 source=(%.17g,%.17g,%.17g) target=(%.17g,%.17g,%.17g) absoluteSource=%d/%d/%d absoluteTarget=%d/%d/%d"),
   int32(SourceParent&&TargetParent),int32(SourceParent&&TargetParent&&SourceParent->GetOwner()==ExpectedSource&&TargetParent->GetOwner()==ExpectedTarget),
   int32(SourceParent&&TargetParent&&Remap.FindRef(SourceParent)==TargetParent),int32(Source.GetAttachSocketName()==Target.GetAttachSocketName()),
   int32(SourceParent&&TargetParent&&ExactTransformBytes(SourceParent->GetComponentTransform(),TargetParent->GetComponentTransform())),
   int32(SourceParent&&TargetParent&&ExactTransformBytes(SourceParent->GetSocketTransform(Source.GetAttachSocketName()),TargetParent->GetSocketTransform(Target.GetAttachSocketName()))),
   int32(ExactVectorBytes(SS,TS)),int32(Source.IsUsingAbsoluteLocation()==Target.IsUsingAbsoluteLocation()&&Source.IsUsingAbsoluteRotation()==Target.IsUsingAbsoluteRotation()&&Source.IsUsingAbsoluteScale()==Target.IsUsingAbsoluteScale()),
   *GetPathNameSafe(Source.GetOwner()),*GetPathNameSafe(Target.GetOwner()),*GetPathNameSafe(ExpectedSource),*GetPathNameSafe(ExpectedTarget),*GetPathNameSafe(SourceParent),*GetPathNameSafe(TargetParent),*Source.GetAttachSocketName().ToString(),*Target.GetAttachSocketName().ToString(),
   SS.X,SS.Y,SS.Z,TS.X,TS.Y,TS.Z,int32(Source.IsUsingAbsoluteLocation()),int32(Source.IsUsingAbsoluteRotation()),int32(Source.IsUsingAbsoluteScale()),int32(Target.IsUsingAbsoluteLocation()),int32(Target.IsUsingAbsoluteRotation()),int32(Target.IsUsingAbsoluteScale()));
  if(SourceParent&&TargetParent)
  {Evidence+=TEXT(" PARENT WORLD ")+TransformDifference(SourceParent->GetComponentTransform(),TargetParent->GetComponentTransform());
   Evidence+=TEXT(" SOCKET WORLD ")+TransformDifference(SourceParent->GetSocketTransform(Source.GetAttachSocketName()),TargetParent->GetSocketTransform(Target.GetAttachSocketName()));
   const FVector ParentSL=SourceParent->GetRelativeLocation(),ParentTL=TargetParent->GetRelativeLocation();
   const FRotator ParentSR=SourceParent->GetRelativeRotation(),ParentTR=TargetParent->GetRelativeRotation();
   const FVector ParentSS=SourceParent->GetRelativeScale3D(),ParentTS=TargetParent->GetRelativeScale3D();
   Evidence+=FString::Printf(TEXT(" MAPPED PARENT localP17=(%.17g,%.17g,%.17g)/(%.17g,%.17g,%.17g) localEuler17=(%.17g,%.17g,%.17g)/(%.17g,%.17g,%.17g) localScale17=(%.17g,%.17g,%.17g)/(%.17g,%.17g,%.17g) rootIdentity=%d/%d unattached=%d/%d registered=%d/%d localEqualsOwnActorP=%d/%d worldEqualsOwnActorTRS=%d/%d relativeEqualsOwnWorldTRS=%d/%d actorPairExact=%d"),
    ParentSL.X,ParentSL.Y,ParentSL.Z,ParentTL.X,ParentTL.Y,ParentTL.Z,ParentSR.Pitch,ParentSR.Yaw,ParentSR.Roll,ParentTR.Pitch,ParentTR.Yaw,ParentTR.Roll,ParentSS.X,ParentSS.Y,ParentSS.Z,ParentTS.X,ParentTS.Y,ParentTS.Z,
    int32(SourceParent==ExpectedSource->GetRootComponent()),int32(TargetParent==ExpectedTarget->GetRootComponent()),int32(!SourceParent->GetAttachParent()),int32(!TargetParent->GetAttachParent()),int32(SourceParent->IsRegistered()),int32(TargetParent->IsRegistered()),
    int32(ExactVectorBytes(ParentSL,ExpectedSource->GetActorLocation())),int32(ExactVectorBytes(ParentTL,ExpectedTarget->GetActorLocation())),
    int32(ExactTransformBytes(SourceParent->GetComponentTransform(),ExpectedSource->GetActorTransform())),int32(ExactTransformBytes(TargetParent->GetComponentTransform(),ExpectedTarget->GetActorTransform())),
    int32(ExactTransformBytes(SourceParent->GetRelativeTransform(),SourceParent->GetComponentTransform())),int32(ExactTransformBytes(TargetParent->GetRelativeTransform(),TargetParent->GetComponentTransform())),
    int32(ExactTransformBytes(ExpectedSource->GetActorTransform(),ExpectedTarget->GetActorTransform())));
   constexpr int ParentFlags=PPF_DeepCompareInstances|PPF_ExportsNotFullyQualified|PPF_Copy|PPF_Delimited;
   for(const TCHAR* ParentName:{TEXT("RelativeLocation"),TEXT("RelativeRotation"),TEXT("RelativeScale3D")})
   {
    auto* ParentProperty=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),ParentName);
    if(!ParentProperty||ParentProperty->ArrayDim!=1)continue;
    FString ParentText,ParentTargetText;ParentProperty->ExportTextItem_Direct(ParentText,ParentProperty->ContainerPtrToValuePtr<void>(SourceParent),nullptr,SourceParent,ParentFlags);
    ParentProperty->ExportTextItem_Direct(ParentTargetText,ParentProperty->ContainerPtrToValuePtr<void>(TargetParent),nullptr,TargetParent,ParentFlags);FOutputDeviceNull ParentErrors;
    if(ParentProperty->Struct==TBaseStructure<FRotator>::Get())
    {
     FRotator ParentExpected=FRotator::ZeroRotator;const TCHAR* ParentTail=ParentProperty->ImportText_Direct(*ParentText,&ParentExpected,TargetParent,ParentFlags,&ParentErrors);
     if(ParentTail)while(*ParentTail&&FChar::IsWhitespace(*ParentTail))++ParentTail;
     const double ParentParsed[]={ParentExpected.Pitch,ParentExpected.Yaw,ParentExpected.Roll},ParentActual[]={ParentTR.Pitch,ParentTR.Yaw,ParentTR.Roll};
     Evidence+=FString::Printf(TEXT(" parentStock%s source={%s} target={%s} parseComplete=%d matchesActualTarget=%d expected17=(%.17g,%.17g,%.17g) flags=%d"),ParentName,*ParentText,*ParentTargetText,int32(ParentTail&&!*ParentTail),int32(ParentTail&&!*ParentTail&&!FMemory::Memcmp(ParentParsed,ParentActual,sizeof(ParentParsed))),ParentExpected.Pitch,ParentExpected.Yaw,ParentExpected.Roll,ParentFlags);
    }
    else if(ParentProperty->Struct==TBaseStructure<FVector>::Get())
    {
     FVector ParentExpected=FVector::ZeroVector;const TCHAR* ParentTail=ParentProperty->ImportText_Direct(*ParentText,&ParentExpected,TargetParent,ParentFlags,&ParentErrors);
     if(ParentTail)while(*ParentTail&&FChar::IsWhitespace(*ParentTail))++ParentTail;
     const FVector ParentActual=FString(ParentName)==TEXT("RelativeLocation")?ParentTL:ParentTS;
     Evidence+=FString::Printf(TEXT(" parentStock%s source={%s} target={%s} parseComplete=%d matchesActualTarget=%d expected17=(%.17g,%.17g,%.17g) flags=%d"),ParentName,*ParentText,*ParentTargetText,int32(ParentTail&&!*ParentTail),int32(ParentTail&&!*ParentTail&&ExactVectorBytes(ParentExpected,ParentActual)),ParentExpected.X,ParentExpected.Y,ParentExpected.Z,ParentFlags);
    }
   }
  }
  Evidence+=FString::Printf(TEXT(" CHILD localPosition17=(%.17g,%.17g,%.17g)/(%.17g,%.17g,%.17g) localEuler17=(%.17g,%.17g,%.17g)/(%.17g,%.17g,%.17g) CHILD WORLD "),SourceLocation.X,SourceLocation.Y,SourceLocation.Z,TargetLocation.X,TargetLocation.Y,TargetLocation.Z,SR.Pitch,SR.Yaw,SR.Roll,TR.Pitch,TR.Yaw,TR.Roll)+TransformDifference(Source.GetComponentTransform(),Target.GetComponentTransform());
  constexpr int Flags=PPF_DeepCompareInstances|PPF_ExportsNotFullyQualified|PPF_Copy|PPF_Delimited;
  for(const TCHAR* Name:{TEXT("RelativeLocation"),TEXT("RelativeRotation"),TEXT("RelativeScale3D")})
  {auto* P=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),Name);if(!P)continue;FString Text,TargetText;
   P->ExportTextItem_Direct(Text,P->ContainerPtrToValuePtr<void>(&Source),nullptr,&Source,Flags);P->ExportTextItem_Direct(TargetText,P->ContainerPtrToValuePtr<void>(&Target),nullptr,&Target,Flags);
   FOutputDeviceNull Errors;
   if(P->Struct==TBaseStructure<FRotator>::Get())
   {FRotator Expected=FRotator::ZeroRotator;const TCHAR* Tail=P->ImportText_Direct(*Text,&Expected,&Target,Flags,&Errors);
    Evidence+=FString::Printf(TEXT(" stock%s source={%s} target={%s} parsed=%d expected17=(%.17g,%.17g,%.17g) flags=%d"),Name,*Text,*TargetText,int32(Tail!=nullptr),Expected.Pitch,Expected.Yaw,Expected.Roll,Flags);}
   else if(P->Struct==TBaseStructure<FVector>::Get())
   {FVector Expected=FVector::ZeroVector;const TCHAR* Tail=P->ImportText_Direct(*Text,&Expected,&Target,Flags,&Errors);
    Evidence+=FString::Printf(TEXT(" stock%s source={%s} target={%s} parsed=%d expected17=(%.17g,%.17g,%.17g) flags=%d"),Name,*Text,*TargetText,int32(Tail!=nullptr),Expected.X,Expected.Y,Expected.Z,Flags);}}
  return false;
 }
 // Exact stock CopyActors -> LevelExporterT3D COPY -> ExportProperties flags:
 // EditorActor.cpp423, EditorExporters.cpp637, UnrealExporter.cpp1142.
 constexpr int Flags=PPF_DeepCompareInstances|PPF_ExportsNotFullyQualified|PPF_Copy|PPF_Delimited;
 FString LocationText,RotationText;FOutputDeviceNull Errors;
 if(LocationDiff)
 {
  auto* Property=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),TEXT("RelativeLocation"));
  if(!Property||Property->Struct!=TBaseStructure<FVector>::Get()||Property->ArrayDim!=1)return false;
  Property->ExportTextItem_Direct(LocationText,Property->ContainerPtrToValuePtr<void>(&Source),nullptr,&Source,Flags);
  FVector Expected=FVector::ZeroVector;const TCHAR* Tail=Property->ImportText_Direct(*LocationText,&Expected,&Target,Flags,&Errors);
  if(Tail)while(*Tail&&FChar::IsWhitespace(*Tail))++Tail;
  if(!Tail||*Tail||!ExactVectorBytes(Expected,TargetLocation))
  {Evidence=TEXT("child local difference is NOT exact stock TEXT roundtrip: ")+LocationText;return false;}
 }
 const FQuat DirectSource=SR.Quaternion(),CachedSource=Source.GetRelativeRotationCache().RotatorToQuat_ReadOnly(SR);
 if(RepairRotation)
 {
  auto* Property=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),TEXT("RelativeRotation"));
  if(!Property||Property->Struct!=TBaseStructure<FRotator>::Get()||Property->ArrayDim!=1)return false;
  Property->ExportTextItem_Direct(RotationText,Property->ContainerPtrToValuePtr<void>(&Source),nullptr,&Source,Flags);
  FRotator Expected=FRotator::ZeroRotator;const TCHAR* Tail=Property->ImportText_Direct(*RotationText,&Expected,&Target,Flags,&Errors);
  if(Tail)while(*Tail&&FChar::IsWhitespace(*Tail))++Tail;
  const double E[]={Expected.Pitch,Expected.Yaw,Expected.Roll};
  if(!Tail||*Tail||FMemory::Memcmp(E,B,sizeof(E)))
  {Evidence=TEXT("child rotation difference is NOT exact stock TEXT roundtrip: ")+RotationText+TEXT(" WORLD ")+TransformDifference(Source.GetComponentTransform(),Target.GetComponentTransform());return false;}
 }
 // Preserve the actual source direct/cache quaternion measurements. Neither is
 // substituted for the source world pose: the exact world postcondition wins.
 const FString QuaternionProof=FString::Printf(TEXT(" sourceDirectQ=(%.17g,%.17g,%.17g,%.17g) sourceReadonlyCachedQ=(%.17g,%.17g,%.17g,%.17g) directCacheBitEqual=%d"),DirectSource.X,DirectSource.Y,DirectSource.Z,DirectSource.W,CachedSource.X,CachedSource.Y,CachedSource.Z,CachedSource.W,int32(ExactQuaternion(DirectSource,CachedSource)));
 if(RepairRotation)Target.SetRelativeRotation_Direct(SR);
 if(LocationDiff)Target.SetRelativeLocation_Direct(SourceLocation);
 Target.UpdateComponentToWorld(EUpdateTransformFlags::None,ETeleportType::TeleportPhysics);
 const FRotator After=Target.GetRelativeRotation();const double R[]={After.Pitch,After.Yaw,After.Roll};
 if(!ExactVectorBytes(SourceLocation,Target.GetRelativeLocation())||(RepairRotation&&FMemory::Memcmp(A,R,sizeof(A)))||!ExactTransformBytes(Source.GetComponentTransform(),Target.GetComponentTransform()))
 {Evidence=TEXT("child pose exact source local/world postcondition failed")+QuaternionProof+TEXT(" WORLD ")+TransformDifference(Source.GetComponentTransform(),Target.GetComponentTransform());return false;}
 Restored=true;Evidence=FString::Printf(TEXT("RESTORED NEW TARGET child sourceRelative=(%.17g,%.17g,%.17g) TEXTtarget=(%.17g,%.17g,%.17g) sourceEuler=(%.17g,%.17g,%.17g) targetEulerBefore=(%.17g,%.17g,%.17g) repairedRotation=%d exactStockFlags=%d locationExport={%s} rotationExport={%s}; exactworld/localpostcondition; source untouched"),SourceLocation.X,SourceLocation.Y,SourceLocation.Z,TargetLocation.X,TargetLocation.Y,TargetLocation.Z,SR.Pitch,SR.Yaw,SR.Roll,TR.Pitch,TR.Yaw,TR.Roll,int32(RepairRotation),Flags,*LocationText,*RotationText)+QuaternionProof;return true;
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
bool State(UObject& O,const TMap<const UObject*,FString>& IDs,const TSet<const UPackage*>& Forbidden,bool Target,TArray<uint8>& Out,FRotator* ComparisonRotation,FTransform* ActorComparisonTransform,FTransform* RootComparisonTransform,FTransform* ChildComparisonTransform,FKAggregateGeom* AggregateComparison);
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
   if(const auto* BoxProperty=CastField<FStructProperty>(P);BoxProperty&&P->GetOwnerClass()==UBoxComponent::StaticClass()&&P->GetFName()==TEXT("BoxExtent")&&BoxProperty->Struct==TBaseStructure<FVector>::Get()&&P->ArrayDim==1&&StaticIndex==0)
   {
    auto* SourceBox=Cast<UBoxComponent>(&Source);auto* TargetBox=Cast<UBoxComponent>(&Target);
    if(SourceBox&&TargetBox)
    {
     const FVector SourceExtent=*BoxProperty->ContainerPtrToValuePtr<FVector>(&Source),TargetExtent=*BoxProperty->ContainerPtrToValuePtr<FVector>(&Target);
     constexpr int BoxFlags=PPF_DeepCompareInstances|PPF_ExportsNotFullyQualified|PPF_Copy|PPF_Delimited;
     FString BoxText;BoxProperty->ExportTextItem_Direct(BoxText,BoxProperty->ContainerPtrToValuePtr<void>(&Source),nullptr,&Source,BoxFlags);
     FVector ExpectedExtent=FVector::ZeroVector;FOutputDeviceNull BoxErrors;
     const TCHAR* BoxTail=BoxProperty->ImportText_Direct(*BoxText,&ExpectedExtent,&Target,BoxFlags,&BoxErrors);
     if(BoxTail)while(*BoxTail&&FChar::IsWhitespace(*BoxTail))++BoxTail;
     Numeric+=FString::Printf(TEXT(" BOX_EXTENT_STOCK_TEXT source17=(%.17g,%.17g,%.17g) target17=(%.17g,%.17g,%.17g) export={%s} flags=%d parseComplete=%d exactActualTarget=%d expected17=(%.17g,%.17g,%.17g) classSame=%d source=%s target=%s sourceOwner=%s targetOwner=%s sourceWorld=%s targetWorld=%s registered=%d/%d exactWorldTRS=%d exactRelativeTRS=%d"),SourceExtent.X,SourceExtent.Y,SourceExtent.Z,TargetExtent.X,TargetExtent.Y,TargetExtent.Z,*BoxText,BoxFlags,int32(BoxTail&&!*BoxTail),int32(BoxTail&&!*BoxTail&&ExactVectorBytes(ExpectedExtent,TargetExtent)),ExpectedExtent.X,ExpectedExtent.Y,ExpectedExtent.Z,int32(SourceBox->GetClass()==TargetBox->GetClass()),*SourceBox->GetPathName(),*TargetBox->GetPathName(),*GetPathNameSafe(SourceBox->GetOwner()),*GetPathNameSafe(TargetBox->GetOwner()),*GetPathNameSafe(SourceBox->GetWorld()),*GetPathNameSafe(TargetBox->GetWorld()),int32(SourceBox->IsRegistered()),int32(TargetBox->IsRegistered()),int32(ExactTransformBytes(SourceBox->GetComponentTransform(),TargetBox->GetComponentTransform())),int32(ExactTransformBytes(SourceBox->GetRelativeTransform(),TargetBox->GetRelativeTransform())));
     auto BoxDetails=[&](const TCHAR* Side,UBoxComponent& Box)
     {
      FString Responses;for(int I=0;I<64;++I)Responses+=FString::FromInt(int32(Box.GetCollisionResponseToChannels().GetResponse(static_cast<ECollisionChannel>(I))));
      Numeric+=FString::Printf(TEXT(" %sPolicy profile=%s enabled=%d objectType=%d responses64=%s nav=%d overlap=%d shadow=%d hiddenShadow=%d physicsCreated=%d"),Side,*Box.GetCollisionProfileName().ToString(),int32(Box.GetCollisionEnabled()),int32(Box.GetCollisionObjectType()),*Responses,int32(Box.CanEverAffectNavigation()),int32(Box.GetGenerateOverlapEvents()),int32(Box.CastShadow),int32(Box.bCastHiddenShadow),int32(Box.IsPhysicsStateCreated()));
      const FBoxSphereBounds CachedBounds=Box.Bounds,CalculatedBounds=Box.CalcBounds(Box.GetComponentTransform());
      Numeric+=FString::Printf(TEXT(" %sBounds cachedOrigin17=(%.17g,%.17g,%.17g) extent17=(%.17g,%.17g,%.17g) radius17=%.17g calcOrigin17=(%.17g,%.17g,%.17g) extent17=(%.17g,%.17g,%.17g) radius17=%.17g"),Side,CachedBounds.Origin.X,CachedBounds.Origin.Y,CachedBounds.Origin.Z,CachedBounds.BoxExtent.X,CachedBounds.BoxExtent.Y,CachedBounds.BoxExtent.Z,double(CachedBounds.SphereRadius),CalculatedBounds.Origin.X,CalculatedBounds.Origin.Y,CalculatedBounds.Origin.Z,CalculatedBounds.BoxExtent.X,CalculatedBounds.BoxExtent.Y,CalculatedBounds.BoxExtent.Z,double(CalculatedBounds.SphereRadius));
      // Read the existing pointer through reflection; GetBodySetup could create one.
      const auto* BodyProperty=FindFProperty<FObjectPropertyBase>(UShapeComponent::StaticClass(),TEXT("ShapeBodySetup"));
      auto* Body=BodyProperty?Cast<UBodySetup>(BodyProperty->GetObjectPropertyValue_InContainer(&Box)):nullptr;
      Numeric+=FString::Printf(TEXT(" %sExistingBodySetup=%s pointerPropertyPresent=%d"),Side,*GetPathNameSafe(Body),int32(BodyProperty!=nullptr));
      if(Body)
      {
       TArray<uint8> BodyBytes;const bool BodyStateOK=State(*Body,IDs,Forbidden,false,BodyBytes,nullptr,nullptr,nullptr,nullptr,nullptr);uint8 Digest[FSHA1::DigestSize];FSHA1::HashBuffer(BodyBytes.GetData(),BodyBytes.Num(),Digest);
       Numeric+=FString::Printf(TEXT(" %sBody guid=%s trace=%d boxes=%d spheres=%d capsules=%d convex=%d stateOK=%d canonicalBytes=%d canonicalSHA1=%s"),Side,*Body->BodySetupGuid.ToString(),int32(Body->CollisionTraceFlag),Body->AggGeom.BoxElems.Num(),Body->AggGeom.SphereElems.Num(),Body->AggGeom.SphylElems.Num(),Body->AggGeom.ConvexElems.Num(),int32(BodyStateOK),BodyBytes.Num(),*BytesToHex(Digest,FSHA1::DigestSize));
      }
     };
     BoxDetails(TEXT("SOURCE"),*SourceBox);BoxDetails(TEXT("TARGET"),*TargetBox);
    }
   }
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
// This contract defers ONLY PostLoad. Audited native PreDuplicate,
// PostDuplicate and native UClass PostInitInstance still run inside duplication.
struct FBinaryControlLifetime
{
 TArray<TStrongObjectPtr<UObject>> Targets;
 TArray<TStrongObjectPtr<UObject>> SourceWorlds;
 TArray<ULevel*> SourceLevels;
 TArray<AActor*> SourceActors;
 TArray<uint8> SourceTopology;
};
bool CaptureBinarySourceTopology(const FBinaryControlLifetime& Lifetime,TArray<uint8>& Bytes)
{
 FObjectWriter W(Bytes);auto Pointer=[&](const void* P){UPTRINT V=reinterpret_cast<UPTRINT>(P);W.Serialize(&V,sizeof(V));};
 for(ULevel* Level:Lifetime.SourceLevels)
 {if(!IsValid(Level))return false;Pointer(Level);int32 N=Level->Actors.Num();W<<N;for(const auto& Actor:Level->Actors)Pointer(Actor.Get());}
 const TMap<const UObject*,FString> NoIDs;const TSet<const UPackage*> NoForbidden;
 for(AActor* Actor:Lifetime.SourceActors)
 {
  if(!IsValid(Actor))return false;Pointer(Actor);Pointer(Actor->GetOwner());Pointer(Actor->GetRootComponent());int32 N=Actor->Children.Num();W<<N;for(const auto& Child:Actor->Children)Pointer(Child.Get());
  TArray<UObject*> Objects;Objects.Add(Actor);ForEachObjectWithOuter(Actor,[&](UObject* O){Objects.Add(O);},EGetObjectsFlags::IncludeNestedObjects);
  Objects.Sort([](const UObject& A,const UObject& B){return A.GetPathName()<B.GetPathName();});
  for(UObject* Object:Objects)
  {
   Pointer(Object);Pointer(Object->GetOuter());
   if(auto* C=Cast<USceneComponent>(Object))
   {Pointer(C->GetOwner());Pointer(C->GetAttachParent());FName Socket=C->GetAttachSocketName();W<<Socket;FTransform Local=C->GetRelativeTransform(),World=C->GetComponentTransform();W<<Local<<World;int32 Count=C->GetAttachChildren().Num();W<<Count;for(const auto& Child:C->GetAttachChildren())Pointer(Child.Get());}
   if(auto* C=Cast<UPrimitiveComponent>(Object))
   {int32 Enabled=int32(C->GetCollisionEnabled()),Type=int32(C->GetCollisionObjectType());FName Profile=C->GetCollisionProfileName();bool Physics=C->IsPhysicsStateCreated();W<<Enabled<<Type<<Profile<<Physics;const FBodyInstance& ExistingInstance=C->BodyInstance;Pointer(ExistingInstance.GetPhysicsActorHandle());for(int I=0;I<64;++I){int32 Response=int32(C->GetCollisionResponseToChannels().GetResponse(static_cast<ECollisionChannel>(I)));W<<Response;}
    const auto* ShapeBody=FindFProperty<FObjectPropertyBase>(UShapeComponent::StaticClass(),TEXT("ShapeBodySetup"));
    auto* ExistingBody=C->IsA<UShapeComponent>()&&ShapeBody?Cast<UBodySetup>(ShapeBody->GetObjectPropertyValue_InContainer(C)):nullptr;Pointer(ExistingBody);
    if(ExistingBody){FGuid Guid=ExistingBody->BodySetupGuid;W<<Guid;TArray<uint8> BodyBytes;if(!State(*ExistingBody,NoIDs,NoForbidden,false,BodyBytes))return false;W<<BodyBytes;}}
   if(auto* Body=Cast<UBodySetup>(Object))
   {FGuid Guid=Body->BodySetupGuid;W<<Guid;TArray<uint8> BodyBytes;if(!State(*Body,NoIDs,NoForbidden,false,BodyBytes))return false;W<<BodyBytes;}
  }
 }
 return !W.IsError();
}
bool VerifyBinarySourceTopology(const FBinaryControlLifetime& Lifetime,FString& Error)
{
 TArray<uint8> Now;if(!CaptureBinarySourceTopology(Lifetime,Now)||Now!=Lifetime.SourceTopology)
 {Error=TEXT("binary copy callback changed source owner/Children/level/attachment/body topology");return false;}return true;
}
void CaptureBinaryImmediateActors(AActor& Actor,FBinaryControlLifetime& Immediate)
{
 Immediate.SourceActors.Add(&Actor);auto Add=[&](AActor* A){if(A&&!Immediate.SourceActors.Contains(A))Immediate.SourceActors.Add(A);};
 Add(Actor.GetOwner());for(const auto& Child:Actor.Children)Add(Child.Get());
 TInlineComponentArray<USceneComponent*> Components(&Actor);
 for(auto* C:Components){if(C->GetAttachParent())Add(C->GetAttachParent()->GetOwner());for(const auto& Child:C->GetAttachChildren())if(Child)Add(Child->GetOwner());}
 Immediate.SourceActors.Sort([](const AActor& A,const AActor& B){return A.GetPathName()<B.GetPathName();});
}
bool AuditedBinaryObject(UObject& Object,const TSet<const UPackage*>& SourcePackages,FString& Error)
{
 static const TSet<FString> Classes={
  TEXT("/Script/Engine.Actor"),TEXT("/Script/Engine.PlayerStart"),TEXT("/Script/Engine.DirectionalLight"),TEXT("/Script/Engine.SkyLight"),TEXT("/Script/Engine.ExponentialHeightFog"),
  TEXT("/Script/DinkCore.DinkGreyboxScreen"),TEXT("/Script/DinkCore.DinkScreenVolume"),TEXT("/Script/DinkCore.DinkPlaceholderActor"),TEXT("/Script/DinkCore.DinkWarpPlaceholderActor"),TEXT("/Script/DinkCore.DinkScriptWarpActor"),
  TEXT("/Script/Engine.SceneComponent"),TEXT("/Script/Engine.StaticMeshComponent"),TEXT("/Script/Engine.InstancedStaticMeshComponent"),TEXT("/Script/Engine.BoxComponent"),TEXT("/Script/Engine.CapsuleComponent"),TEXT("/Script/Engine.ArrowComponent"),TEXT("/Script/Engine.BillboardComponent"),
  TEXT("/Script/Engine.DirectionalLightComponent"),TEXT("/Script/Engine.SkyLightComponent"),TEXT("/Script/Engine.SkyAtmosphereComponent"),TEXT("/Script/Engine.ExponentialHeightFogComponent"),TEXT("/Script/Engine.BodySetup"),
  TEXT("/Script/DinkCore.DinkOriginComponent"),TEXT("/Script/DinkCore.DinkInstanceOriginsComponent"),TEXT("/Script/DinkCore.DinkWarpComponent")};
 if(!Classes.Contains(Object.GetClass()->GetPathName())||Object.GetClass()->GetClass()!=UClass::StaticClass())
 {Error=TEXT("unreviewed binary native object callback/class: ")+Object.GetClass()->GetPathName();return false;}
 TSet<const UObject*> Seen;for(const UObject* A=Object.GetArchetype();A;A=A->GetArchetype())
 {if(Seen.Contains(A)){Error=TEXT("source archetype chain cyclic");return false;}Seen.Add(A);if(SourcePackages.Contains(A->GetOutermost())){Error=TEXT("source-instance archetype rejected BEFORE binary construction");return false;}if(A->HasAnyFlags(RF_ClassDefaultObject))break;}
 if(Object.IsA<UStaticMeshComponent>())
 {const auto* Paint=FindFProperty<FObjectPropertyBase>(UStaticMeshComponent::StaticClass(),TEXT("MeshPaintTexture"));if(!Paint||Paint->GetObjectPropertyValue_InContainer(&Object)){Error=TEXT("binary static mesh callback requires audited null mesh-paint texture");return false;}}
 return true;
}
// Binary loaded-actor transport: never clipboard/TEXT, never reparent sources.
bool BinaryCopyControls(const TArray<AActor*>& Controls,ULevel& NewLevel,TMap<UObject*,UObject*>& Remap,
 TMap<UObject*,UObject*>& Created,TArray<AActor*>& Copies,FBinaryControlLifetime& Lifetime,FString& Error)
{
 if(!NewLevel.GetWorld()){Error=TEXT("binary target level requires an owning world");return false;}
 Copies.Reset();Created.Reset();Lifetime.SourceLevels.Reset();Lifetime.SourceActors.Reset();Lifetime.SourceTopology.Reset();
 TSet<AActor*> PreflightActors;TSet<const UPackage*> SourcePackages;TSet<UWorld*> Worlds;
 for(AActor* Actor:Controls)
 {
  if(!Actor||!IsValid(Actor)||!Actor->GetWorld()||!Actor->GetLevel()||Actor->GetLevel()==&NewLevel||PreflightActors.Contains(Actor))
  {Error=TEXT("binary controls require nonnull unique source actors BEFORE sorting");return false;}
  PreflightActors.Add(Actor);if(!Worlds.Contains(Actor->GetWorld())){Worlds.Add(Actor->GetWorld());Lifetime.SourceWorlds.Emplace(Actor->GetWorld());}
 }
 for(UWorld* World:Worlds)for(ULevel* Level:World->GetLevels())
 {if(!Lifetime.SourceLevels.Contains(Level))Lifetime.SourceLevels.Add(Level);SourcePackages.Add(Level->GetOutermost());for(const auto& Actor:Level->Actors)if(Actor&&!Lifetime.SourceActors.Contains(Actor.Get()))Lifetime.SourceActors.Add(Actor.Get());}
 Lifetime.SourceLevels.Sort([](const ULevel& A,const ULevel& B){return A.GetPathName()<B.GetPathName();});Lifetime.SourceActors.Sort([](const AActor& A,const AActor& B){return A.GetPathName()<B.GetPathName();});
 for(AActor* Actor:Controls)
 {if(!AuditedBinaryObject(*Actor,SourcePackages,Error))return false;bool OK=true;ForEachObjectWithOuter(Actor,[&](UObject* O){if(OK&&!AuditedBinaryObject(*O,SourcePackages,Error))OK=false;},EGetObjectsFlags::IncludeNestedObjects);if(!OK)return false;}
 if(!CaptureBinarySourceTopology(Lifetime,Lifetime.SourceTopology)){Error=TEXT("cannot snapshot source topology before immediate callbacks");return false;}
 TArray<AActor*> Ordered=Controls;
 Ordered.Sort([](const AActor& A,const AActor& B){return A.GetPathName()<B.GetPathName();});
 TSet<AActor*> Unique;
 for(AActor* SourceActor:Ordered)
 {
  if(!SourceActor||SourceActor->GetLevel()==&NewLevel||Unique.Contains(SourceActor))
  {Error=TEXT("binary controls require unique actors from distinct source levels");return false;}
  Unique.Add(SourceActor);AActor* Copy=Cast<AActor>(Remap.FindRef(SourceActor));
  if(!Copy)
  {
   FObjectDuplicationParameters Parameters(SourceActor,&NewLevel);
   Parameters.DestName=MakeUniqueObjectName(&NewLevel,SourceActor->GetClass(),SourceActor->GetFName());
   Parameters.DestClass=SourceActor->GetClass();Parameters.DuplicateMode=EDuplicateMode::World;
   Parameters.bAssignExternalPackages=false;Parameters.bSkipPostLoad=true;
   Parameters.DuplicationSeed=Remap;TMap<UObject*,UObject*> CallCreated;Parameters.CreatedObjects=&CallCreated;
   FBinaryControlLifetime Immediate;CaptureBinaryImmediateActors(*SourceActor,Immediate);
   if(!CaptureBinarySourceTopology(Immediate,Immediate.SourceTopology)){Error=TEXT("cannot snapshot audited immediate-callback source peers");return false;}
   Copy=Cast<AActor>(StaticDuplicateObjectEx(Parameters));
   // GC-visible retention immediately after the supported API returns, before
   // another duplication or any deferred-load/registration callback can run.
   for(const auto& Pair:CallCreated)if(Pair.Value)Lifetime.Targets.Emplace(Pair.Value);
   if(!VerifyBinarySourceTopology(Immediate,Error))return false;
   if(!Copy||CallCreated.FindRef(SourceActor)!=Copy)
   {Error=TEXT("binary actor duplication did not report its actual root mapping");return false;}
   for(const auto& Pair:CallCreated)
   {
    if(!Pair.Key||!Pair.Value||Pair.Key==Pair.Value||Pair.Key->GetClass()!=Pair.Value->GetClass()||
       (Remap.Contains(Pair.Key)&&Remap.FindRef(Pair.Key)!=Pair.Value)||
       (Created.Contains(Pair.Key)&&Created.FindRef(Pair.Key)!=Pair.Value))
    {Error=TEXT("binary created-object map conflict or class/identity mismatch");return false;}
    Remap.Add(Pair.Key,Pair.Value);Created.Add(Pair.Key,Pair.Value);
   }
  }
  if(Copy==SourceActor||Copy->GetClass()!=SourceActor->GetClass()||Copy->GetOuter()!=&NewLevel||Copy->GetLevel()!=&NewLevel||Copies.Contains(Copy))
  {Error=TEXT("binary actor copy has wrong target level/class/identity");return false;}
  Copies.Add(Copy);
 }
 return Copies.Num()==Controls.Num()&&VerifyBinarySourceTopology(Lifetime,Error);
}
bool FinalizeBinaryControls(const TArray<AActor*>& Copies,ULevel& NewLevel,const TMap<UObject*,UObject*>& Remap,
 const TMap<UObject*,UObject*>& Created,const TMap<const UObject*,FString>& IDs,const TSet<const UPackage*>& SourcePackages,FBinaryControlLifetime& Lifetime,FString& Error)
{
 if(!VerifyBinarySourceTopology(Lifetime,Error))return false;
 TSet<UObject*> Retained;for(const auto& Strong:Lifetime.Targets)if(Strong.IsValid())Retained.Add(Strong.Get());
 TSet<UObject*> TargetObjects;
 for(const auto& Pair:Created)
 {
  UObject* Target=Pair.Value;
  if(!Pair.Key||!Target||Remap.FindRef(Pair.Key)!=Target||Pair.Key==Target||Pair.Key->GetClass()!=Target->GetClass()||
     !Target->IsIn(&NewLevel)||!Retained.Contains(Target)||SourcePackages.Contains(Target->GetOutermost()))
  {Error=TEXT("binary finalization requires complete distinct target object mappings");return false;}
  TargetObjects.Add(Target);
 }
 // Complete all actor/component/nested cross-references BEFORE any PostLoad.
 for(UObject* Target:TargetObjects)
 {FArchiveReplaceObjectRef<UObject> Fix(Target,Remap,EArchiveReplaceObjectFlags::IgnoreOuterRef|EArchiveReplaceObjectFlags::IgnoreArchetypeRef);}
 for(UObject* Target:TargetObjects)
 {
  TSet<const UObject*> Seen;
  for(const UObject* Archetype=Target->GetArchetype();Archetype;Archetype=Archetype->GetArchetype())
  {
   if(Seen.Contains(Archetype)){Error=TEXT("binary target archetype chain is cyclic");return false;}Seen.Add(Archetype);
   if(SourcePackages.Contains(Archetype->GetOutermost()))
   {Error=TEXT("binary target retained source-instance archetype: ")+Target->GetPathName();return false;}
   if(Archetype->HasAnyFlags(RF_ClassDefaultObject))break;
  }
  TArray<uint8> BeforeCallbacks;
  if(!State(*Target,IDs,SourcePackages,true,BeforeCallbacks))
  {Error=TEXT("binary target retained source-package reference before deferred PostLoad: ")+Target->GetPathName();return false;}
  if(auto* Component=Cast<UActorComponent>(Target);Component&&Component->IsRegistered())
  {Error=TEXT("binary target component registered before complete reference validation");return false;}
 }
 for(AActor* Copy:Copies)
  if(!Copy||Copy->GetLevel()!=&NewLevel||!TargetObjects.Contains(Copy))
  {Error=TEXT("binary finalization actor membership mismatch");return false;}
 // Same supported post-load routing as StaticDuplicateObjectEx, deferred until
 // Owner and every nested/cross-actor reference point at the complete copies.
 {
  TGuardValue<bool> RoutingPostLoad(FUObjectThreadContext::Get().IsRoutingPostLoad,true);
  for(UObject* Target:TargetObjects)if(!Target->IsTemplate())Target->ConditionalPostLoad();
 }
 if(!VerifyBinarySourceTopology(Lifetime,Error))return false;
 NewLevel.AddLoadedActors(Copies,nullptr);
 // New editor worlds may not yet have level-wide registration enabled.
 // This is the same public target-only registration used by the staging pass.
 for(AActor* Copy:Copies)if(IsValid(Copy))Copy->RegisterAllComponents();
 for(AActor* Copy:Copies)if(!IsValid(Copy)||Copy->GetLevel()!=&NewLevel||!NewLevel.Actors.Contains(Copy))
 {Error=TEXT("supported loaded-level registration lost a binary actor");return false;}
 if(!VerifyBinarySourceTopology(Lifetime,Error))return false;
 TSet<AActor*> CopiedSet(Copies);
 for(AActor* Copy:Copies)
 {
  if(NewLevel.Actors.FilterByPredicate([&](const auto& A){return A.Get()==Copy;}).Num()!=1){Error=TEXT("binary actor level membership is not unique");return false;}
  if(AActor* Owner=Copy->GetOwner();Owner&&Owner->Children.FilterByPredicate([&](const auto& A){return A.Get()==Copy;}).Num()!=1){Error=TEXT("binary copied owner Children membership is not exactly once");return false;}
  TSet<AActor*> Children;for(const auto& Child:Copy->Children)
  {if(!Child||!CopiedSet.Contains(Child.Get())||Child->GetOwner()!=Copy||Children.Contains(Child.Get())){Error=TEXT("binary copied Children contains missing/duplicate/source actor");return false;}Children.Add(Child.Get());}
 }
 return true;
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
 FBinaryControlLifetime BinaryLifetime;
 TStrongObjectPtr<UWorld> World(UWorld::CreateWorld(EWorldType::Editor,false,FName(*FPackageName::GetShortName(TargetWorldPackage)),Package,false));
 if(!World.IsValid())return Fail(TEXT("candidate world creation failed"));
 ON_SCOPE_EXIT{World->DestroyWorld(false);World->MarkObjectsPendingKill();};
 World->SetFlags(RF_Public|RF_Standalone);
 auto* NewSettings=World->GetWorldSettings();
 for(TFieldIterator<FProperty> It(Settings->GetClass());It;++It)
  if(It->GetOwnerClass()==AWorldSettings::StaticClass()&&!It->HasAnyPropertyFlags(CPF_Transient|CPF_DuplicateTransient|CPF_NonPIEDuplicateTransient|CPF_SkipSerialization))
   It->CopyCompleteValue(It->ContainerPtrToValuePtr<void>(NewSettings),It->ContainerPtrToValuePtr<void>(Settings));
 TMap<UObject*,UObject*> Remap;Remap.Add(SourceWorld,World.Get());Remap.Add(const_cast<AWorldSettings*>(Settings),NewSettings);
 for(const auto* L:SourceWorld->GetLevels())Remap.Add(const_cast<ULevel*>(L),World->PersistentLevel);
 TArray<AActor*> Copies;TMap<UObject*,UObject*> BinaryCreated;FString BinaryError;
 if(!BinaryCopyControls(Controls,*World->PersistentLevel,Remap,BinaryCreated,Copies,BinaryLifetime,BinaryError))return Fail(BinaryError);
 TMap<FString,AActor*> Targets;for(AActor* A:Copies){const FString K=Key(*A);if(!Sources.Contains(K)||Targets.Contains(K))return Fail(TEXT("copied control identity missing/duplicate"));if(A->GetWorld()!=World.Get()||SourcePackages.Contains(A->GetArchetype()->GetOutermost()))return Fail(TEXT("copied actor retained source world/archetype"));Targets.Add(K,A);A->SetActorLabel(Sources[K]->GetActorLabel(),false);}
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
   UObject** New=Objects.Find(O.Key);if(!New||(*New)->GetClass()!=O.Value->GetClass()||(Remap.Contains(O.Value)&&Remap.FindRef(O.Value)!=*New))return Fail(TEXT("source descendant missing/conflicting binary mapping"));Remap.Add(O.Value,*New);
  }
 }
 for(const auto& P:Remap)if(const FString* Identity=IDs.Find(P.Key))IDs.Add(P.Value,*Identity);
 {FArchiveReplaceObjectRef<UObject> FixSettingsBeforeCallbacks(NewSettings,Remap,EArchiveReplaceObjectFlags::IgnoreOuterRef|EArchiveReplaceObjectFlags::IgnoreArchetypeRef);}
 if(!FinalizeBinaryControls(Copies,*World->PersistentLevel,Remap,BinaryCreated,IDs,SourcePackages,BinaryLifetime,BinaryError))return Fail(BinaryError);
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
  bool Restored=false;FString Repair;if(!RestoreNewTargetChildPose(*Src,*Dst,Owner,NewOwner,World.Get(),Remap,Restored,Repair))return Fail(Src->GetPathName()+TEXT(" ")+Repair);
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
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkBinaryControlCopyRegression,
 "Dink.Import.Foundation.BinaryControlCopy",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FDinkBinaryControlCopyRegression::RunTest(const FString&)
{
 const FString Token=FGuid::NewGuid().ToString(EGuidFormats::Digits);
 UPackage* SourcePackage=CreatePackage(*(TEXT("/Temp/DinkBinarySource_")+Token));
 UPackage* TargetPackage=CreatePackage(*(TEXT("/Temp/DinkBinaryTarget_")+Token));
 UWorld* SourceWorld=UWorld::CreateWorld(EWorldType::Editor,false,FName(TEXT("BinarySource")),SourcePackage,false);
 UWorld* TargetWorld=UWorld::CreateWorld(EWorldType::Editor,false,FName(TEXT("BinaryTarget")),TargetPackage,false);
 if(!TestNotNull(TEXT("binary source scratchworld"),SourceWorld)||!TestNotNull(TEXT("binary target scratchworld"),TargetWorld))return false;
 FBinaryControlLifetime Lifetime,BadLifetime;
 TStrongObjectPtr<UWorld> HoldSourceWorld(SourceWorld),HoldTargetWorld(TargetWorld);
 ON_SCOPE_EXIT{TargetWorld->DestroyWorld(false);TargetWorld->MarkObjectsPendingKill();SourceWorld->DestroyWorld(false);SourceWorld->MarkObjectsPendingKill();};
 ULevel* ExtraLevel=NewObject<ULevel>(SourceWorld,TEXT("BinaryExtraLevel"));ExtraLevel->OwningWorld=SourceWorld;SourceWorld->AddLevel(ExtraLevel);
 FActorSpawnParameters FirstParams;FirstParams.Name=TEXT("BinarySameName");FirstParams.OverrideLevel=SourceWorld->PersistentLevel;
 FActorSpawnParameters SecondParams;SecondParams.Name=TEXT("BinarySameName");SecondParams.OverrideLevel=ExtraLevel;
 auto* First=SourceWorld->SpawnActor<ADinkPlaceholderActor>(FirstParams);auto* Second=SourceWorld->SpawnActor<ADinkPlaceholderActor>(SecondParams);
 if(!TestNotNull(TEXT("binary native/defaultsubobject actor first"),First)||!TestNotNull(TEXT("binary same-name other-level actor second"),Second))return false;
 TestEqual(TEXT("source names deliberately collide across levels"),First->GetFName(),Second->GetFName());First->SetOwner(Second);
 First->Tags.Add(TEXT("DinkKey=S031_P03"));FDinkOriginId::Parse(TEXT("S031_P03"),First->Origin->OriginId);First->Origin->ScriptName=TEXT("bar-f1");First->Origin->SourceHash=TEXT("binary-copy-fixture-source");
 auto* Light=SourceWorld->SpawnActor<ADirectionalLight>();if(!TestNotNull(TEXT("actual native directional light for World-mode GUID fidelity"),Light))return false;
 auto* LightComponent=Cast<ULightComponentBase>(Light->GetLightComponent());if(!TestNotNull(TEXT("actual light component"),LightComponent))return false;
 auto GuidValue=[](ULightComponentBase& C,const TCHAR* Name){const auto* Property=FindFProperty<FStructProperty>(ULightComponentBase::StaticClass(),Name);check(Property&&Property->Struct==TBaseStructure<FGuid>::Get());return *Property->ContainerPtrToValuePtr<FGuid>(&C);};
 const FGuid LightGuidBefore=GuidValue(*LightComponent,TEXT("LightGuid")),OriginalLightGuidBefore=GuidValue(*LightComponent,TEXT("OriginalLightGuid"));
 const TArray<TObjectPtr<AActor>> FirstChildrenBefore=First->Children,SecondChildrenBefore=Second->Children;const FGuid FirstActorGuidBefore=First->GetActorGuid(),SecondActorGuidBefore=Second->GetActorGuid();
 auto* Warp=NewObject<UDinkWarpComponent>(First,TEXT("BinaryWarp"));First->AddInstanceComponent(Warp);Warp->SetupAttachment(First->GetRootComponent());
 Warp->WarpId=TEXT("S254_P04");Warp->SourceScreen=254;Warp->DestScreen=418;Warp->DestLocation=FVector(-184172.03999999998,55656.424999999988,0);Warp->DestMapPixel=FVector2D(303.00000000000006,389.99999999999994);
 Warp->SetBoxExtent(FVector(180,145.00000000000341,150),false);Warp->SetCollisionProfileName(TEXT("BlockAll"));Warp->RegisterComponent();
 auto* Nested=NewObject<USceneComponent>(First->GetRootComponent(),TEXT("BinaryNested"));First->AddInstanceComponent(Nested);Nested->SetupAttachment(Second->GetRootComponent());Nested->SetRelativeLocation(FVector(205.62000000002445,7929.4799999999996,-0.));Nested->RegisterComponent();
 auto* Instances=NewObject<UInstancedStaticMeshComponent>(First,TEXT("BinaryInstances"));First->AddInstanceComponent(Instances);Instances->SetupAttachment(First->GetRootComponent());Instances->SetCollisionEnabled(ECollisionEnabled::NoCollision);
 auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));if(!TestNotNull(TEXT("actual cube for raw instance binary proof"),Cube))return false;Instances->SetStaticMesh(Cube);First->Card->SetStaticMesh(Cube);First->Card->SetMaterial(0,Cube->GetMaterial(0));Instances->AddInstance(FTransform::Identity,false);Instances->RegisterComponent();
 TArray<FInstancedStaticMeshInstanceData> SourceRecords=Instances->PerInstanceSMData;SourceRecords[0].Transform.M[3][0]=205.62000000002445;
 if(!TestTrue(TEXT("source raw setup uses stock invalidation API"),Instances->BatchUpdateInstancesData(0,SourceRecords.Num(),SourceRecords.GetData(),false,true)))return false;
 TMap<const UObject*,FString> IDs;TMap<FString,UObject*> FirstObjects,SecondObjects,LightObjects;AddObjects(*First,TEXT("First"),IDs,FirstObjects);AddObjects(*Second,TEXT("Second"),IDs,SecondObjects);AddObjects(*Light,TEXT("Light"),IDs,LightObjects);
 IDs.Add(SourceWorld,TEXT("World"));IDs.Add(SourceWorld->PersistentLevel,TEXT("Level"));IDs.Add(ExtraLevel,TEXT("Level"));IDs.Add(SourceWorld->GetWorldSettings(),TEXT("Settings"));
 TSet<const UPackage*> Forbidden;Forbidden.Add(SourcePackage);
 TMap<UObject*,TArray<uint8>> SourceBefore;
 for(const auto* Group:{&FirstObjects,&SecondObjects,&LightObjects})for(const auto& Pair:*Group)
 {TArray<uint8> Bytes;if(!TestTrue(TEXT("source binary fixture state before"),State(*Pair.Value,IDs,Forbidden,false,Bytes)))return false;SourceBefore.Add(Pair.Value,MoveTemp(Bytes));}
 auto* SourceBody=Warp->GetBodySetup();if(!TestNotNull(TEXT("actual registered source warp body"),SourceBody))return false;
 const FGuid SourceBodyGuid=SourceBody->BodySetupGuid;
 TArray<uint8> SourceBodyBefore,SourceBodyAfter;if(!TestTrue(TEXT("source body before binary copy"),State(*SourceBody,IDs,Forbidden,false,SourceBodyBefore)))return false;
 TMap<UObject*,UObject*> Remap;Remap.Add(SourceWorld,TargetWorld);Remap.Add(SourceWorld->PersistentLevel,TargetWorld->PersistentLevel);Remap.Add(ExtraLevel,TargetWorld->PersistentLevel);Remap.Add(SourceWorld->GetWorldSettings(),TargetWorld->GetWorldSettings());
 TMap<UObject*,UObject*> Created;TArray<AActor*> Copies;FString Error;
 const bool Copied=BinaryCopyControls({First,Second,Light},*TargetWorld->PersistentLevel,Remap,Created,Copies,Lifetime,Error);
 if(!TestTrue(TEXT("same production binary transport succeeds: ")+Error,Copied))return false;
 TestTrue(TEXT("source transient Children unchanged after immediate native callbacks"),First->Children==FirstChildrenBefore&&Second->Children==SecondChildrenBefore);
 auto* PendingFirst=Cast<AActor>(Remap.FindRef(First));auto* PendingSecond=Cast<AActor>(Remap.FindRef(Second));
 TestTrue(TEXT("actual binary objects still require deferred PostLoad after immediate callbacks returned"),PendingFirst&&PendingSecond&&PendingFirst->HasAnyFlags(RF_NeedPostLoad)&&PendingSecond->HasAnyFlags(RF_NeedPostLoad));
 if(!TestNotNull(TEXT("pending copied owner before deferred loading"),PendingSecond))return false;TestEqual(TEXT("transient copied Children empty BEFORE deferred owner PostLoad"),PendingSecond->Children.Num(),0);
 TArray<TWeakObjectPtr<UObject>> BeforeGC;for(const auto& Pair:Created)BeforeGC.Emplace(Pair.Value);
 CollectGarbage(RF_NoFlags,true);
 for(const auto& Weak:BeforeGC)TestTrue(TEXT("every unpublished binary target survives forced interval GC"),Weak.IsValid());
 TestTrue(TEXT("source topology including transient Children unchanged after interval GC"),VerifyBinarySourceTopology(Lifetime,Error));TestTrue(TEXT("source transient Children unchanged after forced GC"),First->Children==FirstChildrenBefore&&Second->Children==SecondChildrenBefore);
 for(const auto& Pair:Remap)if(const auto* ID=IDs.Find(Pair.Key))IDs.Add(Pair.Value,*ID);
 auto* BinaryLightComponent=Cast<ULightComponentBase>(Remap.FindRef(LightComponent));
 if(!TestNotNull(TEXT("binary light component before deferred load"),BinaryLightComponent))return false;
 const FGuid BinaryLightGuid=GuidValue(*BinaryLightComponent,TEXT("LightGuid")),BinaryOriginalLightGuid=GuidValue(*BinaryLightComponent,TEXT("OriginalLightGuid"));
 AddInfo(FString::Printf(TEXT("LIGHT_GUID BEFORE_DEFERRED sourceLight=%s sourceOriginal=%s sourceValid=%d/%d binaryLight=%s binaryOriginal=%s sourceActor=%s binaryActor=%s sourceInstance=%s binaryInstance=%s"),*LightGuidBefore.ToString(),*OriginalLightGuidBefore.ToString(),int32(LightGuidBefore.IsValid()),int32(OriginalLightGuidBefore.IsValid()),*BinaryLightGuid.ToString(),*BinaryOriginalLightGuid.ToString(),*Light->GetActorGuid().ToString(),*CastChecked<AActor>(Remap.FindRef(Light))->GetActorGuid().ToString(),*Light->GetActorInstanceGuid().ToString(),*CastChecked<AActor>(Remap.FindRef(Light))->GetActorInstanceGuid().ToString()));
 AddInfo(FString::Printf(TEXT("LIGHT_POLICY BEFORE_DEFERRED sourceMobility=%d sourceStaticLighting=%d sourceStaticShadowing=%d binaryMobility=%d binaryStaticLighting=%d binaryStaticShadowing=%d"),int32(LightComponent->GetMobility()),int32(LightComponent->HasStaticLighting()),int32(LightComponent->HasStaticShadowing()),int32(BinaryLightComponent->GetMobility()),int32(BinaryLightComponent->HasStaticLighting()),int32(BinaryLightComponent->HasStaticShadowing())));
 const bool Finalized=FinalizeBinaryControls(Copies,*TargetWorld->PersistentLevel,Remap,Created,IDs,Forbidden,Lifetime,Error);
 if(!TestTrue(TEXT("same production deferred loaded-level finalization succeeds: ")+Error,Finalized))return false;
 TestTrue(TEXT("source transient Children unchanged after deferred PostLoad and registration"),First->Children==FirstChildrenBefore&&Second->Children==SecondChildrenBefore);
 auto* LightCopy=Cast<ADirectionalLight>(Remap.FindRef(Light));if(!TestNotNull(TEXT("actual copied light"),LightCopy))return false;
 auto* LightComponentCopy=Cast<ULightComponentBase>(LightCopy->GetLightComponent());if(!TestNotNull(TEXT("actual copied light component"),LightComponentCopy))return false;
 AddInfo(FString::Printf(TEXT("LIGHT_GUID AFTER_LOADED_REGISTER sourceLight=%s sourceOriginal=%s binaryBeforeLight=%s binaryBeforeOriginal=%s targetLight=%s targetOriginal=%s sourceActor=%s targetActor=%s sourceInstance=%s targetInstance=%s sourceRegistered=%d targetRegistered=%d"),*GuidValue(*LightComponent,TEXT("LightGuid")).ToString(),*GuidValue(*LightComponent,TEXT("OriginalLightGuid")).ToString(),*BinaryLightGuid.ToString(),*BinaryOriginalLightGuid.ToString(),*GuidValue(*LightComponentCopy,TEXT("LightGuid")).ToString(),*GuidValue(*LightComponentCopy,TEXT("OriginalLightGuid")).ToString(),*Light->GetActorGuid().ToString(),*LightCopy->GetActorGuid().ToString(),*Light->GetActorInstanceGuid().ToString(),*LightCopy->GetActorInstanceGuid().ToString(),int32(LightComponent->IsRegistered()),int32(LightComponentCopy->IsRegistered())));
 TestTrue(TEXT("World duplication preserves strict LightGuid and OriginalLightGuid"),GuidValue(*LightComponentCopy,TEXT("LightGuid"))==LightGuidBefore&&GuidValue(*LightComponentCopy,TEXT("OriginalLightGuid"))==OriginalLightGuidBefore);
 TestTrue(TEXT("source light GUIDs unchanged by immediate callbacks and deferred load"),GuidValue(*LightComponent,TEXT("LightGuid"))==LightGuidBefore&&GuidValue(*LightComponent,TEXT("OriginalLightGuid"))==OriginalLightGuidBefore);
 auto* FirstCopy=Cast<ADinkPlaceholderActor>(Remap.FindRef(First));auto* SecondCopy=Cast<ADinkPlaceholderActor>(Remap.FindRef(Second));auto* WarpCopy=Cast<UDinkWarpComponent>(Remap.FindRef(Warp));auto* NestedCopy=Cast<USceneComponent>(Remap.FindRef(Nested));auto* InstanceCopy=Cast<UInstancedStaticMeshComponent>(Remap.FindRef(Instances));
 if(!TestNotNull(TEXT("actual binary warp mapping"),WarpCopy)||!TestNotNull(TEXT("actual nested instance mapping"),NestedCopy)||!TestNotNull(TEXT("actual raw instance mapping"),InstanceCopy))return false;
 TestTrue(TEXT("flattened actors distinct and names unique"),FirstCopy&&SecondCopy&&FirstCopy!=SecondCopy&&FirstCopy->GetFName()!=SecondCopy->GetFName());
 TestTrue(TEXT("supported World-copy actor GUIDs are new valid identities, unlike retained light GUIDs"),FirstCopy->GetActorGuid().IsValid()&&SecondCopy->GetActorGuid().IsValid()&&FirstCopy->GetActorGuid()!=FirstActorGuidBefore&&SecondCopy->GetActorGuid()!=SecondActorGuidBefore&&FirstCopy->GetActorGuid()!=SecondCopy->GetActorGuid());
 TestTrue(TEXT("cross-actor owner points at copied actor"),FirstCopy->GetOwner()==SecondCopy);
 TestEqual(TEXT("copied owner Children has exactly one mapped child"),SecondCopy->Children.FilterByPredicate([&](const auto& A){return A.Get()==FirstCopy;}).Num(),1);for(const auto& Child:SecondCopy->Children)TestTrue(TEXT("copied Children never contains a source actor"),Child!=First&&Child!=Second&&Child->GetWorld()==TargetWorld);
 for(AActor* Copy:Copies)TestEqual(TEXT("every copied actor has unique level membership"),TargetWorld->PersistentLevel->Actors.FilterByPredicate([&](const auto& A){return A.Get()==Copy;}).Num(),1);
 TestEqual(TEXT("copied keyed placement identity"),Key(*FirstCopy),Key(*First));TestEqual(TEXT("copied real source-script identity"),FirstCopy->Origin->ScriptName,First->Origin->ScriptName);TestTrue(TEXT("copied material asset pointer exact"),FirstCopy->Card->GetMaterial(0)==First->Card->GetMaterial(0));TestEqual(TEXT("native default component CreationMethod"),int32(FirstCopy->GetRootComponent()->CreationMethod),int32(First->GetRootComponent()->CreationMethod));TestEqual(TEXT("nested instance CreationMethod"),int32(NestedCopy->CreationMethod),int32(Nested->CreationMethod));TestTrue(TEXT("nested component keeps copied outer and owner"),NestedCopy->GetOuter()==Remap.FindRef(Nested->GetOuter())&&NestedCopy->GetOwner()==FirstCopy);
 TestTrue(TEXT("nested cross-actor attach parent references copied defaultsubobject"),NestedCopy->GetAttachParent()==SecondCopy->GetRootComponent());
 TestTrue(TEXT("native defaultsubobject class/CDO archetypes preserved"),FirstCopy->GetRootComponent()->GetArchetype()==First->GetRootComponent()->GetArchetype()&&FirstCopy->GetArchetype()==First->GetArchetype());
 TestTrue(TEXT("actual DestLocation all double bits preserved"),ExactVectorBytes(Warp->DestLocation,WarpCopy->DestLocation));TestTrue(TEXT("actual BoxExtent all double bits preserved"),ExactVectorBytes(Warp->GetUnscaledBoxExtent(),WarpCopy->GetUnscaledBoxExtent()));
 TestTrue(TEXT("warp target and trigger fields preserved"),WarpCopy->DestScreen==Warp->DestScreen&&WarpCopy->WarpId==Warp->WarpId&&WarpCopy->bTriggerEnabled==Warp->bTriggerEnabled);
 TestTrue(TEXT("all64 collision policy preserved"),WarpCopy->GetCollisionResponseToChannels()==Warp->GetCollisionResponseToChannels());TestEqual(TEXT("warp collision profile preserved"),WarpCopy->GetCollisionProfileName(),Warp->GetCollisionProfileName());TestEqual(TEXT("warp collision enabled preserved"),int32(WarpCopy->GetCollisionEnabled()),int32(Warp->GetCollisionEnabled()));
 TestTrue(TEXT("actual box calculated bounds exact"),ExactVectorBytes(Warp->CalcBounds(Warp->GetComponentTransform()).BoxExtent,WarpCopy->CalcBounds(WarpCopy->GetComponentTransform()).BoxExtent));
 TestTrue(TEXT("owned loaded actors become registered before use"),WarpCopy->IsRegistered());
 TestEqual(TEXT("raw instance count exact"),InstanceCopy->PerInstanceSMData.Num(),Instances->PerInstanceSMData.Num());
 for(int I=0;I<Instances->PerInstanceSMData.Num();++I)for(int Row=0;Row<4;++Row)for(int Col=0;Col<4;++Col)
 {const auto A=Instances->PerInstanceSMData[I].Transform.M[Row][Col],B=InstanceCopy->PerInstanceSMData[I].Transform.M[Row][Col];TestTrue(TEXT("every raw instance scalar bit exact"),FMemory::Memcmp(&A,&B,sizeof(A))==0);}
 for(const auto& Pair:SourceBefore)
 {TArray<uint8> Bytes;TestTrue(TEXT("source binary state after"),State(*Pair.Key,IDs,Forbidden,false,Bytes));TestTrue(TEXT("every source actor/subobject byte unchanged"),Pair.Value==Bytes);
  UObject* Target=Remap.FindRef(Pair.Key);TArray<uint8> TargetBytes;
  if(!Target)
  {
   AddInfo(FString::Printf(TEXT("MISSING_BINARY_REMAP source=%s class=%s flags=0x%llx outer=%s archetype=%s sourcePackage=%s"),*Pair.Key->GetPathName(),*Pair.Key->GetClass()->GetPathName(),static_cast<unsigned long long>(Pair.Key->GetFlags()),*GetPathNameSafe(Pair.Key->GetOuter()),*GetPathNameSafe(Pair.Key->GetArchetype()),*Pair.Key->GetOutermost()->GetName()));
   auto* SourceShape=Cast<UShapeComponent>(Pair.Key->GetOuter());auto* TargetShape=SourceShape?Cast<UShapeComponent>(Remap.FindRef(SourceShape)):nullptr;
   const auto* ShapeProperty=FindFProperty<FObjectPropertyBase>(UShapeComponent::StaticClass(),TEXT("ShapeBodySetup"));
   if(SourceShape&&TargetShape&&ShapeProperty)
   {
    auto* SourceExisting=Cast<UBodySetup>(ShapeProperty->GetObjectPropertyValue_InContainer(SourceShape));auto* TargetExisting=Cast<UBodySetup>(ShapeProperty->GetObjectPropertyValue_InContainer(TargetShape));
    AddInfo(FString::Printf(TEXT("MISSING_BODY_CONTEXT pointerPropertyFlags=0x%llx sourceFieldPointsAtMissing=%d sourceExisting=%s targetExisting=%s sourceBodyGuid=%s targetBodyGuid=%s targetRegistered=%d"),static_cast<unsigned long long>(ShapeProperty->GetPropertyFlags()),int32(SourceExisting==Pair.Key),*GetPathNameSafe(SourceExisting),*GetPathNameSafe(TargetExisting),SourceExisting?*SourceExisting->BodySetupGuid.ToString():TEXT("None"),TargetExisting?*TargetExisting->BodySetupGuid.ToString():TEXT("None"),int32(TargetShape->IsRegistered())));
    if(SourceExisting&&TargetExisting)AddInfo(TEXT("EXISTING_BODY_FIRST_STATE_DIFFERENCE ")+FirstStateDifference(*SourceExisting,*TargetExisting,IDs,Forbidden));
   }
  }
  if(!TestNotNull(TEXT("complete source subobject remap"),Target))return false;
  const bool TargetStateOK=State(*Target,IDs,Forbidden,true,TargetBytes);TestTrue(TEXT("strict actual target state contains no source refs"),TargetStateOK);
  if(Pair.Value!=TargetBytes)AddInfo(FString::Printf(TEXT("BINARY_TRACKED_STATE_DIFFERENCE source=%s target=%s sourceClass=%s targetClass=%s sourceFlags=0x%llx targetFlags=0x%llx sourceOuter=%s targetOuter=%s sourceArchetype=%s targetArchetype=%s sourceBytes=%d targetBytes=%d "),*Pair.Key->GetPathName(),*Target->GetPathName(),*Pair.Key->GetClass()->GetPathName(),*Target->GetClass()->GetPathName(),static_cast<unsigned long long>(Pair.Key->GetFlags()),static_cast<unsigned long long>(Target->GetFlags()),*GetPathNameSafe(Pair.Key->GetOuter()),*GetPathNameSafe(Target->GetOuter()),*GetPathNameSafe(Pair.Key->GetArchetype()),*GetPathNameSafe(Target->GetArchetype()),Pair.Value.Num(),TargetBytes.Num())+FirstStateDifference(*Pair.Key,*Target,IDs,Forbidden));
  TestTrue(TEXT("full binary transported tracked state exact"),Pair.Value==TargetBytes);}
 TestTrue(TEXT("source body after binary finalization"),State(*SourceBody,IDs,Forbidden,false,SourceBodyAfter));TestTrue(TEXT("source BodySetup immutable"),SourceBodyBefore==SourceBodyAfter);TestTrue(TEXT("source BodySetup GUID unchanged"),SourceBody->BodySetupGuid==SourceBodyGuid);
 auto* CopyBody=WarpCopy->GetBodySetup();if(!TestNotNull(TEXT("actual registered copied box body"),CopyBody))return false;
 TestEqual(TEXT("copied physical box shape count"),CopyBody->AggGeom.BoxElems.Num(),SourceBody->AggGeom.BoxElems.Num());
 if(SourceBody->AggGeom.BoxElems.Num()==1&&CopyBody->AggGeom.BoxElems.Num()==1)
 {TestEqual(TEXT("copied physical box X"),CopyBody->AggGeom.BoxElems[0].X,SourceBody->AggGeom.BoxElems[0].X);TestEqual(TEXT("copied physical box Y"),CopyBody->AggGeom.BoxElems[0].Y,SourceBody->AggGeom.BoxElems[0].Y);TestEqual(TEXT("copied physical box Z"),CopyBody->AggGeom.BoxElems[0].Z,SourceBody->AggGeom.BoxElems[0].Z);}
 TestEqual(TEXT("copied physics readiness matches source"),WarpCopy->IsPhysicsStateCreated(),Warp->IsPhysicsStateCreated());
 TMap<UObject*,UObject*> MissingMap=Remap;MissingMap.Remove(Second);TestFalse(TEXT("missing cross-actor mapping refuses before deferred PostLoad"),FinalizeBinaryControls(Copies,*TargetWorld->PersistentLevel,MissingMap,Created,IDs,Forbidden,Lifetime,Error));
 TMap<UObject*,UObject*> ConflictingMap;ConflictingMap.Add(First,First);TMap<UObject*,UObject*> BadCreated;TArray<AActor*> BadCopies;TestFalse(TEXT("source actor as its own copy refuses"),BinaryCopyControls({First},*TargetWorld->PersistentLevel,ConflictingMap,BadCreated,BadCopies,BadLifetime,Error));
 TMap<UObject*,UObject*> IncompleteSeed;IncompleteSeed.Add(SourceWorld,TargetWorld);IncompleteSeed.Add(SourceWorld->PersistentLevel,TargetWorld->PersistentLevel);IncompleteSeed.Add(ExtraLevel,TargetWorld->PersistentLevel);IncompleteSeed.Add(SourceWorld->GetWorldSettings(),TargetWorld->GetWorldSettings());
 const bool IncompleteCopied=BinaryCopyControls({First},*TargetWorld->PersistentLevel,IncompleteSeed,BadCreated,BadCopies,BadLifetime,Error);
 if(!TestTrue(TEXT("incomplete peer map fixture still binary copies its root"),IncompleteCopied))return false;
 for(const auto& Pair:IncompleteSeed)if(const auto* ID=IDs.Find(Pair.Key))IDs.Add(Pair.Value,*ID);
 TestFalse(TEXT("retained source cross-actor reference refuses before PostLoad"),FinalizeBinaryControls(BadCopies,*TargetWorld->PersistentLevel,IncompleteSeed,BadCreated,IDs,Forbidden,BadLifetime,Error));TestTrue(TEXT("missing peer refusal reports actual source reference"),Error.Contains(TEXT("source-package reference before deferred PostLoad")));
 auto* SourceInstanceTemplate=NewObject<ADinkPlaceholderActor>(SourceWorld->PersistentLevel,TEXT("BinaryInstanceArchetype"),RF_Transactional,First);
 TMap<UObject*,UObject*> ArchetypeSeed;ArchetypeSeed.Add(SourceWorld,TargetWorld);ArchetypeSeed.Add(SourceWorld->PersistentLevel,TargetWorld->PersistentLevel);ArchetypeSeed.Add(Second,SecondCopy);
 const bool ArchetypeCopied=BinaryCopyControls({SourceInstanceTemplate},*TargetWorld->PersistentLevel,ArchetypeSeed,BadCreated,BadCopies,BadLifetime,Error);
 TestFalse(TEXT("source-instance archetype refuses BEFORE binary construction"),ArchetypeCopied);TestTrue(TEXT("archetype preflight identifies source-instance archetype"),Error.Contains(TEXT("source-instance archetype")));
 for(const auto& Pair:SourceBefore){TArray<uint8> Bytes;TestTrue(TEXT("source state after refusal fixtures"),State(*Pair.Key,IDs,Forbidden,false,Bytes));TestTrue(TEXT("no refusal fixture changed source bytes"),Pair.Value==Bytes);}
 TestTrue(TEXT("source body after refusal fixtures"),State(*SourceBody,IDs,Forbidden,false,SourceBodyAfter));TestTrue(TEXT("source body and GUID unchanged after all negative cases"),SourceBodyBefore==SourceBodyAfter&&SourceBody->BodySetupGuid==SourceBodyGuid);
 return true;
}

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
 // Actual Stage25 parent-root quaternion measurement, converted by the
 // installed native quaternion/rotator path; actual stage remains separate.
 AActor* EulerOwnerS=World->SpawnActor<AActor>();AActor* EulerOwnerT=NewWorld->SpawnActor<AActor>();
 auto* EulerRootS=NewObject<USceneComponent>(EulerOwnerS);auto* EulerRootT=NewObject<USceneComponent>(EulerOwnerT);
 EulerOwnerS->SetRootComponent(EulerRootS);EulerOwnerT->SetRootComponent(EulerRootT);EulerRootS->RegisterComponent();EulerRootT->RegisterComponent();
 const FQuat Stage25RootQ(-0.,0.,-1.2370370394624901e-6,.99999999999923483);
 const FRotator EulerS=Stage25RootQ.Rotator();
 auto* EulerProperty=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),TEXT("RelativeRotation"));
 if(!TestNotNull(TEXT("actual native root rotation property"),EulerProperty))return false;
 auto RootPose=[](USceneComponent& C,const FVector& L,const FRotator& R){C.SetRelativeLocation_Direct(L);C.SetRelativeRotation_Direct(R);C.UpdateComponentToWorld(EUpdateTransformFlags::None,ETeleportType::TeleportPhysics);};
 const FVector Stage25RootP(-86633.889999999999,423474.72999999998,0);
 RootPose(*EulerRootS,Stage25RootP,EulerS);
 constexpr int EulerFlags=PPF_DeepCompareInstances|PPF_ExportsNotFullyQualified|PPF_Copy|PPF_Delimited;
 FString EulerText;EulerProperty->ExportTextItem_Direct(EulerText,EulerProperty->ContainerPtrToValuePtr<void>(EulerRootS),nullptr,EulerRootS,EulerFlags);
 FRotator EulerT=FRotator::ZeroRotator;FOutputDeviceNull EulerErrors;
 if(!TestNotNull(TEXT("actual native Euler TEXT parse"),EulerProperty->ImportText_Direct(*EulerText,&EulerT,EulerRootT,EulerFlags,&EulerErrors)))return false;
 RootPose(*EulerRootT,Stage25RootP,EulerT);
 TestTrue(TEXT("Stage25 root Euler fixture world positions already byteexact"),ExactVectorBytes(EulerOwnerS->GetActorLocation(),EulerOwnerT->GetActorLocation()));
 TestTrue(TEXT("Stage25 root Euler fixture genuinely different quaternion before repair"),!ExactQuaternion(EulerRootS->GetComponentQuat(),EulerRootT->GetComponentQuat()));
 TestEqual(TEXT("Stage25 target rounded yaw"),EulerT.Yaw,-.000142);
 TMap<UObject*,UObject*> EulerMap;EulerMap.Add(EulerOwnerS,EulerOwnerT);EulerMap.Add(EulerRootS,EulerRootT);
 TArray<uint8> EulerBefore,EulerAfter;TestTrue(TEXT("Euler source before repair raw state"),State(*EulerRootS,TestIDs,NoForbidden,false,EulerBefore));
 bool EulerRestored=false;FString EulerEvidence;
 const bool EulerOK=RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,EulerMap,EulerRestored,EulerEvidence);
 TestTrue(TEXT("same-position Stage25 TEXT-only root Euler repair succeeds: ")+EulerEvidence,EulerOK);
 TestTrue(TEXT("same-position root Euler repair performed"),EulerRestored);
 TestTrue(TEXT("root Euler repair actor/world byteexact"),ExactTransformBytes(EulerOwnerS->GetActorTransform(),EulerOwnerT->GetActorTransform()));AddInfo(EulerEvidence);
 FRotator ArbitraryRoot=EulerT;ArbitraryRoot.Yaw+=.0000001;RootPose(*EulerRootT,Stage25RootP,ArbitraryRoot);
 TestFalse(TEXT("arbitrary nonTEXT root yaw refuses"),RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,EulerMap,EulerRestored,EulerEvidence));
 RootPose(*EulerRootT,Stage25RootP,EulerT);TMap<UObject*,UObject*> InvalidEulerMap=EulerMap;InvalidEulerMap.Remove(EulerRootS);
 TestFalse(TEXT("root Euler wrong root mapping refuses"),RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,InvalidEulerMap,EulerRestored,EulerEvidence));
 InvalidEulerMap=EulerMap;InvalidEulerMap.Remove(EulerOwnerS);
 TestFalse(TEXT("root Euler wrong actor mapping refuses"),RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,InvalidEulerMap,EulerRestored,EulerEvidence));
 TestFalse(TEXT("root Euler wrong NEW world refuses"),RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,World,EulerMap,EulerRestored,EulerEvidence));
 EulerRootT->SetRelativeScale3D(FVector(1,1,2));
 TestFalse(TEXT("root Euler changed scale refuses"),RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,EulerMap,EulerRestored,EulerEvidence));EulerRootT->SetRelativeScale3D(FVector::OneVector);
 SetExact(*EulerRootT,Stage25RootP+FVector(1,0,0));
 TestFalse(TEXT("root Euler changed position refuses"),RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,EulerMap,EulerRestored,EulerEvidence));SetExact(*EulerRootT,Stage25RootP);
 AActor* ExtraEulerParentActor=NewWorld->SpawnActor<AActor>();
 if(!TestNotNull(TEXT("separate root Euler attachment fixture parent actor"),ExtraEulerParentActor))return false;
 auto* ExtraEulerParent=NewObject<USceneComponent>(ExtraEulerParentActor);ExtraEulerParentActor->SetRootComponent(ExtraEulerParent);ExtraEulerParent->RegisterComponent();
 const bool ActualRootAttachment=EulerRootT->AttachToComponent(ExtraEulerParent,FAttachmentTransformRules::KeepRelativeTransform);
 if(!TestTrue(TEXT("root Euler negative has an actual different-actor parent attachment"),ActualRootAttachment&&EulerRootT->GetAttachParent()==ExtraEulerParent))return false;
 TestFalse(TEXT("attached root Euler refuses"),RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,EulerMap,EulerRestored,EulerEvidence));EulerRootT->DetachFromComponent(FDetachmentTransformRules::KeepRelativeTransform);
 RootPose(*EulerRootT,Stage25RootP,EulerT);EulerProperty->ContainerPtrToValuePtr<FRotator>(EulerRootT)->Yaw=std::numeric_limits<double>::quiet_NaN();
 TestFalse(TEXT("nonfinite root Euler refuses before setter"),RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,EulerMap,EulerRestored,EulerEvidence));EulerProperty->ContainerPtrToValuePtr<FRotator>(EulerRootT)->Yaw=EulerT.Yaw;
 TestTrue(TEXT("Euler source after all cases raw state"),State(*EulerRootS,TestIDs,NoForbidden,false,EulerAfter));TestTrue(TEXT("root Euler source raw state unchanged"),EulerBefore==EulerAfter);
 // Actual Stage27 S144_P01: both independently stock-TEXT-derived fields differ.
 const FVector S144SourceP(61693.359999999993,7929.4799999999996,0);
 const FRotator S144SourceEuler(-0.,-.077097042524470513,-0.);
 RootPose(*EulerRootS,S144SourceP,S144SourceEuler);
 auto* S144LocationProperty=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),TEXT("RelativeLocation"));
 if(!TestNotNull(TEXT("actual S144 location property"),S144LocationProperty))return false;
 FString S144PText,S144EulerText;
 S144LocationProperty->ExportTextItem_Direct(S144PText,S144LocationProperty->ContainerPtrToValuePtr<void>(EulerRootS),nullptr,EulerRootS,EulerFlags);
 EulerProperty->ExportTextItem_Direct(S144EulerText,EulerProperty->ContainerPtrToValuePtr<void>(EulerRootS),nullptr,EulerRootS,EulerFlags);
 FVector S144TargetP=FVector::ZeroVector;FRotator S144TargetEuler=FRotator::ZeroRotator;
 const TCHAR* S144PTail=S144LocationProperty->ImportText_Direct(*S144PText,&S144TargetP,EulerRootT,EulerFlags,&EulerErrors);
 const TCHAR* S144ETail=EulerProperty->ImportText_Direct(*S144EulerText,&S144TargetEuler,EulerRootT,EulerFlags,&EulerErrors);
 if(!TestTrue(TEXT("S144 fixture parses complete real stock TEXT fields"),S144PTail&&!*S144PTail&&S144ETail&&!*S144ETail))return false;
 TestEqual(TEXT("actual measured S144 target X"),S144TargetP.X,61693.360000000001);
 TestEqual(TEXT("actual measured S144 target yaw"),S144TargetEuler.Yaw,-.077096999999999999);
 RootPose(*EulerRootT,S144TargetP,S144TargetEuler);
 TestFalse(TEXT("S144 precondition position genuinely differs"),ExactVectorBytes(EulerOwnerS->GetActorLocation(),EulerOwnerT->GetActorLocation()));
 TestFalse(TEXT("S144 precondition quaternion genuinely differs"),ExactQuaternion(EulerRootS->GetComponentQuat(),EulerRootT->GetComponentQuat()));
 TArray<uint8> S144Before,S144After;TestTrue(TEXT("S144 source raw before"),State(*EulerRootS,TestIDs,NoForbidden,false,S144Before));
 const bool S144OK=RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,EulerMap,EulerRestored,EulerEvidence);
 TestTrue(TEXT("actual S144 combined TEXT position/Euler repair succeeds: ")+EulerEvidence,S144OK);
 TestTrue(TEXT("S144 repair performed"),EulerRestored);
 TestTrue(TEXT("S144 source/target actor and component worlds byteexact after"),ExactTransformBytes(EulerOwnerS->GetActorTransform(),EulerOwnerT->GetActorTransform())&&ExactTransformBytes(EulerRootS->GetComponentTransform(),EulerRootT->GetComponentTransform()));AddInfo(EulerEvidence);
 const FVector ArbitraryS144P(std::nextafter(S144TargetP.X,std::numeric_limits<double>::infinity()),S144TargetP.Y,S144TargetP.Z);
 RootPose(*EulerRootT,ArbitraryS144P,S144TargetEuler);
 TestFalse(TEXT("combined S144 arbitrary nonTEXT position refuses"),RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,EulerMap,EulerRestored,EulerEvidence));
 TestTrue(TEXT("refused arbitrary S144 position unchanged"),ExactVectorBytes(EulerRootT->GetRelativeLocation(),ArbitraryS144P));
 FRotator ArbitraryS144Euler=S144TargetEuler;ArbitraryS144Euler.Yaw+=.0000001;RootPose(*EulerRootT,S144TargetP,ArbitraryS144Euler);
 TestFalse(TEXT("combined S144 arbitrary nonTEXT Euler refuses"),RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,EulerMap,EulerRestored,EulerEvidence));
 TestTrue(TEXT("refused arbitrary S144 Euler leaves target position unchanged"),ExactVectorBytes(EulerRootT->GetRelativeLocation(),S144TargetP));
 TestTrue(TEXT("S144 source raw after"),State(*EulerRootS,TestIDs,NoForbidden,false,S144After));TestTrue(TEXT("S144 source raw bytes unchanged"),S144Before==S144After);
 // Actual Stage29 parent Bounds position-only TWO-ULP stock TEXT case.
 const FVector Stage29ParentP(585.82000000000005,55656.424999999988,500);
 RootPose(*EulerRootS,Stage29ParentP,FRotator::ZeroRotator);
 FString Stage29ParentText;S144LocationProperty->ExportTextItem_Direct(Stage29ParentText,S144LocationProperty->ContainerPtrToValuePtr<void>(EulerRootS),nullptr,EulerRootS,EulerFlags);
 FVector Stage29ParentTarget=FVector::ZeroVector;
 const TCHAR* Stage29Tail=S144LocationProperty->ImportText_Direct(*Stage29ParentText,&Stage29ParentTarget,EulerRootT,EulerFlags,&EulerErrors);
 if(!TestTrue(TEXT("Stage29 parent fixture actual stock parse complete"),Stage29Tail&&!*Stage29Tail))return false;
 TestEqual(TEXT("actual measured Stage29 parent target Y"),Stage29ParentTarget.Y,55656.425000000003);
 const double Stage29A[]={Stage29ParentP.X,Stage29ParentP.Y,Stage29ParentP.Z},Stage29B[]={Stage29ParentTarget.X,Stage29ParentTarget.Y,Stage29ParentTarget.Z};
 TestFalse(TEXT("Stage29 measured parent remains outside unchanged ONE-ULP predicate"),AdjacentTranslationValues(Stage29A,Stage29B));
 RootPose(*EulerRootT,Stage29ParentTarget,FRotator::ZeroRotator);
 TArray<uint8> ParentBefore,ParentAfter;TestTrue(TEXT("Stage29 source raw before"),State(*EulerRootS,TestIDs,NoForbidden,false,ParentBefore));
 const bool ParentOK=RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,EulerMap,EulerRestored,EulerEvidence);
 TestTrue(TEXT("Stage29 position-only stock TEXT parent repair succeeds: ")+EulerEvidence,ParentOK);TestTrue(TEXT("Stage29 parent repair performed"),EulerRestored);
 TestTrue(TEXT("Stage29 repaired parent actor and root bytes exact"),ExactTransformBytes(EulerOwnerS->GetActorTransform(),EulerOwnerT->GetActorTransform())&&ExactTransformBytes(EulerRootS->GetComponentTransform(),EulerRootT->GetComponentTransform()));AddInfo(EulerEvidence);
 FVector NonTextParent=Stage29ParentTarget;NonTextParent.Y=std::nextafter(std::nextafter(Stage29ParentP.Y,-std::numeric_limits<double>::infinity()),-std::numeric_limits<double>::infinity());RootPose(*EulerRootT,NonTextParent,FRotator::ZeroRotator);
 TestFalse(TEXT("position-only arbitrary nonTEXT TWO-ULP refuses"),RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,EulerMap,EulerRestored,EulerEvidence));TestFalse(TEXT("nonTEXT parent never restored"),EulerRestored);TestTrue(TEXT("nonTEXT parent target untouched"),ExactVectorBytes(EulerRootT->GetRelativeLocation(),NonTextParent));
 RootPose(*EulerRootT,Stage29ParentTarget,FRotator(0,.1,0));TestFalse(TEXT("position-only changed Q/Euler not restored"),RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,EulerMap,EulerRestored,EulerEvidence));
 RootPose(*EulerRootT,Stage29ParentTarget,FRotator::ZeroRotator);EulerRootT->SetRelativeScale3D(FVector(1,1,2));TestFalse(TEXT("position-only changed scale refuses"),RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,EulerMap,EulerRestored,EulerEvidence));EulerRootT->SetRelativeScale3D(FVector::OneVector);
 RootPose(*EulerRootT,Stage29ParentTarget,FRotator::ZeroRotator);TMap<UObject*,UObject*> WrongParentOwnerMap=EulerMap;WrongParentOwnerMap.Remove(EulerOwnerS);TestFalse(TEXT("position-only wrong owner mapping refuses"),RestoreNewTargetRootTranslation(*EulerOwnerS,*EulerOwnerT,NewWorld,WrongParentOwnerMap,EulerRestored,EulerEvidence));
 TestTrue(TEXT("Stage29 source raw after"),State(*EulerRootS,TestIDs,NoForbidden,false,ParentAfter));TestTrue(TEXT("Stage29 parent source bytes unchanged"),ParentBefore==ParentAfter);
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
 TestTrue(TEXT("actual Card TEXT-roundtrip >oneULP childlocal restoration succeeds"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 TestTrue(TEXT("actual Card childlocal restoration was performed"),LocalRestored);TestTrue(TEXT("actual Card source relative/world exact after repair"),ExactVectorBytes(LocalS->GetRelativeLocation(),LocalT->GetRelativeLocation())&&ExactTransformBytes(LocalS->GetComponentTransform(),LocalT->GetComponentTransform()));
 AddInfo(LocalProof);
 SetExact(*LocalT,ObservedT+FVector(1,0,0));
 TestFalse(TEXT("arbitrary child position is not repaired as TEXT drift"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 SetExact(*LocalT,ObservedT);TMap<UObject*,UObject*> BadLocalMap=LocalMap;BadLocalMap.Remove(LocalS);
 TestFalse(TEXT("child wrong component map refuses"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,BadLocalMap,LocalRestored,LocalProof));
 BadLocalMap=LocalMap;BadLocalMap.Remove(ParentS);
 TestFalse(TEXT("child wrong parent map refuses"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,BadLocalMap,LocalRestored,LocalProof));
 TestFalse(TEXT("child wrong NEW world refuses"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,World,LocalMap,LocalRestored,LocalProof));
 LocalT->AttachToComponent(ParentT,FAttachmentTransformRules::KeepRelativeTransform,TEXT("wrong_socket"));
 TestFalse(TEXT("child different attachment socket refuses"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 LocalT->AttachToComponent(ParentT,FAttachmentTransformRules::KeepRelativeTransform);
 LocalT->SetRelativeRotation(FRotator(0,1,0));
 TestFalse(TEXT("child changed rotation refuses"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 LocalT->SetRelativeRotation(FRotator::ZeroRotator);LocalT->SetRelativeScale3D(FVector(2,1,1));
 TestFalse(TEXT("child changed scale refuses"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 LocalT->SetRelativeScale3D(FVector::OneVector);
 auto* LocationProperty=FindFProperty<FStructProperty>(USceneComponent::StaticClass(),TEXT("RelativeLocation"));
 LocationProperty->ContainerPtrToValuePtr<FVector>(LocalT)->X=std::numeric_limits<double>::quiet_NaN();
 TestFalse(TEXT("child nonfinite relative location refuses before setter"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 LocationProperty->ContainerPtrToValuePtr<FVector>(LocalT)->X=ObservedT.X;
 TestTrue(TEXT("local source post-repair raw state available"),State(*LocalS,TestIDs,NoForbidden,false,LocalAfter));TestTrue(TEXT("child source raw state never changed"),LocalBefore==LocalAfter);
 const FVector WarpLocationS(-68.744999999995343,-68.747499999997672,150),WarpLocationT(-68.745000000000005,-68.747500000000002,150);
 const FRotator WarpRotationS(-0.,-.00090586212638620685,-0.),WarpRotationT(-0.,-.00090600000000000001,-0.);
 auto PoseExact=[](USceneComponent& C,const FVector& L,const FRotator& R){C.SetRelativeRotation_Direct(R);C.SetRelativeLocation_Direct(L);C.UpdateComponentToWorld(EUpdateTransformFlags::None,ETeleportType::TeleportPhysics);};
 PoseExact(*LocalS,WarpLocationS,WarpRotationS);PoseExact(*LocalT,WarpLocationT,WarpRotationT);
 TestTrue(TEXT("actual Warp yaw has genuinely different direct quaternion before restoration"),!ExactQuaternion(LocalS->GetRelativeRotation().Quaternion(),LocalT->GetRelativeRotation().Quaternion()));
 TArray<uint8> WarpBefore,WarpAfter;TestTrue(TEXT("Warp source before pose repair serializes"),State(*LocalS,TestIDs,NoForbidden,false,WarpBefore));
 TestTrue(TEXT("actual Warp XY plus yaw TEXT drift restores"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 TestTrue(TEXT("actual Warp XY+yaw repair performed"),LocalRestored);TestTrue(TEXT("actual Warp world pose exactly source after repair"),ExactTransformBytes(LocalS->GetComponentTransform(),LocalT->GetComponentTransform()));AddInfo(LocalProof);
 PoseExact(*LocalT,WarpLocationS,WarpRotationT);
 TestTrue(TEXT("same-location yaw-only TEXT drift restores"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 TestTrue(TEXT("yaw-only repair not skipped by equal locations"),LocalRestored);TestTrue(TEXT("yaw-only repaired world byteexact"),ExactTransformBytes(LocalS->GetComponentTransform(),LocalT->GetComponentTransform()));
 FRotator ArbitraryYaw=WarpRotationT;ArbitraryYaw.Yaw+=.0000001;PoseExact(*LocalT,WarpLocationS,ArbitraryYaw);
 TestFalse(TEXT("arbitrary nonTEXT yaw refuses"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));
 PoseExact(*LocalT,WarpLocationS,WarpRotationT);
 TMap<UObject*,UObject*> BadYawMap=LocalMap;BadYawMap.Remove(LocalS);
 TestFalse(TEXT("rotation-only wrong component mapping refuses"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,BadYawMap,LocalRestored,LocalProof));
 TestFalse(TEXT("rotation-only wrong NEW world refuses"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,World,LocalMap,LocalRestored,LocalProof));
 ParentT->SetRelativeRotation(FRotator(0,1,0));
 TestFalse(TEXT("rotation-only changed parent quaternion frame refuses"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));ParentT->SetRelativeRotation(FRotator::ZeroRotator);
 LocalT->SetRelativeScale3D(FVector(1,2,1));
 TestFalse(TEXT("rotation-only changed scale refuses"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));LocalT->SetRelativeScale3D(FVector::OneVector);
 RP->ContainerPtrToValuePtr<FRotator>(LocalT)->Yaw=std::numeric_limits<double>::quiet_NaN();
 TestFalse(TEXT("rotation-only nonfinite yaw refuses before setter"),RestoreNewTargetChildPose(*LocalS,*LocalT,LocalOwnerS,LocalOwnerT,NewWorld,LocalMap,LocalRestored,LocalProof));RP->ContainerPtrToValuePtr<FRotator>(LocalT)->Yaw=WarpRotationT.Yaw;
 TestTrue(TEXT("Warp source after all pose cases serializes"),State(*LocalS,TestIDs,NoForbidden,false,WarpAfter));TestTrue(TEXT("Warp source raw state unchanged"),WarpBefore==WarpAfter);










 return true;
}
#endif
