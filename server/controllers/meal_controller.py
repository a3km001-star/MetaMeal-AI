"""Controller functions for meal planner API endpoints."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from fastapi import HTTPException
from pydantic import ValidationError

from model.meal_model import MealRequest, SaveMealRequest
from db.mongo import meal_plans_collection, users_collection
from services.auth_service import update_user_details, record_meal_generation_event
from services.nutrition_engine.meal_planner import UserProfile, create_meal_plan_response
from services.nutrition_engine.metabolic_calculator import Sex, ActivityLevel, FitnessGoal


logger = logging.getLogger(__name__)


def generate_meal_plan_controller(
	request_data: Union[MealRequest, Dict[str, Any]],
	current_user: Optional[dict] = None,
) -> Dict[str, Any]:
	"""Validate input and generate a meal plan response for the API layer."""
	try:
		payload = request_data if isinstance(request_data, MealRequest) else MealRequest(**request_data)
		logger.info("Meal generation request received")

		# Convert string values to enum instances for UserProfile
		user_profile_data = payload.model_dump()
		user_profile_data["sex"] = Sex(payload.sex)
		user_profile_data["activity_level"] = ActivityLevel(payload.activity_level)
		user_profile_data["goal"] = FitnessGoal(payload.goal)

		user_profile = UserProfile(**user_profile_data)

		if current_user is not None:
			try:
				record_meal_generation_event(current_user["id"], payload.model_dump(mode="json"))
			except Exception as exc:
				logger.warning("Failed to record meal generation metadata: %s", exc)

		response = create_meal_plan_response(user_profile)

		if current_user is not None:
			try:
				meal_plans_collection.insert_one(
					{
						"user_id": current_user.get("id"),
						"created_at": datetime.now(timezone.utc),
						"plan": response,
					}
				)
			except Exception as exc:
				logger.warning("Failed to persist meal plan for chat tools: %s", exc)

		if current_user is not None:
			try:
				update_user_details(current_user["id"], {
					"age": int(payload.age),
					"sex": payload.sex,
					"height": float(payload.height),
					"weight": float(payload.weight),
					"diet_type": payload.diet_type,
					"activity_level": payload.activity_level,
					"goal": payload.goal,
					"allergies": payload.allergies,
				})
			except Exception as exc:
				logger.warning("Failed to update user details: %s", exc)

		logger.info("Meal planner executed")
		logger.info("Meal plan successfully generated")

		return {
			"success": True,
			"message": "Meal plan generated successfully",
			"data": response,
		}

	except ValidationError as exc:
		logger.warning("Invalid meal generation input: %s", exc)
		raise HTTPException(
			status_code=400,
			detail={
				"message": "Invalid input data",
				"errors": exc.errors(),
			},
		)
	except HTTPException as exc:
		detail_text = str(exc.detail).lower()
		if exc.status_code == 400:
			logger.warning("Meal generation failed due to invalid request or no feasible plan: %s", exc.detail)
		elif "dataset" in detail_text or "file" in detail_text or "not found" in detail_text:
			logger.error("Meal generation failed due to dataset error: %s", exc.detail)
		else:
			logger.error("Meal generation failed with HTTP error: %s", exc.detail)
		raise
	except FileNotFoundError:
		logger.exception("Meal generation failed: dataset file missing")
		raise HTTPException(status_code=500, detail="Dataset file is missing")
	except Exception:
		logger.exception("Meal generation failed with internal error")
		raise HTTPException(status_code=500, detail="Internal server error while generating meal plan")


def save_meal_controller(
	request_data: Union[SaveMealRequest, Dict[str, Any]],
	current_user: Optional[dict] = None,
) -> Dict[str, Any]:
	"""Save a generated meal plan to user's profile."""
	if current_user is None:
		raise HTTPException(status_code=401, detail="Authentication required to save meals")
	
	try:
		payload = request_data if isinstance(request_data, SaveMealRequest) else SaveMealRequest(**request_data)
		user_id = current_user.get("id")
		
		logger.info(f"Saving meal for user {user_id} on date {payload.save_date}")
		
		# Calculate total meal macros from all meal slots
		total_calories = 0
		total_protein = 0
		meal_plan = payload.meal_data.get("meal_plan", {})
		
		for slot in ["breakfast", "lunch", "dinner", "snack"]:
			meal = meal_plan.get(slot, {})
			if meal:
				total_calories += meal.get("calories", 0)
				total_protein += meal.get("protein", 0)
		
		# Create meal history entry
		meal_history_entry = {
			"date": payload.save_date,
			"calories": total_calories,
			"protein": total_protein,
			"meal_data": payload.meal_data,
			"saved_at": datetime.now(timezone.utc),
		}
		
		# Update user document to store saved meal and add to history
		users_collection.update_one(
			{"_id": user_id},
			{
				"$set": {
					"saved_meals": {
						"date": payload.save_date,
						"meal_data": payload.meal_data,
						"saved_at": datetime.now(timezone.utc),
					}
				},
				"$push": {
					"meal_history": meal_history_entry
				}
			},
			upsert=True,
		)
		
		logger.info(f"Meal successfully saved for user {user_id}")
		return {
			"success": True,
			"message": "Meal saved successfully",
			"data": {
				"date": payload.save_date,
				"calories": total_calories,
				"protein": total_protein,
			},
		}
		
	except ValidationError as exc:
		logger.warning("Invalid save meal input: %s", exc)
		raise HTTPException(
			status_code=400,
			detail={"message": "Invalid input data", "errors": exc.errors()},
		)
	except Exception as exc:
		logger.exception("Error saving meal: %s", exc)
		raise HTTPException(status_code=500, detail="Failed to save meal")


