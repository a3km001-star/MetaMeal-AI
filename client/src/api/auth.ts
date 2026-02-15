import { apiClient } from "./client";

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
  age: string;
  height: string;
  weight: string;
  workoutExperience: string;
  dietPreference: string;
  goal: string;
  activityLevel: string;
}

export const registerUser = (payload: RegisterPayload) =>
  apiClient.post("/register", payload);
