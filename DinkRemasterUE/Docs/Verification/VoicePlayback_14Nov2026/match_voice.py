"""Find which voice clips occur in a recording: normalised cross-correlation of envelopes.
usage: match_voice.py <recording.wav> <clip.mp3>...
Prints, per clip, the best match time and score (1.0 = identical waveform shape)."""
import subprocess
import sys
import numpy as np

RATE = 16000


def decode(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(RATE), '-f', 's16le', '-'],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def ncc(signal, template):
    n = len(template)
    if len(signal) < n:
        return 0.0, 0
    size = 1 << int(np.ceil(np.log2(len(signal) + n)))
    t = template - template.mean()
    corr = np.fft.irfft(np.fft.rfft(signal, size) * np.conj(np.fft.rfft(t, size)), size)[:len(signal) - n + 1]
    c1 = np.concatenate([[0], np.cumsum(signal)])
    c2 = np.concatenate([[0], np.cumsum(signal * signal)])
    s1 = c1[n:] - c1[:-n]
    s2 = c2[n:] - c2[:-n]
    var = np.maximum(s2 - s1 * s1 / n, 1e-9)
    score = corr / (np.sqrt(var) * np.linalg.norm(t) + 1e-9)
    i = int(np.argmax(score))
    return float(score[i]), i


recording = decode(sys.argv[1])
print('recording %.1f s, rms %.4f, peak %.3f' % (len(recording) / RATE, np.sqrt(np.mean(recording ** 2)), np.abs(recording).max()))
for clip in sys.argv[2:]:
    score, at = ncc(recording, decode(clip))
    print('%-40s score %.3f at %6.2f s' % (clip.rsplit('/', 1)[-1], score, at / RATE))
