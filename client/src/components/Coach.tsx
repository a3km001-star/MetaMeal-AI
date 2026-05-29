import { useState, useRef, useEffect, useMemo } from "react";
import { Send, Bot, User } from "lucide-react";
import type { User as AppUser, ViewType } from "../types";
import { getChatHistory, sendChatMessage } from "../api/chat";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface CoachProps {
  setActiveView: (view: ViewType) => void;
  user: AppUser;
}

const conversationStorageKey = (userId: string) =>
  `chat_conversation_id:${userId}`;
const configStorageKey = (userId: string) => `chat_config_id:${userId}`;

const getConversationId = (userId: string): string => {
  const key = conversationStorageKey(userId);
  const existing = localStorage.getItem(key);
  if (existing) return existing;

  const newId =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `conv_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  localStorage.setItem(key, newId);
  return newId;
};

const getConfigId = (userId: string): string => {
  const key = configStorageKey(userId);
  const existing = localStorage.getItem(key);
  if (existing) return existing;

  const newId =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `cfg_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  localStorage.setItem(key, newId);
  return newId;
};

function Coach({ setActiveView, user }: CoachProps) {
  const getErrorMessage = (error: unknown, fallback: string): string => {
    if (error && typeof error === "object") {
      const response = (error as { response?: { data?: any } }).response;
      const detail = response?.data?.detail;
      const message = response?.data?.message;
      if (typeof detail === "string" && detail.trim()) return detail;
      if (typeof message === "string" && message.trim()) return message;
    }

    if (error instanceof Error && error.message.trim()) {
      return error.message;
    }

    return fallback;
  };
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hello! I'm your MetaMeal AI Coach. How can I help you with your nutrition goals today?",
    },
  ]);
  const [input, setInput] = useState<string>("");
  const [isSending, setIsSending] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const conversationId = useMemo(() => getConversationId(user.id), [user.id]);
  const configId = useMemo(() => getConfigId(user.id), [user.id]);

  const scrollToBottom = (): void => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    let isActive = true;
    const loadHistory = async (): Promise<void> => {
      if (!user?.id) return;

      try {
        const response = await getChatHistory({
          conversation_id: conversationId,
          config_id: configId,
          limit: 50,
        });
        const history = response.data?.data?.messages ?? [];
        const filtered = history
          .filter((item) => item.role === "user" || item.role === "assistant")
          .map((item) => ({ role: item.role, content: item.content }));

        if (isActive && filtered.length > 0) {
          setMessages(filtered);
        }
      } catch (error) {
        if (isActive) {
          const message = getErrorMessage(
            error,
            "I could not load your previous messages, but you can keep chatting.",
          );
          setMessages((prev) =>
            prev.length > 1
              ? prev
              : [
                  ...prev,
                  {
                    role: "assistant",
                    content: message,
                  },
                ],
          );
        }
      }
    };

    loadHistory();
    return () => {
      isActive = false;
    };
  }, [user?.id, conversationId, configId]);

  const handleSend = async (
    e: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    e.preventDefault();
    if (!input.trim()) return;

    const normalizedInput = input.trim().toLowerCase();
    if (normalizedInput.includes("previous question")) {
      const lastUserMessage = [...messages]
        .reverse()
        .find((message) => message.role === "user");
      const responseText = lastUserMessage?.content
        ? `Your previous question was: "${lastUserMessage.content}"`
        : "I couldn't find a previous question in this session yet.";

      setMessages((prev) => [
        ...prev,
        { role: "user", content: input },
        { role: "assistant", content: responseText },
      ]);
      setInput("");
      return;
    }

    if (!user?.id) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Please log in to use the AI Coach.",
        },
      ]);
      return;
    }

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsSending(true);

    try {
      const response = await sendChatMessage({
        message: userMessage.content,
        user_id: user.id,
        conversation_id: conversationId,
        config_id: configId,
      });
      const reply = response.data?.data?.reply?.trim();
      const aiResponse: Message = {
        role: "assistant",
        content:
          reply && reply.length > 0
            ? reply
            : "I could not generate a response right now. Please try again.",
      };
      setMessages((prev) => [...prev, aiResponse]);
    } catch (error) {
      const message = getErrorMessage(
        error,
        "Sorry, I ran into an error while contacting the server. Please try again.",
      );
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: message,
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-2">
          AI Coach
        </h1>
        <p className="text-gray-600 dark:text-gray-300">
          Get personalized nutrition guidance
        </p>
      </div>

      <div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg overflow-hidden flex flex-col"
        style={{ height: "calc(100vh - 300px)" }}
      >
        <div className="flex-grow overflow-y-auto p-6 space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`flex items-start space-x-3 max-w-[80%] ${
                  message.role === "user"
                    ? "flex-row-reverse space-x-reverse"
                    : ""
                }`}
              >
                <div
                  className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
                    message.role === "user"
                      ? "bg-gradient-to-br from-blue-500 to-indigo-600"
                      : "bg-gradient-to-br from-purple-500 to-pink-600"
                  }`}
                >
                  {message.role === "user" ? (
                    <User className="w-5 h-5 text-white" />
                  ) : (
                    <Bot className="w-5 h-5 text-white" />
                  )}
                </div>

                <div
                  className={`rounded-2xl px-4 py-3 ${
                    message.role === "user"
                      ? "bg-gradient-to-br from-blue-500 to-indigo-600 text-white"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-white"
                  }`}
                >
                  <p className="text-sm leading-relaxed">{message.content}</p>
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-800">
          <form onSubmit={handleSend} className="flex space-x-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isSending}
              aria-label="Ask a nutrition question"
              placeholder="Ask me anything about nutrition..."
              className="flex-grow px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            />
            <button
              type="submit"
              disabled={isSending}
              className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:scale-105 transition-all flex items-center space-x-2"
            >
              <Send className="w-5 h-5" />
              <span className="hidden sm:inline">
                {isSending ? "Sending..." : "Send"}
              </span>
            </button>
          </form>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <button
          onClick={() => setInput("What should I eat before a workout?")}
          className="text-left p-4 bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-lg transition-shadow"
        >
          <p className="text-sm font-semibold text-gray-800 dark:text-white">
            Pre-workout nutrition
          </p>
          <p className="text-xs text-gray-600 dark:text-gray-300 mt-1">
            What should I eat before exercising?
          </p>
        </button>
        <button
          onClick={() => setInput("How much protein do I need daily?")}
          className="text-left p-4 bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-lg transition-shadow"
        >
          <p className="text-sm font-semibold text-gray-800 dark:text-white">
            Protein requirements
          </p>
          <p className="text-xs text-gray-600 dark:text-gray-300 mt-1">
            Calculate my daily protein needs
          </p>
        </button>
      </div>
    </div>
  );
}

export default Coach;
