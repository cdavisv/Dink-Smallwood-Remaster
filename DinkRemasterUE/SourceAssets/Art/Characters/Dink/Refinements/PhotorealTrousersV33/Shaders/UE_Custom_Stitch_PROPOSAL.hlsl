// PROPOSAL ONLY. Pixel Custom inputs: SeamMeters float2, BaseNormalWS float3,
// PositionCM float3. Return float3 normalWS, additional float1 StitchMaskOut.
float2 seamDx = ddx(SeamMeters), seamDy = ddy(SeamMeters);
float2 widths = max(abs(seamDx) + abs(seamDy), float2(1e-8,1e-8));
float3 dist = float3(SeamMeters.x, SeamMeters.x + 0.1*seamDx.x, SeamMeters.x + 0.1*seamDy.x);
float3 arc = float3(SeamMeters.y, SeamMeters.y + 0.1*seamDx.y, SeamMeters.y + 0.1*seamDy.y);
float3 x = dist - 0.0025;
float3 lineLo = x - 0.5*widths.x, lineHi = x + 0.5*widths.x;
float3 tl = min(abs(lineLo)/0.0003,1.0), th = min(abs(lineHi)/0.0003,1.0);
float3 pl = sign(lineLo)*0.0003*(tl-tl*tl*tl+0.5*tl*tl*tl*tl);
float3 ph = sign(lineHi)*0.0003*(th-th*th*th+0.5*th*th*th*th);
float3 lineAverage = (ph-pl)/widths.x;
float3 phase = frac(arc/0.003);
float phaseWidth = widths.y/0.003;
float3 phaseLo = phase-0.5*phaseWidth, phaseHi = phase+0.5*phaseWidth;
float3 ql = frac(phaseLo), qh = frac(phaseHi);
float3 rlo = saturate((ql-0.10)/0.17), rhi = saturate((qh-0.10)/0.17);
float3 flo = saturate((ql-0.73)/0.17), fhi = saturate((qh-0.73)/0.17);
float3 jrlo = rlo*rlo*rlo-0.5*rlo*rlo*rlo*rlo;
float3 jrhi = rhi*rhi*rhi-0.5*rhi*rhi*rhi*rhi;
float3 jflo = flo*flo*flo-0.5*flo*flo*flo*flo;
float3 jfhi = fhi*fhi*fhi-0.5*fhi*fhi*fhi*fhi;
float3 integralLo = floor(phaseLo)*0.63 + 0.17*jrlo + clamp(ql-0.27,0.0,0.46) + 0.17*(flo-jflo);
float3 integralHi = floor(phaseHi)*0.63 + 0.17*jrhi + clamp(qh-0.27,0.0,0.46) + 0.17*(fhi-jfhi);
float3 arcAverage = (integralHi-integralLo)/phaseWidth;
float3 h = 9.87*lineAverage*arcAverage;
float3 px = ddx(PositionCM), py = ddy(PositionCM);
float3 base = normalize(BaseNormalWS);
float3 rx = cross(py,base), ry = cross(base,px);
float surfaceDet = dot(px,rx);
float3 gradient = (h.y-h.x)*rx + (h.z-h.x)*ry;
float3 bent = base;
if (abs(surfaceDet)>1e-20)
    bent = normalize(0.1*abs(surfaceDet)*base - 0.008*sign(surfaceDet)*gradient);
StitchMaskOut = h.x/9.87;
return normalize(0.19*bent + 0.81*base);
