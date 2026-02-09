import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',

  async rewrites() {
    return [
      {
        // This maps frontend calls to your backend
        source: '/api/v1/:path*',
        destination: 'http://3.224.184.102:8000/api/v1/:path*',
      },
    ];
  },
};

export default nextConfig;