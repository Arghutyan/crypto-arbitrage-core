/** @type {import('next').NextConfig} */
const nextConfig = {
  // Emit a minimal standalone server bundle for small production Docker images.
  output: "standalone",
  reactStrictMode: true,
};

export default nextConfig;
