"""
Sound manager using pyglet's built-in synthesizer.
No audio files needed — all sounds are generated from waveforms.
Lightweight enough for Raspberry Pi.
"""
from pyglet.media import StaticSource
from pyglet.media.synthesis import (
    Sine, Square, Triangle, Sawtooth, WhiteNoise,
    ADSREnvelope, LinearDecayEnvelope, FlatEnvelope,
)


def _make(source):
    """Convert a synth source to a StaticSource for repeated playback."""
    return StaticSource(source)


class SoundManager:
    """Generates and caches all game sounds from synthesized waveforms."""

    def __init__(self):
        self.enabled = True
        self._cache = {}
        self._build_sounds()

    def _build_sounds(self):
        """Generate all game sounds."""
        # Blaster fire — short sharp square wave, pew!
        self._cache["fire"] = _make(
            Square(
                duration=0.08,
                frequency=880,
                envelope=LinearDecayEnvelope(peak=0.3),
            )
        )

        # Blaster hit — lower thud
        self._cache["hit"] = _make(
            Square(
                duration=0.12,
                frequency=220,
                envelope=LinearDecayEnvelope(peak=0.4),
            )
        )

        # Player death — descending noise burst
        self._cache["death"] = _make(
            WhiteNoise(
                duration=0.4,
                envelope=LinearDecayEnvelope(peak=0.35),
            )
        )

        # Wall bounce — soft tick
        self._cache["bounce"] = _make(
            Triangle(
                duration=0.03,
                frequency=600,
                envelope=LinearDecayEnvelope(peak=0.15),
            )
        )

        # Menu select — bright chirp
        self._cache["menu_select"] = _make(
            Sine(
                duration=0.1,
                frequency=1200,
                envelope=ADSREnvelope(
                    attack=0.01, decay=0.05, release=0.04,
                    sustain_amplitude=0.3,
                ),
            )
        )

        # Game over — low ominous tone
        self._cache["game_over"] = _make(
            Sawtooth(
                duration=0.8,
                frequency=110,
                envelope=LinearDecayEnvelope(peak=0.3),
            )
        )

        # Win — bright tone
        self._cache["win"] = _make(
            Sine(
                duration=0.3,
                frequency=880,
                envelope=ADSREnvelope(
                    attack=0.02, decay=0.1, release=0.15,
                    sustain_amplitude=0.3,
                ),
            )
        )

        # Suck — low descending sine, ship entering black hole gravity well
        self._cache["suck"] = _make(
            Sine(
                duration=0.6,
                frequency=90,
                envelope=ADSREnvelope(
                    attack=0.05, decay=0.2, release=0.3,
                    sustain_amplitude=0.25,
                ),
            )
        )

    def play(self, name):
        """Play a named sound. Fails silently if sound not found or disabled."""
        if not self.enabled:
            return
        source = self._cache.get(name)
        if source:
            source.play()
