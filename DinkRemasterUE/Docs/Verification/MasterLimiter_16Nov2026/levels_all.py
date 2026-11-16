"""Output level per window of a recorded run (SDL disk driver, F32LE, 6 ch, 48 kHz), ALL channels.
usage: levels_all.py <raw> [window s]"""
import sys, numpy as np
x = np.memmap(sys.argv[1], dtype='<f4', mode='r'); x = x[:len(x)//6*6].reshape(-1, 6)
step = float(sys.argv[2]) if len(sys.argv) > 2 else 30; R = 48000; ceil = 10**(-1.5/20)
print(f"# {len(x)/R:.1f} s recorded; ceiling -1.5 dBFS = {ceil:.6f} linear; columns: window start, rms (front pair), peak over all 6 channels, samples above -1.5 dBFS (any channel), samples >= 0.999")
tot_over = 0; worst = 0.0
for t0 in np.arange(0, len(x)/R, step):
    s = np.asarray(x[int(t0*R):int((t0+step)*R)]); a = np.abs(s)
    pk = a.max() if a.size else 0; worst = max(worst, pk)
    rms = 10*np.log10(max(np.mean(s[:, :2]**2), 1e-12))
    n = int((a > ceil + 1e-6).sum()); tot_over += n
    print(f"{t0:6.0f}s rms {rms:6.1f} peak {20*np.log10(max(pk,1e-9)):7.2f} dBFS  >-1.5dBFS: {n:7d}  >=0dBFS: {int((a>=0.999).sum()):6d}")
print(f"# whole run: peak {20*np.log10(max(worst,1e-9)):.3f} dBFS, {tot_over} samples above the ceiling")
