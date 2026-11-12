#pragma once
#include <algorithm>
#include <vector>
namespace DinkHardness
{
/** Actual enumerated world authority must match supplied unique paths exactly. */
template<class Path> bool ExactAuthorityPaths(std::vector<Path> Actual,std::vector<Path> Supplied)
{
    if(Actual.empty())return false;
    std::sort(Actual.begin(),Actual.end());std::sort(Supplied.begin(),Supplied.end());
    return std::adjacent_find(Actual.begin(),Actual.end())==Actual.end() &&
        std::adjacent_find(Supplied.begin(),Supplied.end())==Supplied.end() && Actual==Supplied;
}
}
