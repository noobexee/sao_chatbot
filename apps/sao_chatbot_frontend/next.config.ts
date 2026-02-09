import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',

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