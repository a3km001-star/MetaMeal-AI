"""Build weekly day types from split and training-day constraints."""

from typing import List


_SPLIT_CYCLES = {
	"push_pull_legs": ["push", "pull", "legs"],
	"upper_lower": ["upper", "lower"],
	"full_body": ["full_body"],
}


def build_weekly_day_types(split: str, training_days: int) -> List[str]:
	"""Return a 7-day day-type list that preserves split order and rest days."""
	cycle = _SPLIT_CYCLES.get(str(split).strip().lower(), ["full_body"])
	days = max(1, min(int(training_days), 7))

	result: List[str] = []
	for idx in range(days):
		result.append(cycle[idx % len(cycle)])

	while len(result) < 7:
		result.append("rest")

	return result