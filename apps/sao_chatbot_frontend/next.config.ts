import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  // Add this experimental block
  experimental: {
    proxyTimeout: 600000, // 10 minutes in milliseconds
  },
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://backend:8000/api/v1/:path*',
      },
    ];
  },
};

export default nextConfig;