import { Suspense } from "react";
import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <div className="container narrow">
      <div className="card">
        <h1>Attorney sign in</h1>
        <p className="subtitle">Access the internal leads dashboard.</p>

        <Suspense fallback={null}>
          <LoginForm />
        </Suspense>

        <p className="muted" style={{ marginTop: 24 }}>
          <a href="/">← Back to application form</a>
        </p>
      </div>
    </div>
  );
}
