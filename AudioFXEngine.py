import json
import math

try:
    import numpy as np
except ImportError:
    np = None

try:
    import librosa
except Exception:
    librosa = None

try:
    from scipy.io import wavfile
    from scipy import signal
except Exception:
    wavfile = None
    signal = None


class AudioFXEngine:
    """
    Audio analysis + state-machine sequence builder for ArcadeCommander.
    Outputs a JSON-compatible sequence with Entrance/Main/Exit phases.
    """

    def __init__(
        self,
        sample_rate=44100,
        hop_length=512,
        n_fft=2048,
        bass_range=(20, 250),
        mid_range=(250, 2000),
        treble_range=(2000, 8000),
    ):
        if np is None:
            raise ImportError("numpy is required for AudioFXEngine.")
        if librosa is None and wavfile is None:
            raise ImportError("Install librosa or scipy to load wav files.")
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.n_fft = n_fft
        self.bass_range = bass_range
        self.mid_range = mid_range
        self.treble_range = treble_range

    def load_audio(self, path):
        if librosa is not None:
            y, sr = librosa.load(path, sr=self.sample_rate, mono=True)
            return y.astype(np.float32), sr
        sr, data = wavfile.read(path)
        if data.ndim > 1:
            data = data.mean(axis=1)
        if data.dtype.kind in ("i", "u"):
            max_val = np.iinfo(data.dtype).max
            y = data.astype(np.float32) / float(max_val)
        else:
            y = data.astype(np.float32)
            m = np.max(np.abs(y)) if len(y) else 1.0
            if m > 1.0:
                y = y / m
        if self.sample_rate and sr != self.sample_rate and signal is not None:
            target_len = int(len(y) * (self.sample_rate / float(sr)))
            y = signal.resample(y, target_len)
            sr = self.sample_rate
        return y, sr

    def normalize_series(self, arr):
        if arr is None or len(arr) == 0:
            return []
        a = np.asarray(arr, dtype=np.float32)
        amin = float(np.min(a))
        amax = float(np.max(a))
        if math.isclose(amax, amin):
            return [0.0 for _ in a]
        return ((a - amin) / (amax - amin)).astype(np.float32).tolist()

    def _stft_mag(self, y):
        if librosa is not None:
            stft = librosa.stft(y, n_fft=self.n_fft, hop_length=self.hop_length)
            return np.abs(stft)
        # fallback numpy STFT
        win = np.hanning(self.n_fft)
        frames = []
        for start in range(0, len(y) - self.n_fft, self.hop_length):
            frame = y[start : start + self.n_fft] * win
            frames.append(np.fft.rfft(frame))
        if not frames:
            return np.zeros((self.n_fft // 2 + 1, 0), dtype=np.float32)
        return np.abs(np.stack(frames, axis=1))

    def _rms(self, y):
        if librosa is not None:
            return librosa.feature.rms(y=y, frame_length=self.n_fft, hop_length=self.hop_length)[0]
        if len(y) < self.n_fft:
            return np.array([], dtype=np.float32)
        rms = []
        for start in range(0, len(y) - self.n_fft, self.hop_length):
            frame = y[start : start + self.n_fft]
            rms.append(float(np.sqrt(np.mean(frame * frame))))
        return np.asarray(rms, dtype=np.float32)

    def _freq_bins(self, mag, sr):
        freqs = np.fft.rfftfreq(self.n_fft, d=1.0 / sr)

        def band_energy(lo, hi):
            idx = (freqs >= lo) & (freqs < hi)
            if not np.any(idx):
                return np.zeros(mag.shape[1], dtype=np.float32)
            return np.mean(mag[idx, :], axis=0)

        bass = band_energy(*self.bass_range)
        mid = band_energy(*self.mid_range)
        treble = band_energy(*self.treble_range)
        return bass, mid, treble

    def _peak_pick(self, x, thresh=0.15, min_gap=4):
        peaks = []
        last = -min_gap
        for i in range(1, len(x) - 1):
            if i - last < min_gap:
                continue
            if x[i] > thresh and x[i] >= x[i - 1] and x[i] >= x[i + 1]:
                peaks.append(i)
                last = i
        return peaks

    def _onsets_beats(self, y, sr, rms):
        if librosa is not None:
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr, hop_length=self.hop_length)
            _, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=self.hop_length)
            return onset_frames.tolist(), beat_frames.tolist()
        # fallback: use rms peaks
        rms_n = self.normalize_series(rms)
        onsets = self._peak_pick(rms_n, thresh=0.35, min_gap=3)
        beats = self._peak_pick(rms_n, thresh=0.55, min_gap=6)
        return onsets, beats

    def analyze_wav(self, path):
        y, sr = self.load_audio(path)
        rms = self._rms(y)
        mag = self._stft_mag(y)
        bass, mid, treble = self._freq_bins(mag, sr)
        onsets, beats = self._onsets_beats(y, sr, rms)
        return {
            "sr": sr,
            "hop_length": self.hop_length,
            "frame_time": float(self.hop_length) / float(sr),
            "rms": rms.tolist(),
            "bass": bass.tolist(),
            "mid": mid.tolist(),
            "treble": treble.tolist(),
            "onsets": onsets,
            "beats": beats,
        }

    def build_sequence(self, analysis, entrance_sec=1.0, exit_sec=1.0, loop_main=True):
        rms = self.normalize_series(analysis.get("rms", []))
        bass = self.normalize_series(analysis.get("bass", []))
        mid = self.normalize_series(analysis.get("mid", []))
        treble = self.normalize_series(analysis.get("treble", []))
        onsets = set(analysis.get("onsets", []))
        beats = set(analysis.get("beats", []))
        frame_time = float(analysis.get("frame_time", 0.0))
        frame_count = min(len(rms), len(bass), len(mid), len(treble))
        if frame_count == 0:
            return {
                "meta": {"frame_time": frame_time, "frames": 0},
                "entrance": {"loop": False, "frames": []},
                "main": {"loop": loop_main, "frames": []},
                "exit": {"loop": False, "frames": []},
            }

        entrance_frames = int(max(0.0, entrance_sec) / frame_time) if frame_time > 0 else 0
        exit_frames = int(max(0.0, exit_sec) / frame_time) if frame_time > 0 else 0
        entrance_frames = min(entrance_frames, frame_count)
        exit_frames = min(exit_frames, frame_count - entrance_frames)

        def make_frame(i, fade=1.0):
            return {
                "t": round(i * frame_time, 4),
                "brightness": round(rms[i] * fade, 4),
                "bass": round(bass[i] * fade, 4),
                "mid": round(mid[i] * fade, 4),
                "treble": round(treble[i] * fade, 4),
                "onset": i in onsets,
                "beat": i in beats,
            }

        entrance = []
        for i in range(entrance_frames):
            fade = (i + 1) / float(max(1, entrance_frames))
            entrance.append(make_frame(i, fade))

        main = []
        for i in range(entrance_frames, frame_count - exit_frames):
            main.append(make_frame(i, 1.0))

        exit_seq = []
        for j, i in enumerate(range(frame_count - exit_frames, frame_count)):
            fade = 1.0 - (j + 1) / float(max(1, exit_frames))
            exit_seq.append(make_frame(i, fade))

        return {
            "meta": {
                "frame_time": frame_time,
                "frames": frame_count,
                "entrance_frames": entrance_frames,
                "exit_frames": exit_frames,
            },
            "entrance": {"loop": False, "frames": entrance},
            "main": {"loop": loop_main, "frames": main},
            "exit": {"loop": False, "frames": exit_seq},
        }

    def to_json(self, sequence):
        return json.dumps(sequence, indent=2)