def get_saved_meal_for_today_controller(current_user: Optional[dict] = None) -> Dict[str, Any]:
	"""Retrieve the saved meal for today (if exists)."""
	if current_user is None:
		raise HTTPException(status_code=401, detail="Authentication required")
	
	try:
		user_id = current_user.get("id")
		from datetime import date
		
		today_date = str(date.today())
		logger.info(f"Fetching saved meal for user {user_id} for date {today_date}")
		
		# Fetch user document
		user = users_collection.find_one({"_id": user_id})
		
		if not user:
			logger.info(f"User {user_id} not found")
			return {"success": True, "data": None}
		
		saved_meals = user.get("saved_meals")
		
		# Check if saved meal exists and if it's for today
		if saved_meals and saved_meals.get("date") == today_date:
			logger.info(f"Found saved meal for user {user_id} for {today_date}")
			return {
				"success": True,
				"data": saved_meals.get("meal_data"),
				"saved_date": saved_meals.get("date"),
			}
		
		logger.info(f"No saved meal found for user {user_id} for {today_date}")
		return {"success": True, "data": None}
		
	except Exception as exc:
		logger.exception("Error retrieving saved meal: %s", exc)
		raise HTTPException(status_code=500, detail="Failed to retrieve saved meal")


def save_weight_entry_controller(
	weight: float,
	current_user: Optional[dict] = None,
) -> Dict[str, Any]:
	"""Save a weight entry for the user."""
	if current_user is None:
		raise HTTPException(status_code=401, detail="Authentication required")
	
	try:
		from datetime import date
		user_id = current_user.get("id")
		today_date = str(date.today())
		
		logger.info(f"Saving weight {weight}kg for user {user_id} on {today_date}")
		
		weight_entry = {
			"date": today_date,
			"weight": float(weight),
			"recorded_at": datetime.now(timezone.utc),
		}
		
		# Save weight trend and update current profile weight
		users_collection.update_one(
			{"_id": user_id},
			{
				"$push": {
					"weight_history": weight_entry,
					"user_details.weight_history": weight_entry,
				},
				"$set": {
					"user_details.weight": float(weight),
					"user_details.last_weight_updated_at": today_date,
				},
			},
			upsert=True,
		)
		
		logger.info(f"Weight successfully saved for user {user_id}")
		return {
			"success": True,
			"message": "Weight saved successfully",
			"data": weight_entry,
		}
		
	except Exception as exc:
		logger.exception("Error saving weight: %s", exc)
		raise HTTPException(status_code=500, detail="Failed to save weight")


