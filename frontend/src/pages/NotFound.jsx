import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-paper flex flex-col items-center justify-center text-center px-6">
      <p className="font-mono text-sm text-ink-faint mb-2">404</p>
      <h1 className="font-display text-2xl mb-4">This page doesn't exist.</h1>
      <Link to="/" className="text-amber-dark underline text-sm">Back to home</Link>
    </div>
  );
}
