import { apiClient } from "./client";

export const generateMealPlan = async (payload: any) => {
  return apiClient.post("/meal/generate", payload);
};

export const saveMeal = async (payload: any) => {
  return apiClient.post("/meal/save", payload);
};

export const getSavedMealForToday = async () => {
  return apiClient.get("/meal/saved-for-today");
};

export const saveWeight = async (weight: number) => {
  return apiClient.post("/meal/weight", { weight });
};

export const getWeightHistory = async () => {
  return apiClient.get("/meal/weight-history");
};

export const getMealHistory = async () => {
  return apiClient.get("/meal/meal-history");
};

export const getWeeklySummary = async () => {
  return apiClient.get("/meal/weekly-summary");
};
