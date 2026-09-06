import type { NextConfig } from "next";

// Where /api/* is proxied. Local dev talks to the FastAPI backend on :8000; a hosted
// backend is selected with NEXT_PUBLIC_BACKEND_URL. Static builds never call /api.
const backend = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
