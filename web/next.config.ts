import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // This app lives in web/. Do not trace from a lockfile above the repo.
  outputFileTracingRoot: path.join(process.cwd()),
  experimental: {
    // SegmentViewNode is missing from the client manifest after overlapping
    // dev compiles, which 500s GET /. Leave that devtool off.
    devtoolSegmentExplorer: false,
  },
};

export default nextConfig;
