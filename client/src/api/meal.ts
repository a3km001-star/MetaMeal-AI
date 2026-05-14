import { apiClient } from "./client";

export const generateMealPlan = async (payload: any) => {
  return apiClient.post("/meal/generate", payload);
};
