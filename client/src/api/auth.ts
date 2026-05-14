import { apiClient } from "./client";

export const registerUser = async (payload: any) => {
  return apiClient.post("/auth/register", payload);
};

export const loginUser = async (payload: any) => {
  return apiClient.post("/auth/login", payload);
};

// Use the new /me endpoint from your latest schema
export const getMe = async () => {
  return apiClient.get("/me");
};
