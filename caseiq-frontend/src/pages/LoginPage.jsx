import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate, Link } from "react-router-dom";
import bgImage from "../assets/download.png";

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.error || "Invalid email or password.");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: "100%",
    padding: "14px 16px",
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(212,175,55,0.25)",
    borderRadius: "12px",
    color: "#E5E5E5",
    outline: "none",
    fontSize: "14px",
    transition: "all 0.2s",
  };

  const handleInputFocus = (e) => {
    e.target.style.borderColor = "#FFD700";
    e.target.style.boxShadow = "0 0 0 3px rgba(212,175,55,0.15)";
  };

  const handleInputBlur = (e) => {
    e.target.style.borderColor = "rgba(212,175,55,0.25)";
    e.target.style.boxShadow = "none";
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background:
          "radial-gradient(ellipse at 50% 0%, rgba(212,175,55,0.12) 0%, #0B0B0B 60%)",
        padding: "20px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* 🔥 GOLD BACKGROUND IMAGE */}
      <img
        src={bgImage}
        alt="legal emblem"
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: "600px",
          opacity: 0.06,
          filter: "blur(1px)",
          pointerEvents: "none",
          zIndex: 0,
        }}
      />

      {/* ✨ GOLD GLOW */}
      <div
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: "700px",
          height: "700px",
          background:
            "radial-gradient(circle, rgba(212,175,55,0.08), transparent 70%)",
          pointerEvents: "none",
          zIndex: 1,
        }}
      />

      {/* LOGIN CARD */}
      <div
        style={{
          background: "rgba(17,17,17,0.75)",
          border: "1px solid rgba(212,175,55,0.25)",
          borderRadius: "24px",
          padding: "48px",
          width: "100%",
          maxWidth: "440px",
          backdropFilter: "blur(20px)",
          boxShadow:
            "0 30px 80px rgba(0,0,0,0.7), 0 0 20px rgba(212,175,55,0.1)",
          position: "relative",
          zIndex: 10,
        }}
      >
        {/* TOP GOLD LINE */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: "15%",
            right: "15%",
            height: "1px",
            background:
              "linear-gradient(90deg, transparent, #D4AF37, transparent)",
          }}
        />

        {/* LOGO */}
        <div style={{ textAlign: "center", marginBottom: "36px" }}>
          <div
            style={{
              width: "60px",
              height: "60px",
              borderRadius: "18px",
              background: "linear-gradient(135deg, #D4AF37, #FFD700)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 16px",
              boxShadow: "0 8px 30px rgba(212,175,55,0.4)",
              fontSize: "28px",
            }}
          >
            ⚖️
          </div>

          <h1
            style={{
              fontSize: "32px",
              fontWeight: "800",
              fontFamily: "'Georgia', serif",
              background: "linear-gradient(135deg, #D4AF37, #FFD700)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              marginBottom: "6px",
            }}
          >
            CaseIQ
          </h1>

          <p style={{ color: "#A1A1AA", fontSize: "13px" }}>
            AI-Powered Legal Knowledge Platform
          </p>
        </div>

        {/* ERROR */}
        {error && (
          <div
            style={{
              background: "rgba(239,68,68,0.1)",
              border: "1px solid rgba(239,68,68,0.3)",
              color: "#FCA5A5",
              fontSize: "13px",
              borderRadius: "10px",
              padding: "12px 16px",
              marginBottom: "20px",
            }}
          >
            {error}
          </div>
        )}

        {/* FORM */}
        <form
          onSubmit={handleLogin}
          style={{ display: "flex", flexDirection: "column", gap: "14px" }}
        >
          <input
            type="email"
            placeholder="Email Address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={inputStyle}
            onFocus={handleInputFocus}
            onBlur={handleInputBlur}
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={inputStyle}
            onFocus={handleInputFocus}
            onBlur={handleInputBlur}
          />

          <div style={{ textAlign: "right" }}>
            <Link
              to="/forgot-password"
              style={{
                fontSize: "13px",
                color: "#A1A1AA",
                textDecoration: "none",
              }}
            >
              Forgot password?
            </Link>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "14px",
              background: "linear-gradient(135deg, #D4AF37, #FFD700)",
              border: "none",
              borderRadius: "12px",
              color: "#0B0B0B",
              fontWeight: "700",
              cursor: "pointer",
              transition: "all 0.2s",
              boxShadow: "0 6px 25px rgba(212,175,55,0.5)",
            }}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        {/* DIVIDER */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            margin: "24px 0",
          }}
        >
          <div style={{ flex: 1, height: "1px", background: "#333" }} />
          <span style={{ color: "#A1A1AA", fontSize: "13px" }}>or</span>
          <div style={{ flex: 1, height: "1px", background: "#333" }} />
        </div>

        {/* GUEST */}
        <button
          onClick={() => navigate("/")}
          style={{
            width: "100%",
            padding: "13px",
            background: "transparent",
            border: "1px solid rgba(212,175,55,0.3)",
            borderRadius: "12px",
            color: "#C5A46D",
            cursor: "pointer",
          }}
        >
          Continue as Guest
        </button>

        {/* REGISTER */}
        <p
          style={{
            textAlign: "center",
            fontSize: "13px",
            marginTop: "20px",
            color: "#A1A1AA",
          }}
        >
          Don't have an account?{" "}
          <Link to="/register" style={{ color: "#FFD700" }}>
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
