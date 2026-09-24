import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  output: "standalone",
  headers() {
    return ["/", "/login", "/api/:path*"].map((source) => ({
      source,
      headers: [
        { key: "Cache-Control", value: "private, no-store, max-age=0" },
        { key: "Vary", value: "Cookie" },
      ],
    }));
  },
};

export default nextConfig;
