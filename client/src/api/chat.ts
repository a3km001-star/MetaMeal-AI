import { apiClient } from "./client";

type ChatResponse = {
  success: boolean;
  message: string;
  data?: {
    reply: string;
    tool_calls: string[];
  };
};

export const sendChatMessage = async (payload: {
  message: string;
  user_id: string;
  conversation_id?: string;
  config_id?: string;
}) => {
  return apiClient.post<ChatResponse>("/chat/message", payload);
};

type ChatHistoryResponse = {
  success: boolean;
  message: string;
  data?: {
    messages: Array<{
      role: "user" | "assistant" | "tool";
      content: string;
      created_at?: string;
    }>;
  };
};

export const getChatHistory = async (params: {
  conversation_id?: string;
  config_id?: string;
  limit?: number;
}) => {
  return apiClient.get<ChatHistoryResponse>("/chat/history", { params });
};
