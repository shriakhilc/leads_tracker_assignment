/** @type {import('next').NextConfig} */
const nextConfig = {
  // Standalone output → small production image (§9).
  output: "standalone",
  reactStrictMode: true,
  // ESLint config isn't bundled into the image; don't block the production build on it.
  eslint: { ignoreDuringBuilds: true },
};

module.exports = nextConfig;
