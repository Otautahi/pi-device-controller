"""PulseDirector autonomous scene planner — offline, bounded, no device I/O.

A fresh scene is planned when the prior scene finishes. This module neither
connects to Lovense nor sends commands; the dashboard enforces output caps,
session deadlines, serialised Stop and connection checks.
"""
from collections import deque
import math
import random

STYLES = ("confident", "unpredictable", "patient", "playful", "progressive")
FLOWS = ("driving", "balanced", "build", "waves")

_SCENES = {
    "confident": {"lead": 5, "follow": 3, "counter": 3, "duet": 5, "swell": 2,
                  "accent": 4, "breather": 1, "echo": 3, "drift": 1, "steps": 4,
                  "hold": 5, "switch": 4, "fakeout": 2},
    "unpredictable": {"lead": 3, "follow": 2, "counter": 2, "duet": 2, "swell": 2,
                      "accent": 2, "breather": 1, "echo": 2, "drift": 2, "steps": 2},
    "patient": {"lead": 3, "follow": 1, "counter": 1, "duet": 2, "swell": 4,
                "accent": 1, "breather": 3, "echo": 1, "drift": 4, "steps": 2},
    "playful": {"lead": 2, "follow": 3, "counter": 4, "duet": 1, "swell": 1,
                "accent": 4, "breather": 1, "echo": 4, "drift": 1, "steps": 3},
    "progressive": {"lead": 3, "follow": 2, "counter": 1, "duet": 3, "swell": 4,
                    "accent": 2, "breather": 1, "echo": 2, "drift": 2, "steps": 3},
}

SCENE_NAMES = {"lead": "Lead & support", "follow": "Follow the lead",
               "counter": "Counterpoint", "duet": "Together", "swell": "Slow swell",
               "accent": "Accents", "breather": "Reset & breathe",
               "echo": "Call & response", "drift": "Slow drift", "steps": "Climbing steps",
               "hold": "Firm hold", "switch": "Take turns", "fakeout": "Unexpected reset"}


INTENTS = {"lead": "Setting the pace", "follow": "Changing the lead", "counter": "Opposing rhythms",
           "duet": "Both together", "swell": "Building deliberately", "accent": "Adding accents",
           "breather": "A purposeful reset", "echo": "Call and response", "drift": "A slow change",
           "steps": "Stepping it up", "hold": "Holding steady", "switch": "Switching focus",
           "fakeout": "An unexpected pause"}


