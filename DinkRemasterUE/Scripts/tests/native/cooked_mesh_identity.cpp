#include "Hardness/DinkCookedMeshIdentity.h"
#include <cassert>
#include <iostream>
#include <utility>
using namespace DinkCookedMeshIdentity;
int main()
{
    Snapshot Source;
    Source.Particles={{{0,0,0}},{{0x3f800000,0,0}},{{0,0x3f800000,0}},{{0,0,0}}};
    Source.Faces={{{{0,1,2}},4,101},{{{1,2,3}},7,-1},{{{0,1,2}},4,101}};
    auto Reordered=Source;std::swap(Reordered.Faces[0],Reordered.Faces[1]);
    assert(SameAssociations(Source,Reordered));assert(!(Source==Reordered));
    auto Cyclic=Source;Cyclic.Faces[0].Indices={1,2,0};
    assert(SameAssociations(Source,Cyclic));assert(!(Source==Cyclic));
    auto Changed=Source;Changed.Particles[0][0]=0x80000000u;assert(!SameAssociations(Source,Changed)); // signed zero
    Changed=Source;Changed.Faces[0].Indices={0,2,1};assert(!SameAssociations(Source,Changed)); // winding
    Changed=Source;Changed.Faces[0].Indices[0]=3;assert(!SameAssociations(Source,Changed)); // duplicate-position vertex ID
    Changed=Source;Changed.Faces[0].Material++;assert(!SameAssociations(Source,Changed));
    Changed=Source;Changed.Faces[0].ExternalFace++;assert(!SameAssociations(Source,Changed));
    Changed=Source;Changed.Faces.pop_back();assert(!SameAssociations(Source,Changed));
    Changed=Source;Changed.LargeIndices=true;assert(!SameAssociations(Source,Changed));
    Changed=Source;Changed.Faces[0].Indices[0]=999;assert(!SameAssociations(Source,Changed));
    assert(!SameAssociations(Snapshot{},Snapshot{}));
    const auto Admitted=Admit(Source,Reordered);assert(Admitted);assert(MatchesOrdered(Admitted,Source,Reordered));
    assert(!MatchesOrdered(Admitted,Source,Source)); // own reordering AFTER freeze refuses
    Changed=Source;Changed.Faces[0].Material++;
    const auto Failed=Admit(Source,Changed);assert(!Failed);
    assert(!MatchesOrdered(Failed,Source,Changed)); // refused initial association never validates itself
    const auto Encoded=Associations(Source);assert(Encoded.size()==3&&Encoded[0].size()==18);
    std::cout<<"PASS exact particles/indices/material/face associations and independent ordered epoch guards\n";
}
