import numpy as np
import math
from dataclasses import dataclass, field
from instrument.instrument import Instrument, Voice  # ton module


@dataclass
class TB303Params:
    # Oscillateur
    waveform: str = "saw"          # "saw" ou "square"
    pulse_width: float = 0.5       # Pour square uniquement (0.0–1.0)

    # Filtre
    cutoff: float = 800.0          # Fréquence de coupure en Hz
    resonance: float = 0.8         # Résonance 0.0–1.0 (attention > 0.9 = auto-oscillation)
    env_mod: float = 0.5           # Intensité de l'enveloppe sur le filtre (0.0–1.0)

    # Enveloppe filtre
    attack: float = 0.005          # secondes
    decay: float = 0.2             # secondes

    # Accent
    accent: bool = False
    accent_amount: float = 0.7     # Boost volume + filtre si accent


class TB303Instrument(Instrument):
    def __init__(self, params: TB303Params = None, **kwargs):
        super().__init__(**kwargs)
        self.params = params or TB303Params()

    # ─── Oscillateur ──────────────────────────────────────────────
    def _oscillator(self, phases: np.ndarray) -> np.ndarray:
        if self.params.waveform == "saw":
            # Dent de scie : rampe de +1 à -1
            return 1.0 - (phases % (2 * math.pi)) / math.pi
        else:
            # Square avec pulse width réglable
            pw = self.params.pulse_width * 2 * math.pi
            return np.where((phases % (2 * math.pi)) < pw, 1.0, -1.0)

    # ─── Filtre Moog ladder (approximation numérique) ─────────────
    def _moog_filter(self, signal: np.ndarray, cutoff_hz: float, resonance: float) -> np.ndarray:
        """
        Approximation du filtre Moog 4 pôles.
        cutoff_hz : fréquence de coupure
        resonance : 0.0 (aucune) → ~1.0 (auto-oscillation)
        """
        sr = self.sample_rate
        f = 2.0 * math.sin(math.pi * min(cutoff_hz, sr * 0.45) / sr)
        k = 2.0 * resonance  # feedback

        # 4 états du filtre (1 pôle chacun)
        s = [0.0, 0.0, 0.0, 0.0]
        out = np.empty_like(signal)

        for i, x in enumerate(signal):
            # Feedback
            x_fb = x - k * s[3]
            # 4 pôles en cascade (filtre passe-bas du 1er ordre)
            s[0] = s[0] + f * (np.tanh(x_fb) - np.tanh(s[0]))
            s[1] = s[1] + f * (s[0] - s[1])
            s[2] = s[2] + f * (s[1] - s[2])
            s[3] = s[3] + f * (s[2] - s[3])
            out[i] = s[3]

        return out

    # ─── Enveloppe filtre ─────────────────────────────────────────
    def _filter_envelope(self, frames: int, voice: Voice) -> np.ndarray:
        """Génère l'enveloppe Attack/Decay qui module le cutoff."""
        p = self.params
        sr = self.sample_rate
        elapsed = 0.0  # simplifié : on suppose début de note

        attack_samples  = max(1, int(p.attack * sr))
        decay_samples   = max(1, int(p.decay  * sr))

        env = np.zeros(frames)
        for i in range(frames):
            if i < attack_samples:
                env[i] = i / attack_samples
            else:
                decay_pos = i - attack_samples
                env[i] = max(0.0, 1.0 - decay_pos / decay_samples)

        return env

    # ─── Synthèse principale ──────────────────────────────────────
    def synthesize(self, voice: Voice, phases: np.ndarray) -> np.ndarray:
        p = self.params
        frames = len(phases)

        # 1. Oscillateur
        raw = self._oscillator(phases)

        # 2. Enveloppe du filtre → module la fréquence de coupure
        env = self._filter_envelope(frames, voice)
        accent_boost = p.accent_amount if p.accent else 0.0
        max_cutoff = 8000.0
        cutoff_mod = p.cutoff + env * p.env_mod * (max_cutoff - p.cutoff) * (1.0 + accent_boost)

        # 3. Filtre passe-bas résonant sample par sample
        # On utilise la valeur moyenne du cutoff par bloc pour simplifier
        # (idéalement il faudrait interpoler sample par sample)
        avg_cutoff = float(np.mean(cutoff_mod))
        filtered = self._moog_filter(raw, avg_cutoff, p.resonance)

        # 4. Accent → boost du volume
        if p.accent:
            filtered *= (1.0 + accent_boost * 0.5)

        return filtered.astype(np.float32)