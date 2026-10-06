import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Dev only: also serve the app on 127.0.0.1, so a second account can be signed in side by side
  // (cookies are per host, so localhost and 127.0.0.1 keep separate sessions).
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
