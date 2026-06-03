import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 代理 /api/* 到 FastAPI 后端（开发时 :3000 → :8000，避免 CORS）
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
