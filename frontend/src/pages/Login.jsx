import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../services/api";
import { Button } from "../components/ui/Primitives";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("demo@student.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(getErrorMessage(err, "Invalid email or password."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <Link to="/" className="font-display text-lg block text-center mb-8">
          Placement Coach
        </Link>
        <div className="bg-paper-panel border border-paper-line rounded-card p-8 tick-corner">
          <h1 className="font-display text-xl mb-1">Welcome back</h1>
          <p className="text-sm text-ink-faint mb-6">Log in to continue your preparation.</p>

          {error && (
            <div className="mb-4 text-sm text-clay bg-clay/5 border border-clay/20 rounded-card px-3 py-2">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium text-ink block mb-1">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-paper-line rounded-card px-3 py-2.5 text-sm focus-ring outline-none"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-ink block mb-1">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border border-paper-line rounded-card px-3 py-2.5 text-sm focus-ring outline-none"
                placeholder="••••••••"
              />
            </div>
            <Button type="submit" variant="accent" className="w-full" disabled={loading}>
              {loading ? "Logging in..." : "Log in"}
            </Button>
          </form>

          <p className="text-xs text-ink-faint mt-4 text-center">
            Demo login: <span className="font-mono">demo@student.com</span> /{" "}
            <span className="font-mono">Demo@1234</span>
          </p>
        </div>
        <p className="text-sm text-center text-ink-faint mt-6">
          New here?{" "}
          <Link to="/register" className="text-amber-dark underline">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
