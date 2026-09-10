/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Every page fetches from the API in the browser, so there is nothing for a
  // Node server to do. `next build` writes a plain folder of HTML and assets
  // to out/, which FastAPI can serve directly or any static host can take.
  output: "export",
  // Directory-per-route (out/voyage/index.html) so static file servers resolve
  // deep links without extra rewrite rules.
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
