"""Volume allocation helpers for deterministic weekly set distribution."""

from typing import Dict, List, Union


_PRIMARY_MUSCLES_BY_DAY_TYPE: Dict[str, List[str]] = {
	"push": ["chest", "shoulders", "triceps"],
	"pull": ["back", "biceps", "rear_delts"],
	"legs": ["quads", "hamstrings", "glutes", "calves"],
	"upper": ["chest", "back", "shoulders", "biceps", "triceps"],
	"lower": ["quads", "hamstrings", "glutes", "calves"],
	"full_body": ["chest", "back", "quads", "hamstrings", "shoulders", "biceps", "triceps", "calves"],
}


def muscles_for_day_type(day_type: str) -> List[str]:
	return list(_PRIMARY_MUSCLES_BY_DAY_TYPE.get(day_type, []))


def resolve_weekly_targets(
	weekly_volume_per_muscle: Union[int, Dict[str, int]],
	day_types: List[str],
) -> Dict[str, int]:
	"""Resolve final weekly target sets per muscle from int or dict input."""
	if isinstance(weekly_volume_per_muscle, dict):
		return {str(k).strip().lower(): int(v) for k, v in weekly_volume_per_muscle.items()}

	target = int(weekly_volume_per_muscle)
	muscles = []
	for day_type in day_types:
		for muscle in muscles_for_day_type(day_type):
			if muscle not in muscles:
				muscles.append(muscle)
	return {muscle: target for muscle in muscles}


def allocate_sets_to_days(day_types: List[str], weekly_targets: Dict[str, int]) -> Dict[str, Dict[str, int]]:
	"""Allocate each muscle's weekly sets across compatible training days as evenly as possible."""
	allocation: Dict[str, Dict[str, int]] = {f"day_{idx+1}": {} for idx in range(7)}

	for muscle, total_sets in weekly_targets.items():
		eligible_day_idx = [
			idx for idx, day_type in enumerate(day_types)
			if muscle in muscles_for_day_type(day_type)
		]

		if not eligible_day_idx:
			continue

		base = total_sets // len(eligible_day_idx)
		remainder = total_sets % len(eligible_day_idx)

		for pos, day_idx in enumerate(eligible_day_idx):
			sets_here = base + (1 if pos < remainder else 0)
			if sets_here <= 0:
				continue
			day_key = f"day_{day_idx+1}"
			allocation[day_key][muscle] = sets_here

	return allocation