class AutonomousDirector:
    def __init__(self, style="confident", surprise=4, flow="driving", rng=None):
        if style not in STYLES:
            raise ValueError("Unknown autonomous style")
        if type(surprise) is not int or not 1 <= surprise <= 5:
            raise ValueError("Surprise must be an integer from 1 to 5")
        if flow not in FLOWS:
            raise ValueError("Unknown session flow")
        self.style = style
        self.surprise = surprise
        self.flow = flow
        self.rng = rng if rng is not None else random.SystemRandom()
        self.recent = deque(maxlen=8)
        self.queue = deque()
        self.segment = None
        self.segment_start = 0.0
        self.segment_until = 0.0
        self.transition_from = (0, 0)
        self.decision_count = 0
        self.last_scene = ""
        self.last_output = (0, 0)
        self.phase = "Warm-up"
        self.energy = 0
        self.intent = "Choosing the next move"
        self.reprises = 0

    def _choose_scene(self, fraction):
        weights = _SCENES[self.style]
        names, values = [], []
        for scene, base in weights.items():
            if scene in list(self.recent)[-2:]:
                continue  # Never repeat either of the last two decisions
            weight = float(base)
            if scene in self.recent:
                weight *= .5
            if scene == "breather":
                # Schedule an occasional recovery, particularly later on.
                weight *= 1.1 if fraction < .50 else 1.8
            if scene in ("accent", "echo", "counter"):
                weight *= .7 + .16 * self.surprise
            if fraction < .12 and scene in ("accent", "counter", "steps"):
                weight *= .35
            names.append(scene)
            values.append(weight)
        # A confident controller occasionally returns to a theme that has
        # already played, but never repeats either of its two most recent scenes.
        # This is deliberate motif recall, not blind randomisation.
        candidates = [s for s in list(self.recent)[:-2] if s in names]
        is_reprise = self.style == "confident" and candidates and self.rng.random() < .21
        if is_reprise:
            chosen = self.rng.choice(candidates)
            self.reprises += 1
        else:
            chosen = self.rng.choices(names, weights=values, k=1)[0]
        self.intent = "Bringing back a theme" if is_reprise else INTENTS[chosen]
        self.recent.append(chosen)
        self.last_scene = chosen
        self.decision_count += 1
        return chosen

    def _plan_scene(self, speed, fraction):
        name = self._choose_scene(fraction)
        r = self.rng
        if self.style == "confident":
            # Stronger programmed relative levels without raising the user's
            # maximum, Motor 2 contribution, or session timeout.
            lo, mid = r.uniform(.36, .51), r.uniform(.66, .82)
            hi, a, b = r.uniform(.88, 1.0), r.uniform(.77, .93), r.uniform(.73, .96)
        else:
            lo, mid = r.uniform(.18, .35), r.uniform(.41, .63)
            hi, a, b = r.uniform(.73, .96), r.uniform(.56, .87), r.uniform(.48, .82)
        if name == "lead":
            phases = [(hi, lo*.55), (mid, b*.65), (lo, b*.25)]
        elif name == "follow":
            phases = [(hi, 0), (hi*.72, b), (lo, b*.9)]
        elif name == "counter":
            phases = [(a, lo), (lo*.5, b), (hi, b*.38), (mid, 0)]
        elif name == "duet":
            phases = [(mid, mid*.7), (hi, b), (mid*.7, mid)]
        elif name == "swell":
            phases = [(lo, lo*.3), (mid, b*.65), (hi, b), (mid, lo)]
        elif name == "accent":
            phases = [(mid, .03), (mid*1.05, b), (hi, 0), (lo, b*.75)]
        elif name == "echo":
            phases = [(mid, 0), (mid*.60, b), (hi, lo*.3), (lo, b*.83)]
        elif name == "drift":
            phases = [(lo, b*.35), (mid, b*.47), (mid*.82, b*.92), (lo, lo)]
        elif name == "steps":
            phases = [(lo, 0), (mid, lo), (hi, b*.5), (mid, b), (lo, 0)]
        elif name == "hold":
            phases = [(hi, b*.62), (hi, b), (hi*.86, b*.85)]
        elif name == "switch":
            phases = [(hi, lo*.25), (mid*.74, b), (hi, b*.91), (lo*.65, b)]
        elif name == "fakeout":
            phases = [(hi, b*.70), (0, 0), (hi*.91, b*.95)]
        else:
            phases = [(0, 0), (lo, lo*.2), (mid, b*.45)]
        # Conservative durations work on LAN while keeping future slower
        # backends from missing every other scene phase.
        pace = {1: 1.42, 2: 1.20, 3: 1.0, 4: .86, 5: .76}[speed]
        novelty = {1: 1.25, 2: 1.12, 3: 1.0, 4: .91, 5: .84}[self.surprise]
        for i, (x, y) in enumerate(phases):
            duration = r.uniform(5.0, 10.5) if self.style == "confident" else r.uniform(4.2, 9.0)
            duration *= pace * novelty
            if name == "hold":
                duration *= 1.6  # A decision that is sustained, not changed at random.
            if name == "fakeout" and i == 1:
                duration = r.uniform(2.5, 4.0)  # Brief fully off, not an uncontrolled wait.
            duration = min(20.0, max(2.5, duration))
            self.queue.append((duration, max(0.0, min(x, 1.0)), max(0.0, min(y, 1.0))))

    def _intensity_factor(self, fraction):
        warmup = .055 if self.style == "confident" else .12
        easeout = .96 if self.style == "confident" else .90
        if fraction < warmup:
            self.phase = "Warm-up"
        elif fraction < .38:
            self.phase = "Explore"
        elif fraction < .72:
            self.phase = "Build"
        elif fraction < easeout:
            self.phase = "High tide"
        else:
            self.phase = "Ease out"

        if self.flow == "driving":
            factor = .96 + .04 * math.sin(2.0 * math.pi * fraction)
        elif self.flow == "build":
            factor = .52 + .48 * min(1.0, fraction / .86)
        elif self.flow == "waves":
            # Slow energy arcs rather than uniform intensity for the whole run.
            factor = .72 + .28 * (.5 + .5 * math.sin(2 * math.pi * (2.25*fraction-.25)))
        else:
            factor = 1.0
        if self.style == "progressive":
            factor *= .72 + .28 * min(1.0, fraction / .84)
        if fraction < warmup:
            start_factor = .76 if self.style == "confident" else .55
            factor *= start_factor + (1.0-start_factor) * fraction / warmup
        if fraction > easeout:
            easing = (fraction-easeout) / (1.0-easeout)
            factor *= max(.58 if self.style == "confident" else .48,
                          1.0 - (.42 if self.style == "confident" else .52) * easing)
        self.energy = round(min(100., max(0., factor * 100)))
        return factor

    def levels(self, elapsed, maximum, speed, support, session_seconds=1200):
        """Return (motor1, motor2) as bounded integers without any device I/O."""
        elapsed = max(0.0, float(elapsed))
        maximum = max(0, min(20, int(maximum)))
        speed = max(1, min(5, int(speed)))
        support = max(0, min(100, int(support)))
        fraction = min(1.0, elapsed / max(1.0, float(session_seconds)))
        factor = self._intensity_factor(fraction)

        # An unusually delayed call means the previous scene timing is no
        # longer relevant; never queue up missed commands.
        if elapsed > self.segment_until + 35:
            self.segment = None
            self.queue.clear()
            self.segment_until = elapsed

        if self.segment is None or elapsed >= self.segment_until:
            if not self.queue:
                self._plan_scene(speed, fraction)
            duration, a, b = self.queue.popleft()
            self.transition_from = self.last_output
            self.segment = (a, b)
            self.segment_start = elapsed
            self.segment_until = elapsed + duration

        a, b = self.segment
        target1 = round(maximum * a * factor)
        target2 = round(maximum * b * factor * support / 100.0)
        # Smooth the hand-off into each new phase, bounded by the user cap.
        blend_seconds = min(1.65, (self.segment_until-self.segment_start)*.35)
        fraction_blend = min(1.0, (elapsed-self.segment_start) / max(.01, blend_seconds))
        eased = fraction_blend * fraction_blend * (3.0 - 2.0 * fraction_blend)
        first = round(self.transition_from[0] * (1-eased) + target1*eased)
        second = round(self.transition_from[1] * (1-eased) + target2*eased)
        self.last_output = (max(0, min(maximum, first)), max(0, min(maximum, second)))
        return self.last_output

    def snapshot(self, elapsed):
        return {"scene": SCENE_NAMES.get(self.last_scene, "Preparing"),
                "phase": self.phase, "energy": self.energy,
                "intent": self.intent, "reprises": self.reprises,
                "sceneSecondsLeft": max(0, int(math.ceil(self.segment_until - elapsed))) if self.segment else 0,
                "decisions": self.decision_count}
