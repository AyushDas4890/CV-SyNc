import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

// Shown on every page reached after login. Calls the real /api/auth/logout
// (destroys the Redis session server-side, not just a client-side redirect).
export default function LogoutBar({ username }) {
  const navigate = useNavigate();

  async function handleLogout() {
    try {
      await api.logout();
    } catch (err) {
      // logout endpoint failing shouldn't trap the user on the page —
      // send them to /auth regardless, a stale cookie will just 401 there
      console.error("[logout]", err.message);
    }
    navigate("/auth");
  }

  return (
    <div className="topbar">
      <span className="username">{username ? `@${username}` : ""}</span>
      <button className="logout-btn" onClick={handleLogout}>Log out</button>
    </div>
  );
}
