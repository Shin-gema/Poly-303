import numpy as np
import math
import time
from dataclasses import dataclass, field
from typing import Dict, Any
from instrument.instrument import Instrument, Voice  # ton module


@dataclass
class TB303Parameter:
    """Classe unifiée pour gérer les paramètres TB303, leur sélection et leurs contraintes."""
    
    # ─── Données des paramètres ───────────────────────────────────
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
    sustain: float = 0.7           # niveau de sustain (0.0–1.0)
    release: float = 0.3           # secondes

    # Accent
    accent: bool = False
    accent_amount: float = 0.7     # Boost volume + filtre si accent

    # ─── Sélection actuelle pour édition ──────────────────────────
    selected_component: str = "filter"      # "filter", "oscillator", "accent", "envelope"
    selected_parameter: str = "cutoff"      # Ex: "cutoff", "resonance", "attack", "decay", etc.

    # ─── Dictionnaire des paramètres éditables (constraints) ──────
    _editable_params: Dict[str, Dict[str, Dict[str, Any]]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        """Initialise le dictionnaire des paramètres éditables après la création."""
        self._editable_params = {
            "filter": {
                "cutoff": {"min": 20.0, "max": 8000.0, "type": "float", "step": 50.0},
                "resonance": {"min": 0.0, "max": 1.0, "type": "float", "step": 0.05},
                "env_mod": {"min": 0.0, "max": 1.0, "type": "float", "step": 0.05},
            },
            "oscillator": {
                "waveform": {"min": 0.0, "max": 1.0, "type": "str", "step": 1.0},
                "pulse_width": {"min": 0.0, "max": 1.0, "type": "float", "step": 0.05},
            },
            "envelope": {
                "attack": {"min": 0.0, "max": 1.0, "type": "float", "step": 0.01},
                "decay": {"min": 0.0, "max": 1.0, "type": "float", "step": 0.01},
                "sustain": {"min": 0.0, "max": 1.0, "type": "float", "step": 0.05},
                "release": {"min": 0.0, "max": 1.0, "type": "float", "step": 0.01},
            },
            "accent": {
                "accent": {"min": 0.0, "max": 1.0, "type": "bool", "step": 1.0},
                "accent_amount": {"min": 0.0, "max": 1.0, "type": "float", "step": 0.05},
            },
        }

    # ─── Méthodes de sélection et navigation ───────────────────────
    def get_full_name(self) -> str:
        """Retourne le chemin complet ex: 'filter/cutoff'"""
        return f"{self.selected_component}/{self.selected_parameter}"

    def set_from_string(self, path: str) -> None:
        """Définit la sélection à partir d'une chaîne comme 'filter/attack'"""
        parts = path.split("/")
        if len(parts) == 2:
            self.selected_component, self.selected_parameter = parts

    def get_components_list(self) -> list:
        """Retourne la liste des composants disponibles."""
        return list(self._editable_params.keys())

    def get_parameters_for_component(self, component: str) -> list:
        """Retourne la liste des paramètres d'un composant."""
        if component in self._editable_params:
            return list(self._editable_params[component].keys())
        return []

    def get_parameter_info(self, component: str, parameter: str) -> Dict[str, Any]:
        """Retourne les infos d'un paramètre (min, max, type, step)."""
        if component in self._editable_params and parameter in self._editable_params[component]:
            return self._editable_params[component][parameter]
        return None

    def cycle_component(self, direction: int = 1):
        """Cycle vers le composant suivant/précédent."""
        components = self.get_components_list()
        current_idx = components.index(self.selected_component) if self.selected_component in components else 0
        next_idx = (current_idx + direction) % len(components)
        self.selected_component = components[next_idx]
        # Reset au premier paramètre du nouveau composant
        self.selected_parameter = self.get_parameters_for_component(self.selected_component)[0]
        print(f"Selected component: {self.selected_component}, parameter: {self.selected_parameter}")

    def cycle_parameter(self, direction: int = 1):
        """Cycle vers le paramètre suivant/précédent du composant actuel."""
        params = self.get_parameters_for_component(self.selected_component)
        if not params:
            return
        current_idx = params.index(self.selected_parameter) if self.selected_parameter in params else 0
        next_idx = (current_idx + direction) % len(params)
        self.selected_parameter = params[next_idx]
        print(f"Selected component: {self.selected_component}, parameter: {self.selected_parameter}")

    # ─── Méthodes de getter/setter des valeurs ────────────────────
    def get_parameter_value(self) -> float:
        """Retourne la valeur actuelle du paramètre sélectionné."""
        return getattr(self, self.selected_parameter, 0.0)

    def get_parameter_position(self) -> float:
        """Retourne la position d'encodeur du paramètre sélectionné (convertie si nécessaire)."""
        value = self.get_parameter_value()
        info = self.get_parameter_info(self.selected_component, self.selected_parameter)
        
        if info and info["type"] == "str":
            # Pour les paramètres string (ex: waveform), retourner un indice
            if self.selected_parameter == "waveform":
                return 0.0 if value == "saw" else 1.0
            return 0.0
        elif info and info["type"] == "bool":
            return 1.0 if value else 0.0
        
        # Pour float et int, retourner la valeur normalisée dans la plage
        if info:
            range_size = info["max"] - info["min"]
            if range_size > 0:
                return (value - info["min"]) / range_size * 100.0
        return float(value)

    def set_parameter_value(self, value: float) -> None:
        """Définit la valeur du paramètre sélectionné."""
        info = self.get_parameter_info(self.selected_component, self.selected_parameter)
        if info:
            if info["type"] == "str":
                # Pour string, value est un indice
                if self.selected_parameter == "waveform":
                    setattr(self, self.selected_parameter, "saw" if value < 0.5 else "square")
            elif info["type"] == "bool":
                setattr(self, self.selected_parameter, value > 0.5)
            else:
                # Pour float et int
                clamped = max(info["min"], min(info["max"], value))
                setattr(self, self.selected_parameter, clamped)
        print(f"Set {self.get_full_name()} to {getattr(self, self.selected_parameter)}")


class TB303Instrument(Instrument):
    def __init__(self, params: TB303Parameter = None, **kwargs):
        super().__init__(**kwargs)
        self.params = params or TB303Parameter()

    # ─── Délégation des méthodes de paramètres ────────────────────
    def get_editable_params(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Retourne le dictionnaire des paramètres éditables."""
        return self.params._editable_params

    def get_components_list(self) -> list:
        """Retourne la liste des composants disponibles."""
        return self.params.get_components_list()

    def get_parameters_for_component(self, component: str) -> list:
        """Retourne la liste des paramètres d'un composant."""
        return self.params.get_parameters_for_component(component)

    def get_parameter_info(self, component: str, parameter: str) -> Dict[str, Any]:
        """Retourne les infos d'un paramètre."""
        return self.params.get_parameter_info(component, parameter)

    def cycle_component(self, direction: int = 1):
        """Cycle vers le composant suivant/précédent."""
        self.params.cycle_component(direction)

    def cycle_parameter(self, direction: int = 1):
        """Cycle vers le paramètre suivant/précédent du composant actuel."""
        self.params.cycle_parameter(direction)

    def get_parameter_value(self) -> float:
        """Retourne la valeur actuelle du paramètre sélectionné."""
        return self.params.get_parameter_value()

    def get_parameter_position(self) -> float:
        """Retourne la position d'encodeur du paramètre sélectionné (convertie si nécessaire)."""
        return self.params.get_parameter_position()

    def set_parameter_value(self, value: float) -> None:
        """Définit la valeur du paramètre sélectionné."""
        self.params.set_parameter_value(value)

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
        """Génère l'enveloppe ADSR complète qui module le cutoff."""
        p = self.params
        sr = self.sample_rate
        now = time.time()
        elapsed_time = now - voice.start_time
        time_remaining = voice.duration - elapsed_time

        attack_time = p.attack
        decay_time = p.decay
        adsr_time = attack_time + decay_time
        release_time = p.release

        env = np.zeros(frames)
        for i in range(frames):
            # Position en secondes pour cet échantillon
            sample_time = elapsed_time + (i / sr)
            time_until_end = voice.duration - sample_time

            if sample_time < attack_time:
                # Attack: 0 → 1
                env[i] = sample_time / attack_time
            elif sample_time < adsr_time:
                # Decay: 1 → sustain level
                decay_pos = sample_time - attack_time
                env[i] = 1.0 - (decay_pos / decay_time) * (1.0 - p.sustain)
            elif time_until_end > release_time:
                # Sustain: reste au niveau sustain
                env[i] = p.sustain
            else:
                # Release: sustain → 0
                if release_time > 0:
                    release_pos = release_time - time_until_end
                    env[i] = p.sustain * max(0.0, 1.0 - release_pos / release_time)

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