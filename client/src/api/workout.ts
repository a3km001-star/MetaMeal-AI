import { apiClient } from "./client";

export const generateWorkoutPlan = async (payload: any) => {
  return apiClient.post("/workout/generate", payload);
};

export const getLatestWorkoutPlan = async () => {
  return apiClient.get("/workout/latest");
};
