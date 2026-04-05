/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  basePath: '/ui',
  assetPrefix: '/ui',
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
