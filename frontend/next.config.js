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
  // Disable experimental features that might cause caching issues
  experimental: {
    // Optimize for development stability
    optimizePackageImports: ['lucide-react'],
  },
}

module.exports = nextConfig
