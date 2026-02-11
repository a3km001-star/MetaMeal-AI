import { useState, useRef } from "react";
import { Send, Bot, User } from "lucide-react";

function Coach({ setActiveView }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I'm your FitLife AI Coach. How can I help you with your nutrition goals today?",
    },
  ]);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    setMessages([...messages, userMessage]);
    setInput("");

    // Scroll after user message
    setTimeout(() => scrollToBottom(), 100);

    // Simulate AI response
    setTimeout(() => {
      const aiResponse = {
        role: "assistant",
        content:
          "Thanks for your question! I'm here to help. This is a demo response. In a real application, I would provide personalized nutrition advice based on your query.",
      };
      setMessages((prev) => [...prev, aiResponse]);
      // Scroll after AI response
      setTimeout(() => scrollToBottom(), 100);
    }, 1000);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-2">
          AI Coach
        </h1>
        <p className="text-gray-600 dark:text-gray-300">
          Get personalized nutrition guidance
        </p>
      </div>

      {/* Chat Container */}
      <div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg overflow-hidden flex flex-col"
        style={{ height: "calc(100vh - 300px)" }}
      >
        {/* Messages Area */}
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
                {/* Avatar */}
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

                {/* Message Bubble */}
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

        {/* Input Area */}
        <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-800">
          <form onSubmit={handleSend} className="flex space-x-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me anything about nutrition..."
              className="flex-grow px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            />
            <button
              type="submit"
              className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:scale-105 transition-all flex items-center space-x-2"
            >
              <Send className="w-5 h-5" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>
        </div>
      </div>

      {/* Quick Questions */}
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
