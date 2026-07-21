import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

export default function LogoutBar({ username }) {
  const navigate = useNavigate();

  async function handleLogout() {
    try {
      await api.logout();
    } catch (err) {
      console.error("[logout]", err.message);
    }
    navigate("/auth");
  }

  return (
    <div className="topbar">
      <div className="topbar-brand">
        <svg width="28" height="28" viewBox="0 0 40 40" fill="none">
          <rect width="40" height="40" rx="10" fill="#1A2E4A" />
          <path d="M8 28 L20 12 L32 28" stroke="#F59E0B" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          <path d="M14 22 L26 22" stroke="#F59E0B" strokeWidth="2.5" strokeLinecap="round" />
        </svg>
        <span className="topbar-brand-name">CV-Sync</span>
      </div>
      <div className="topbar-right">
        {username && <span className="username">@{username}</span>}
        <button className="logout-btn" onClick={handleLogout}>Log out</button>
      </div>
    </div>
  );
}
