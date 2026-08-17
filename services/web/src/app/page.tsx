"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authApi } from "@/lib/api";

type UserRole = "superadmin" | "admin";

export default function AuthPage() {
  const router = useRouter();
  const [role, setRole] = useState<UserRole>("admin");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");
    
    try {
      const response = await authApi.login(username, password);
      console.log("Login successful:", response);
      
      // Redirect to dashboard on successful login
      router.push("/main/dashboard");
    } catch (err) {
      console.error("Login error:", err);
      setError(err instanceof Error ? err.message : "Login failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-md px-6">
        <div className="bg-card rounded-lg border border-border p-8 shadow-sm">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-2xl font-semibold text-foreground mb-2">
              Welcome Back
            </h1>
            <p className="text-sm text-muted-foreground">
              Sign in to your account
            </p>
          </div>

          {/* Role Selector */}
          <div className="flex gap-2 mb-6">
            <button
              type="button"
              onClick={() => setRole("admin")}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
                role === "admin"
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
              }`}
            >
              Admin
            </button>
            <button
              type="button"
              onClick={() => setRole("superadmin")}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
                role === "superadmin"
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
              }`}
            >
              Super Admin
            </button>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 rounded-md bg-red-50 border border-red-200">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}
            
            {/* Helper text */}
            <div className="p-3 rounded-md bg-blue-50 border border-blue-200">
              <p className="text-xs text-blue-600">
                Default credentials: <strong>admin / admin123</strong> or <strong>superadmin / superadmin123</strong>
              </p>
            </div>
            
            <div className="space-y-2">
              <label
                htmlFor="username"
                className="text-sm font-medium text-foreground"
              >
                Username
              </label>
              <Input
                id="username"
                type="text"
                placeholder="admin"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                disabled={isLoading}
                autoComplete="username"
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="password"
                className="text-sm font-medium text-foreground"
              >
                Password
              </label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            <Button
              type="submit"
              className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
              disabled={isLoading}
            >
              {isLoading ? "Signing in..." : "Sign In"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}