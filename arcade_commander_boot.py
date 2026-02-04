import numpy as np
import wave

# =========================
# CONFIG
# =========================
SAMPLE_RATE = 44100
DURATION = 2.6
OUTPUT_FILE = "arcade_commander_boot.wav"

# Time
t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), endpoint=False)

# =========================
# SUB RISE (Dolby-style ramp)
# =========================
start_freq = 55.0
end_freq = 220.0
freq_curve = start_freq * (end_freq / start_freq) ** (t / DURATION)

sub = np.sin(2 * np.pi * freq_curve * t)

# Exponential volume ramp
volume_ramp = np.clip((t / 1.8) ** 2.2, 0, 1)
sub *= volume_ramp * 0.6

# =========================
# HARMONIC BLOOM
# =========================
harmonic_2 = np.sin(2 * np.pi * freq_curve * 2 * t) * 0.25
harmonic_3 = np.sin(2 * np.pi * freq_curve * 3 * t) * 0.18

bloom_gate = np.clip((t - 1.0) / 0.8, 0, 1)
bloom = (harmonic_2 + harmonic_3) * bloom_gate

# =========================
# PUNCH HIT
# =========================
punch_time = 2.15
punch_len = 0.12
punch_env = np.exp(-((t - punch_time) / punch_len) ** 2)

punch_low = np.sin(2 * np.pi * 90 * t) * punch_env * 1.1
punch_click = np.sin(2 * np.pi * 2400 * t) * punch_env * 0.25

punch = punch_low + punch_click

# =========================
# FINAL MIX
# =========================
mix = sub + bloom + punch

# Soft limiter
mix = np.tanh(mix * 1.3)

# Normalize
mix /= np.max(np.abs(mix))

# =========================
# WRITE WAV
# =========================
with wave.open(OUTPUT_FILE, "w") as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(SAMPLE_RATE)
    audio = (mix * 32767).astype(np.int16)
    f.writeframes(audio.tobytes())

print(f"Created {OUTPUT_FILE}")
