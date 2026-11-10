#pragma once
#include "CoreMinimal.h"

/** Authored presentation boundary only; never a collision shape or replacement hit. */
namespace DinkCameraPortal
{
struct FDefinition
{
    FVector Point=FVector::ZeroVector,Normal=FVector::ForwardVector,Tangent=FVector::RightVector;
    FVector InteriorPoint=FVector::ZeroVector;
    FVector2D Minimum=FVector2D::ZeroVector,Maximum=FVector2D::ZeroVector;
    TArray<FPlane> InteriorPlanes; // Inside: PlaneDot(local point)<=0.
    bool IsValid() const
    {
        if(InteriorPoint.ContainsNaN()||Point.ContainsNaN()||Normal.ContainsNaN()||Tangent.ContainsNaN()||Minimum.ContainsNaN()||Maximum.ContainsNaN()||
           !FMath::IsNearlyEqual(Normal.SizeSquared(),1.,1.e-6)||!FMath::IsNearlyEqual(Tangent.SizeSquared(),1.,1.e-6)||
           FMath::Abs(Normal.Z)>1.e-6||FMath::Abs(Tangent.Z)>1.e-6||FMath::Abs(FVector::DotProduct(Normal,Tangent))>1.e-6||
           Minimum.X>=Maximum.X||Minimum.Y>=Maximum.Y||InteriorPlanes.Num()<4)return false;
        bool SupportingPlane=false;
        for(const FPlane& P:InteriorPlanes)
        {
            const FVector N(P.X,P.Y,P.Z);
            if(N.ContainsNaN()||!FMath::IsFinite(P.W)||!FMath::IsNearlyEqual(N.SizeSquared(),1.,1.e-6)||P.PlaneDot(InteriorPoint)>=0)return false;
            SupportingPlane|=FVector::DotProduct(N,Normal)>1.-1.e-6&&P.W<=FVector::DotProduct(Point,Normal);
        }
        return SupportingPlane;
    }
    bool Inside(const FVector& Local,double Margin=0) const
    {
        for(const FPlane& P:InteriorPlanes)if(P.PlaneDot(Local)>Margin)return false;
        return true;
    }
};
struct FLimit
{
    double Fraction=1;
    bool bInfeasible=false;
    FVector Point=FVector::ZeroVector,Normal=FVector::ZeroVector;
    double Clearance=0;
    FString Owner,MeshSourceSHA;
    bool Outside(const FVector& Eye) const
    {return !Eye.ContainsNaN()&&FVector::DotProduct(Eye-Point,Normal)+1.e-5>=Clearance;}
};
inline bool Limit(const FDefinition& Rule,const FTransform& Owner,const FVector& Pivot,const FVector& Desired,
                  double ProbeRadius,FLimit& Out,double FrustumClearance=0)
{
    Out=FLimit();
    const FVector Scale=Owner.GetScale3D();
    if(!Rule.IsValid()||Owner.ContainsNaN()||Pivot.ContainsNaN()||Desired.ContainsNaN()||!FMath::IsFinite(ProbeRadius)||ProbeRadius<=0||!FMath::IsFinite(FrustumClearance)||FrustumClearance<0||
       Scale.X<=0||!FMath::IsNearlyEqual(Scale.X,Scale.Y,1.e-6)||!FMath::IsNearlyEqual(Scale.X,Scale.Z,1.e-6)||
       FVector::DotProduct(Owner.GetRotation().GetUpVector(),FVector::UpVector)<1.-1.e-6)return false;
    const FVector A=Owner.InverseTransformPosition(Pivot),B=Owner.InverseTransformPosition(Desired);
    const double Clearance=FMath::Max(ProbeRadius,FrustumClearance);
    const double Radius=ProbeRadius/Scale.X,Needed=Clearance/Scale.X,DA=FVector::DotProduct(A-Rule.Point,Rule.Normal),DB=FVector::DotProduct(B-Rule.Point,Rule.Normal);
    if(DA<=0||DB>=Needed||DA<=DB)return false;
    // Require the actual boom to cross this finite authored aperture; nearby walls/context are not portals.
    const double T=DA/(DA-DB);
    if(T<=0||T>=1)return false;
    const FVector Cross=A+(B-A)*T-Rule.Point;
    const double U=FVector::DotProduct(Cross,Rule.Tangent),V=Cross.Z;
    if(U<Rule.Minimum.X||U>Rule.Maximum.X||V<Rule.Minimum.Y||V>Rule.Maximum.Y)return false;
    if(Rule.Maximum.X-Rule.Minimum.X<2*Radius||Rule.Maximum.Y-Rule.Minimum.Y<2*Radius)
    {Out.bInfeasible=true;Out.Fraction=0;return false;}
    if(U<Rule.Minimum.X+Radius||U>Rule.Maximum.X-Radius||V<Rule.Minimum.Y+Radius||V>Rule.Maximum.Y-Radius)return false;
    if(Rule.Inside(A,Radius)||DA<=Needed){Out.bInfeasible=true;Out.Fraction=0;return false;}
    Out.Fraction=(DA-Needed)/(DA-DB);
    Out.Point=Owner.TransformPosition(Rule.Point);
    Out.Normal=Owner.TransformVectorNoScale(Rule.Normal).GetSafeNormal();Out.Clearance=Clearance;
    return Out.Fraction>0&&Out.Fraction<1&&Out.Outside(Pivot+(Desired-Pivot)*Out.Fraction);
}
}
