import type { NextConfig } from "next";

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        // When you call /api/v1/... on your frontend
        source: '/api/v1/:path*',
        // It proxy-passes to your backend IP
        destination: 'http://3.224.184.102:8000/api/v1/:path*',
      },
    ];
  },
};

export default nextConfig;