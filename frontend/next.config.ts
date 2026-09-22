import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained server bundle (.next/standalone/server.js) for
  // production Docker deploys — only the traced runtime files are needed
  // in the final image (development behavior is unchanged).
  output: "standalone",
};

export default nextConfig;