def get_weight_history_controller(current_user: Optional[dict] = None) -> Dict[str, Any]:
	"""Get user's weight history for all time."""
	if current_user is None:
		raise HTTPException(status_code=401, detail="Authentication required")
	
	try:
		user_id = current_user.get("id")
		logger.info(f"Fetching weight history for user {user_id}")
		
		user = users_collection.find_one({"_id": user_id})
		
		if not user:
			return {"success": True, "data": []}
		
		weight_history = user.get("weight_history", [])
		if isinstance(weight_history, list):
			weight_history = sorted(weight_history, key=lambda item: item.get("date", ""))
		return {
			"success": True,
			"data": weight_history,
		}
		
	except Exception as exc:
		logger.exception("Error retrieving weight history: %s", exc)
		raise HTTPException(status_code=500, detail="Failed to retrieve weight history")


def get_meal_history_controller(current_user: Optional[dict] = None) -> Dict[str, Any]:
	"""Get user's meal history for all time (calories and protein)."""
	if current_user is None:
		raise HTTPException(status_code=401, detail="Authentication required")
	
	try:
		user_id = current_user.get("id")
		logger.info(f"Fetching meal history for user {user_id}")
		
		user = users_collection.find_one({"_id": user_id})
		
		if not user:
			return {"success": True, "data": []}
		
		meal_history = user.get("meal_history", [])
		# Aggregate by date to produce daily totals (calories, protein)
		daily_map = {}
		for meal in meal_history:
			date_key = meal.get("date") or (meal.get("saved_at") and str(meal.get("saved_at")))
			if not date_key:
				continue
			# Normalize date key to ISO date if possible
			try:
				from datetime import date as _date
				# if already iso-like, keep as-is; otherwise attempt to parse
			except Exception:
				pass
			entry = daily_map.get(date_key)
			if not entry:
				entry = {"date": date_key, "calories": 0.0, "protein": 0.0}
				daily_map[date_key] = entry
			try:
				entry["calories"] += float(meal.get("calories", 0) or 0)
			except Exception:
				pass
			try:
				entry["protein"] += float(meal.get("protein", 0) or 0)
			except Exception:
				pass
		# Convert to sorted list by date string (ISO format expected)
		daily_list = list(daily_map.values())
		daily_list.sort(key=lambda x: x.get("date", ""))
		return {
			"success": True,
			"data": daily_list,
		}
		
	except Exception as exc:
		logger.exception("Error retrieving meal history: %s", exc)
		raise HTTPException(status_code=500, detail="Failed to retrieve meal history")


def get_weekly_summary_controller(current_user: Optional[dict] = None) -> Dict[str, Any]:
	"""Get weekly summary stats for the past 7 days."""
	if current_user is None:
		raise HTTPException(status_code=401, detail="Authentication required")
	
	try:
		from datetime import date, timedelta
		user_id = current_user.get("id")
		logger.info(f"Fetching weekly summary for user {user_id}")
		
		user = users_collection.find_one({"_id": user_id})
		
		if not user:
			return {
				"success": True,
				"data": {
					"total_meals_logged": 0,
					"avg_daily_calories": 0,
					"consistency_rating": 0,
				},
			}
		
		# Get meal history
		meal_history = user.get("meal_history", [])
		
		# Calculate past 7 days
		today = date.today()
		seven_days_ago = today - timedelta(days=6)  # Include today
		
		# Filter meals from past 7 days
		meals_past_7_days = []
		days_with_meals = set()
		
		for meal in meal_history:
			try:
				meal_date = date.fromisoformat(meal.get("date", ""))
				if seven_days_ago <= meal_date <= today:
					meals_past_7_days.append(meal)
					days_with_meals.add(meal_date)
			except:
				pass
		
		# Calculate stats
		total_meals = len(meals_past_7_days)
		total_calories = sum(meal.get("calories", 0) for meal in meals_past_7_days)
		avg_daily_calories = total_calories / 7 if total_calories > 0 else 0
		consistency_rating = (len(days_with_meals) / 7) * 100  # percentage
		
		logger.info(f"Weekly summary calculated for user {user_id}")
		return {
			"success": True,
			"data": {
				"total_meals_logged": total_meals,
				"avg_daily_calories": round(avg_daily_calories, 2),
				"consistency_rating": round(consistency_rating, 1),
				"days_active": len(days_with_meals),
			},
		}
		
	except Exception as exc:
		logger.exception("Error calculating weekly summary: %s", exc)
		raise HTTPException(status_code=500, detail="Failed to calculate weekly summary")