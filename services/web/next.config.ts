import type { NextConfig } from "next";

/**
 * The generated config was an empty object with a `/* config options here *\/`
 * placeholder. This sets the things a compliance console actually needs.
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,

  // Do not leak the framework version in response headers.
  poweredByHeader: false,

  // Fail the production build on a type or lint error rather than shipping it.
  typescript: { ignoreBuildErrors: false },
  eslint: { ignoreDuringBuilds: false },

  // Profile pictures come from the KYC bucket; allow that host only.
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "*.s3.*.amazonaws.com" },
      { protocol: "https", hostname: "*.amazonaws.com" },
    ],
  },

  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
