/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  output: "standalone",
  // Shared contract types are consumed as TypeScript source from the workspace.
  transpilePackages: ["@nav/shared-types"],
};

export default nextConfig;
