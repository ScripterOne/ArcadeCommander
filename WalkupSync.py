import time
import json

try:
    import pygame
except Exception:
    pygame = None


class WalkupSyncController:
    """
    Synchronizes WAV playback with an LED animation service.
    - Entrance phase ends at intro_duration.
    - Main phase runs until exit trigger or audio ends.
    - Exit phase triggers on pause/stop.
    """

    def __init__(self, led_sender, sequence, intro_duration, heartbeat_hz=30):
        if pygame is None:
            raise ImportError("pygame is required for WalkupSyncController.")
        self.led_sender = led_sender
        self.sequence = sequence or {}
        self.intro_duration = max(0.0, float(intro_duration))
        self.heartbeat_hz = max(1, int(heartbeat_hz))
        self._start_time = None
        self._paused = False
        self._stop_requested = False
        self._last_phase = None

    def load(self, wav_path):
        pygame.mixer.init()
        pygame.mixer.music.load(wav_path)
        self._duration = pygame.mixer.Sound(wav_path).get_length()

    def play(self):
        self._stop_requested = False
        pygame.mixer.music.play()
        self._start_time = time.time()
        self._paused = False
        self._run_loop()

    def pause(self):
        if not self._paused:
            pygame.mixer.music.pause()
            self._paused = True
            self._trigger_exit()

    def resume(self):
        if self._paused:
            pygame.mixer.music.unpause()
            self._paused = False
            self._start_time = time.time() - pygame.mixer.music.get_pos() / 1000.0

    def stop(self):
        pygame.mixer.music.stop()
        self._stop_requested = True
        self._trigger_exit()

    def _current_time(self):
        return pygame.mixer.music.get_pos() / 1000.0

    def _phase_for_time(self, t):
        if t <= self.intro_duration:
            return "entrance"
        if self._stop_requested or self._paused:
            return "exit"
        return "main"

    def _trigger_exit(self):
        self._send_state("exit", 0.0)

    def _send_state(self, phase, t):
        payload = {
            "phase": phase,
            "t": t,
            "timestamp": time.time(),
        }
        self.led_sender(payload)

    def _run_loop(self):
        interval = 1.0 / float(self.heartbeat_hz)
        while pygame.mixer.music.get_busy() and not self._stop_requested:
            t = self._current_time()
            phase = self._phase_for_time(t)
            if phase != self._last_phase:
                self._last_phase = phase
            self._send_state(phase, t)
            time.sleep(interval)
        # If playback ended naturally, ensure exit runs
        if not self._stop_requested:
            self._send_state("exit", self._current_time())

    @property
    def duration(self):
        return getattr(self, "_duration", 0.0)

