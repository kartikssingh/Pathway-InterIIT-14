"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

import { Button } from "@/components/ui/button";

/**
 * Catches render-time exceptions so one broken panel does not blank the console.
 *
 * The application had no boundary at all: any component that dereferenced a
 * field the API had not returned unmounted the whole page tree and left an
 * empty white screen with the reason only in the browser console.
 */

interface Props {
  children: ReactNode;
  /** Shown instead of the default panel. */
  fallback?: (error: Error, reset: () => void) => ReactNode;
  /** Human-readable name of the section being guarded. */
  label?: string;
  onError?: (error: Error, info: ErrorInfo) => void;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (process.env.NODE_ENV !== "production") {
      console.error(`[ErrorBoundary${this.props.label ? `: ${this.props.label}` : ""}]`, error, info);
    }
    this.props.onError?.(error, info);
  }

  reset = (): void => this.setState({ error: null });

  render(): ReactNode {
    const { error } = this.state;
    if (!error) return this.props.children;
    if (this.props.fallback) return this.props.fallback(error, this.reset);

    return (
      <div
        role="alert"
        className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm dark:border-red-900 dark:bg-red-950"
      >
        <h2 className="mb-1 font-semibold text-red-800 dark:text-red-200">
          {this.props.label ? `${this.props.label} failed to render` : "Something went wrong"}
        </h2>
        <p className="mb-4 text-red-700 dark:text-red-300">
          The rest of the console is still usable. Try again, or reload the page.
        </p>
        {process.env.NODE_ENV !== "production" && (
          <pre className="mb-4 max-h-40 overflow-auto rounded bg-red-100 p-3 text-xs text-red-900 dark:bg-red-900/40 dark:text-red-100">
            {error.message}
          </pre>
        )}
        <Button variant="outline" size="sm" onClick={this.reset}>
          Try again
        </Button>
      </div>
    );
  }
}

export default ErrorBoundary;
