import { useEffect, useState } from "react";

const RecentSearches = () => {
  const [recentQueries, setRecentQueries] = useState([]);

  useEffect(() => {
    const chats = JSON.parse(localStorage.getItem("caseiq_chat")) || [];

    // Filter only user messages
    const userMessages = chats.filter(
      (msg) => msg.sender === "user"
    );

    // Get last 5 queries
    setRecentQueries(userMessages.slice(-5).reverse());
  }, []);

  return (
    <div className="bg-white shadow-md rounded-xl p-6 border">
      <h3 className="text-lg font-semibold mb-4">
        Recent Searches
      </h3>

      {recentQueries.length === 0 ? (
        <p className="text-slate-500 text-sm">
          No recent searches.
        </p>
      ) : (
        <ul className="space-y-3">
          {recentQueries.map((query, index) => (
            <li
              key={index}
              className="text-sm text-slate-700 bg-slate-50 p-2 rounded-lg"
            >
              {query.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default RecentSearches;
