import random
import time
from core.input_simulator import InputSimulator


class AntiAFK:
    """Anti-AFK module that executes subtle human-like movements."""

    def __init__(self, simulator: InputSimulator):
        self.sim = simulator
        self.action_counter = 0

    def trigger_if_needed(self, min_actions: int = 6, max_actions: int = 12):
        self.action_counter += 1
        threshold = random.randint(min_actions, max_actions)
        if self.action_counter >= threshold:
            self.perform_anti_afk()
            self.action_counter = 0

    def perform_anti_afk(self):
        """Perform a very minor safe action (e.g., slight jump or nudge)."""
        time.sleep(random.uniform(0.3, 0.8))
        # Nudge left or right slightly
        key = random.choice(["LEFT", "RIGHT"])
        self.sim.press_key(key, duration_sec=random.uniform(0.04, 0.08))
