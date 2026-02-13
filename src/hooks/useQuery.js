import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";

const useQuery = () => {
  const { user } = useAuth();
  const storageKey = user
    ? `caseiq_chat_${user.email}`
    : "caseiq_chat";

  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  // Load messages
  useEffect(() => {
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      setMessages(JSON.parse(saved));
    } else {
      setMessages([
        {
          sender: "ai",
          text: "Welcome to CaseIQ AI Assistant.",
        },
      ]);
    }
  }, [storageKey]);

  // Save messages
  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(messages));
  }, [messages, storageKey]);

  const sendQuery = (text) => {
    const userMessage = { sender: "user", text };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    // Simulated AI
    setTimeout(() => {
      const aiMessage = {
        sender: "ai",
        text:
          "This is a simulated legal knowledge response.",
      };

      setMessages((prev) => [...prev, aiMessage]);
      setLoading(false);
    }, 1000);
  };

  return { messages, loading, sendQuery };
};

export default useQuery;
