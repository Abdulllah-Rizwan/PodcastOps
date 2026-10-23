/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The FastAPI backend base URL; defaults to local dev.
  env: {
    API_BASE_URL: process.env.API_BASE_URL || "http://localhost:8000",
  },
};

module.exports = nextConfig;
