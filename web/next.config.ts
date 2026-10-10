import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // This app lives in web/. Do not trace from a lockfile above the repo.
  outputFileTracingRoot: path.join(process.cwd()),
};

export default nextConfig;
