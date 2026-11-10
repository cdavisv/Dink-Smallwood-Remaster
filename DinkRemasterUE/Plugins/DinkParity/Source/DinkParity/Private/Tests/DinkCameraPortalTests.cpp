#include "DinkTestHelpers.h"
#include "DinkCameraPortal.h"
#include "DinkCameraHeadroom.h"
#include <limits>
namespace
{
DinkCameraPortal::FDefinition Rule()
{
    DinkCameraPortal::FDefinition R;R.Point=FVector(530,479.5,0);R.Normal=FVector(0,1,0);R.Tangent=FVector(1,0,0);
    R.Minimum=FVector2D(-75,22);R.Maximum=FVector2D(75,250);R.InteriorPoint=FVector(0,0,100);
    R.InteriorPlanes={FPlane(1,0,0,875),FPlane(-1,0,0,875),FPlane(0,1,0,425),FPlane(0,-1,0,425),FPlane(0,0,-1,-22),FPlane(0,.6,.8,558.4),FPlane(0,-.6,.8,558.4)};return R;
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPortalGeometry,"Dink.Art.Camera.ExteriorPortalGeometry",DINK_TEST_FLAGS)
bool FDinkPortalGeometry::RunTest(const FString&)
{
    const FVector Pawn(97729.63625545749,37512.61084546293,98.34999561309814);
    const FVector Eye(97704.23270538304,37133.03737537629,221.9567933630771);
    const FTransform Owner(FRotator::ZeroRotator,FVector(97131.61092968748,36920.324198125,0));
    auto R=Rule();DinkCameraPortal::FLimit L;
    TestTrue(TEXT("explicit authored hull contains recorded hollow-shell eye"),R.Inside(Owner.InverseTransformPosition(Eye)));
    TestTrue(TEXT("recorded clear-aperture trajectory has authored camera limit"),DinkCameraPortal::Limit(R,Owner,Pawn,Eye,12,L));
    const FVector Limited=Pawn+(Eye-Pawn)*L.Fraction;
    TestTrue(TEXT("actual scalar is derived from recorded pose, not fixed"),FMath::IsNearlyEqual(400*L.Fraction,106.21042331,.001));
    TestTrue(TEXT("independent world plane clearance"),FMath::IsNearlyEqual(Limited.Y,36920.324198125+479.5+12,1.e-6));
    TestFalse(TEXT("limited endpoint is outside authored hollow interior"),R.Inside(Owner.InverseTransformPosition(Limited)));
    const FRotator Rotation(-18,86.1711,0);const FVector F=Rotation.Vector(),Up=Rotation.RotateVector(FVector::UpVector);
    const FVector Top=Pawn+FVector(0,0,96);double Lift=0;
    TestTrue(TEXT("capped eye has capsule-bounded headroom solution"),DinkCameraHeadroom::MinimumLift(Top,Limited,F,Up,1280./720.,0,.2,96,Lift));
    TestTrue(TEXT("headroom differs from fixed preset"),Lift>50&&Lift<55);
    const FVector Raised=Limited+FVector(0,0,Lift);
    const FVector Delta=Top-Raised;const double Depth=FVector::DotProduct(Delta,F);
    TestTrue(TEXT("actual head depth beyond10cm near plane"),Depth>10);
    TestTrue(TEXT("independent projected capsule top has upper margin"),FMath::IsNearlyEqual(FVector::DotProduct(Delta,Up)*(1280./720.)/Depth,.8,1.e-6));
    TestTrue(TEXT("vertical lift retains explicit exterior side"),L.Outside(Raised));
    TestFalse(TEXT("free outside boom does not acquire portal limit"),DinkCameraPortal::Limit(R,Owner,Pawn,Pawn+F*400,12,L));
    TestFalse(TEXT("a wall outside finite aperture is not guessed as portal"),DinkCameraPortal::Limit(R,Owner,Owner.TransformPosition(FVector(0,600,100)),Owner.TransformPosition(FVector(0,100,200)),12,L));
    TestFalse(TEXT("inside-pawn trajectory is not forced through wall"),DinkCameraPortal::Limit(R,Owner,Owner.TransformPosition(FVector(530,100,100)),Owner.TransformPosition(FVector(530,-100,100)),12,L));
    TestFalse(TEXT("too close to portal for probe clearance is rejected"),DinkCameraPortal::Limit(R,Owner,Owner.TransformPosition(FVector(530,480,100)),Eye,12,L));
    TestTrue(TEXT("unsupported near-portal band is explicitly infeasible"),L.bInfeasible);
    TestFalse(TEXT("near-plane clearance cannot silently put camera inside body"),DinkCameraPortal::Limit(R,Owner,Pawn,Eye,12,L,1000));
    TestTrue(TEXT("infeasible near-plane request is explicit"),L.bInfeasible);
    TestFalse(TEXT("insufficient headroom bound is not accepted"),DinkCameraHeadroom::MinimumLift(Top,Limited,F,Up,1280./720.,0,.2,10,Lift));
    R.Minimum.X=-10;R.Maximum.X=10;
    TestFalse(TEXT("aperture narrower than actual probe diameter is not entered"),DinkCameraPortal::Limit(R,Owner,Owner.TransformPosition(FVector(530,600,100)),Owner.TransformPosition(FVector(530,100,200)),12,L));
    TestTrue(TEXT("too-small aperture is explicitly infeasible"),L.bInfeasible);R=Rule();
    const FTransform Moved(FRotator(0,57,0),FVector(400,-900,0),FVector(2));
    const FVector LocalA=Owner.InverseTransformPosition(Pawn),LocalB=Owner.InverseTransformPosition(Eye);
    TestTrue(TEXT("translated rotated uniformly scaled owner uses same local authority"),DinkCameraPortal::Limit(R,Moved,Moved.TransformPosition(LocalA),Moved.TransformPosition(LocalB),24,L));
    TestTrue(TEXT("scaled exterior clearance exact"),L.Outside(Moved.TransformPosition(LocalA+(LocalB-LocalA)*L.Fraction)));
    TestFalse(TEXT("unsupported nonuniform scale is not approximated"),DinkCameraPortal::Limit(R,FTransform(FRotator::ZeroRotator,FVector::ZeroVector,FVector(1,2,1)),LocalA,LocalB,12,L));
    R.InteriorPlanes.Reset();TestFalse(TEXT("unowned malformed hull rejected"),DinkCameraPortal::Limit(R,Owner,Pawn,Eye,12,L));
    R=Rule();R.Point.X=std::numeric_limits<double>::infinity();TestFalse(TEXT("nonfinite metadata rejected"),R.IsValid());
    return true;
}
