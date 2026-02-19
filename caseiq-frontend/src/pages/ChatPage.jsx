import { useState, useEffect, useCallback } from "react";
import AIResponseWindow from "../components/ai/AIResponseWindow";
import QueryInput from "../components/ai/QueryInput";
import LawReferenceViewer from "../components/law/LawReferenceViewer";

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [latestLaws, setLatestLaws] = useState([]);

  /* -------------------------------
     LOAD CHAT HISTORY
  --------------------------------*/
  useEffect(() => {
    try {
      const savedMessages = localStorage.getItem("caseiq_chat");

      if (savedMessages) {
        const parsed = JSON.parse(savedMessages);
        setMessages(parsed);

        const lastMessage = parsed[parsed.length - 1];
        if (lastMessage?.laws) {
          setLatestLaws(lastMessage.laws);
        }
      } else {
        setMessages([
          {
            sender: "ai",
            text: `👋 Welcome to CaseIQ Legal Assistant.

Ask your legal question and I’ll provide a structured explanation under Indian law.

⚖️ This platform provides legal information, not legal advice.`,
          },
        ]);
      }
    } catch (error) {
      console.error("Error loading chat:", error);
    }
  }, []);

  /* -------------------------------
     SAVE CHAT
  --------------------------------*/
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem("caseiq_chat", JSON.stringify(messages));
    }
  }, [messages]);

  /* -------------------------------
     SEND MESSAGE
  --------------------------------*/
  const handleSend = useCallback((text) => {
    if (!text.trim()) return;

    const userMessage = { sender: "user", text };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    setTimeout(() => {
      const aiMessage = {
        sender: "ai",
        text: `Here is a structured legal overview:

🔹 Legal Context  
Your query relates to provisions governed under Indian criminal law.

🔹 Explanation  
The applicable section defines the scope, ingredients of the offence, and legal standards.

🔹 Consequences  
Punishment depends on severity, intent, and evidence.

⚠️ For case-specific advice, consult a qualified advocate.`,
        laws: [
          {
            section: "Relevant Section (Example)",
            title: "Applicable Legal Provision",
            description:
              "This section defines the offence and outlines the necessary legal elements required to establish liability.",
            punishment:
              "Punishment varies depending on facts and judicial discretion.",
          },
        ],
      };

      setMessages((prev) => [...prev, aiMessage]);
      setLatestLaws(aiMessage.laws);
      setLoading(false);
    }, 1000);
  }, []);

  /* -------------------------------
     HANDLE PENDING QUERY
  --------------------------------*/
  useEffect(() => {
    const pendingQuery = localStorage.getItem("caseiq_pending_query");

    if (pendingQuery) {
      handleSend(pendingQuery);
      localStorage.removeItem("caseiq_pending_query");
    }
  }, [handleSend]);

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-12">

      {/* HERO HEADER */}
      <div className="text-center space-y-3">
        <h2 className="text-4xl font-bold text-[#443627]">
          AI Legal Assistant
        </h2>
        <p className="text-[#725E54] text-lg">
          Get structured and verified legal information instantly.
        </p>
      </div>

      {/* CHAT CONTAINER */}
      <div className="
        bg-gradient-to-br from-[#D5DCF9]/60 to-[#8EDCE6]/60
        backdrop-blur-md
        rounded-3xl
        shadow-xl
        p-6
        border border-white/40
        transition
      ">
        <AIResponseWindow messages={messages} loading={loading} />

        <div className="mt-6">
          <QueryInput onSend={handleSend} disabled={loading} />
        </div>
      </div>

      {/* LAW REFERENCES */}
      {latestLaws.length > 0 && (
        <div className="
          bg-gradient-to-br from-[#A7B0CA]/60 to-[#D5DCF9]/60
          backdrop-blur-md
          rounded-3xl
          shadow-lg
          p-6
          border border-white/40
          transition
        ">
          <h3 className="text-xl font-semibold text-[#443627] mb-4">
            📚 Relevant Legal Sections
          </h3>

          <LawReferenceViewer laws={latestLaws} />
        </div>
      )}

    </div>
  );
};

export default ChatPage;
