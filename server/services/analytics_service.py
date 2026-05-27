"""Lightweight analytics helpers for progress logs."""

from typing import Dict, List, Optional


def calculate_moving_average(values: List[float], window: int = 3) -> Optional[float]:
	if len(values) < window:
		return None
	return round(sum(values[:window]) / float(window), 2)


def detect_plateau(values: List[float], threshold: float = 0.2) -> bool:
	if len(values) < 3:
		return False
	return abs(values[0] - values[2]) <= threshold


def build_progress_summary(weights: List[float]) -> Dict[str, Optional[float]]:
	if not weights:
		return {"latest_weight": None, "weight_change": None, "moving_average": None, "plateau": False}

	weight_change = None
	if len(weights) >= 2:
		weight_change = round(weights[0] - weights[-1], 2)

	return {
		"latest_weight": weights[0],
		"weight_change": weight_change,
		"moving_average": calculate_moving_average(weights),
		"plateau": detect_plateau(weights),
	}