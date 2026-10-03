const path = require('path')

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Optimize webpack caching to reduce corruption issues
  webpack: (config, { dev, isServer }) => {
    config.resolve.alias['@'] = path.resolve(__dirname)
    
    // Reduce webpack cache issues in development
    if (dev) {
      config.cache = false
    }
    
    return config
  },
  // Add experimental features for Next.js 16 compatibility
  experimental: {
    // Optimize for development stability
    optimizePackageImports: ['lucide-react'],
  },
  // Allow webpack to work with Next.js 16
  turbopack: {},
}

module.exports = nextConfig
