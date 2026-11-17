import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../services/api";
import { Button } from "../components/ui/Primitives";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setLoading(true);
    try {
      await register(form.name, form.email, form.password);
      navigate("/dashboard");
    } catch (err) {
      setError(getErrorMessage(err, "Could not create your account."));
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
          <h1 className="font-display text-xl mb-1">Create your account</h1>
          <p className="text-sm text-ink-faint mb-6">Start your first mock interview in minutes.</p>

          {error && (
            <div className="mb-4 text-sm text-clay bg-clay/5 border border-clay/20 rounded-card px-3 py-2">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium text-ink block mb-1">Full name</label>
              <input
                name="name"
                required
                value={form.name}
                onChange={handleChange}
                className="w-full border border-paper-line rounded-card px-3 py-2.5 text-sm focus-ring outline-none"
                placeholder="Jane Student"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-ink block mb-1">Email</label>
              <input
                type="email"
                name="email"
                required
                value={form.email}
                onChange={handleChange}
                className="w-full border border-paper-line rounded-card px-3 py-2.5 text-sm focus-ring outline-none"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-ink block mb-1">Password</label>
              <input
                type="password"
                name="password"
                required
                value={form.password}
                onChange={handleChange}
                className="w-full border border-paper-line rounded-card px-3 py-2.5 text-sm focus-ring outline-none"
                placeholder="At least 6 characters"
              />
            </div>
            <Button type="submit" variant="accent" className="w-full" disabled={loading}>
              {loading ? "Creating account..." : "Create account"}
            </Button>
          </form>
        </div>
        <p className="text-sm text-center text-ink-faint mt-6">
          Already registered?{" "}
          <Link to="/login" className="text-amber-dark underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
