#include "DinkTestHelpers.h"
#include "DinkCameraFraming.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCameraMinimumTranslationTest,"Dink.Art.InteriorCamera.MinimumTranslation",DINK_TEST_FLAGS)
bool FDinkCameraMinimumTranslationTest::RunTest(const FString&)
{
    using DinkCameraFraming::FPlane;
    using DinkCameraFraming::FindMinimumTranslation;
    FVector2D Out(99,99);
    TestTrue(TEXT("no constraints needs no translation"),FindMinimumTranslation({},0,Out));
    TestTrue(TEXT("empty solution is zero"),Out.IsNearlyZero());
    TestTrue(TEXT("already feasible negative halfplanes retain origin"),FindMinimumTranslation({{{1,0},-10},{{0,-1},-4}},100,Out));
    TestTrue(TEXT("already feasible point does not drift"),Out.IsNearlyZero());

    // Independent rendered382-door fixture:70 horizontal FOV,16:9,−18pitch,315yaw,
    // LEFT45cm shoulder,240cm arm,+52cm pivot. Intersect all three lower rays with the actual rendered floor at z0.
    // Its southern-most hit needs25.886716cm inward to achieve5cm floor clearance.
    const FVector Body(-183806.0975,393517.23,98);
    const FRotator View(-18,315,0);
    const FVector Forward=View.Vector(),Right=View.RotateVector(FVector(0,1,0)),Up=View.RotateVector(FVector(0,0,1));
    const FVector Eye=Body+FVector(0,0,52)-Forward*240+Right*-45;
    const double TanH=FMath::Tan(FMath::DegreesToRadians(35.));
    double Need=-std::numeric_limits<double>::max();
    for (double Side : {-1.,0.,1.})
    {
        const FVector Ray=Forward+Right*(Side*TanH)-Up*(TanH/(16./9.));
        const FVector Hit=Eye+Ray*(-Eye.Z/Ray.Z);
        Need=FMath::Max(Need,Hit.Y-393595.98+5.);
    }
    TestTrue(TEXT("actual fixture independently predicts25.887cm correction"),FMath::IsNearlyEqual(Need,25.8867164332769,.00001));
    const TArray<FPlane> Actual={{{0,-1},Need},{{-Forward.X,-Forward.Y},180-FVector::DotProduct(Body-Eye,Forward)}};
    TestTrue(TEXT("actual door constraint has a bounded readable solution"),FindMinimumTranslation(Actual,150,Out));
    TestTrue(TEXT("actual minimum is northward25.887cm with no lateral drift"),Out.Equals(FVector2D(0,-Need),.00001));
    TestFalse(TEXT("a25cm cap explicitly rejects the actual floor correction"),FindMinimumTranslation(Actual,25,Out));
    TestTrue(TEXT("infeasible result clears stale prior translation"),Out.IsNearlyZero());

    TestTrue(TEXT("orthogonal corner activates both planes"),FindMinimumTranslation({{{1,0},3},{{0,1},4}},5,Out));
    TestTrue(TEXT("corner minimum is3,4 rather than a greedy overshoot"),Out.Equals(FVector2D(3,4),1.e-6));
    TestFalse(TEXT("corner outside distance cap fails"),FindMinimumTranslation({{{1,0},3},{{0,1},4}},4.99,Out));
    const double C=FMath::Sqrt(.5);
    TestTrue(TEXT("rotated corner works without axis assumptions"),FindMinimumTranslation({{{C,C},3},{{-C,C},4}},6,Out));
    TestTrue(TEXT("rotation preserves closest point and5cm length"),Out.Equals(FVector2D(-C,7*C),1.e-6) && FMath::IsNearlyEqual(Out.Size(),5.,1.e-6));
    TestTrue(TEXT("scaled duplicated and redundant planes do not change minimum"),FindMinimumTranslation({{{1000,0},3000},{{0,.02},.08},{{1,0},1},{{2,0},6},{{1,1},0}},8,Out));
    TestTrue(TEXT("normal scale does not change solution"),Out.Equals(FVector2D(3,4),1.e-6));
    TestTrue(TEXT("finite extreme normal scales remain numerically usable"),FindMinimumTranslation({{{2.e200,0},6.e200},{{0,2.e-200},8.e-200}},8,Out));
    TestTrue(TEXT("extreme scale still gives3,4"),Out.Equals(FVector2D(3,4),1.e-6));
    TestTrue(TEXT("a narrow nearly parallel wedge keeps its valid intersection"),FindMinimumTranslation({{{1,0},0},{{-1,1.e-6},.0001}},150,Out));
    TestTrue(TEXT("near-parallel wedge minimum is0,100"),Out.Equals(FVector2D(0,100),.0001));
    TestFalse(TEXT("opposing parallel constraints expose an empty feasible set"),FindMinimumTranslation({{{1,0},1},{{-1,0},0}},100,Out));
    TestFalse(TEXT("oblique three-plane contradiction is rejected"),FindMinimumTranslation({{{1,0},3},{{0,1},4},{{-1,-1},-6}},100,Out));
    TestTrue(TEXT("zero-normal tautologies are harmless"),FindMinimumTranslation({{{0,0},0},{{0,0},-3}},0,Out));
    TestFalse(TEXT("positive zero-normal constraint is invalid"),FindMinimumTranslation({{{0,0},1}},100,Out));

    const double NaN=std::numeric_limits<double>::quiet_NaN(),Inf=std::numeric_limits<double>::infinity();
    TestFalse(TEXT("negative maximum is invalid"),FindMinimumTranslation({},-1,Out));
    TestFalse(TEXT("infinite maximum is invalid"),FindMinimumTranslation({},Inf,Out));
    TestFalse(TEXT("NaN maximum is invalid"),FindMinimumTranslation({},NaN,Out));
    TestFalse(TEXT("NaN normal is invalid"),FindMinimumTranslation({{{NaN,1},0}},100,Out));
    TestFalse(TEXT("infinite normal is invalid"),FindMinimumTranslation({{{1,Inf},0}},100,Out));
    TestFalse(TEXT("NaN minimum is invalid"),FindMinimumTranslation({{{1,0},NaN}},100,Out));
    TestFalse(TEXT("infinite minimum is invalid"),FindMinimumTranslation({{{1,0},-Inf}},100,Out));
    TestTrue(TEXT("all rejected inputs leave a neutral output"),Out.IsNearlyZero());
    return true;
}
