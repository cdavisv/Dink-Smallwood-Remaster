#include "Hardness/DinkCanonicalSurface.h"
#include <iostream>
int main(int Argc, char**)
{
    std::vector<DinkCanonicalSurface::Triangle> Triangles;
    std::array<std::uint8_t,38> Record;
    while (std::cin.read(reinterpret_cast<char*>(Record.data()), Record.size()))
    {
        DinkCanonicalSurface::Triangle Triangle;
        unsigned Offset=0;
        for(auto& Point:Triangle.Points) for(float& Value:Point)
        {
            std::uint32_t Bits=0;
            for(unsigned Byte=0;Byte<4;++Byte) Bits|=std::uint32_t(Record[Offset++])<<(8*Byte);
            std::memcpy(&Value,&Bits,sizeof(Value));
        }
        Triangle.Material=std::uint16_t(Record[36])|(std::uint16_t(Record[37])<<8);
        Triangles.push_back(Triangle);
    }
    if(std::cin.gcount()!=0)return 2;
    const auto Bytes=DinkCanonicalSurface::Bytes(Triangles,Argc == 1);
    std::cout.write(reinterpret_cast<const char*>(Bytes.data()),Bytes.size());
}
