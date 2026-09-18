# Cache Management Guide

This project has experienced caching issues during development. Here's how to manage and resolve them.

## Available Scripts

The frontend package.json includes several cache management scripts:

- `npm run dev` - Normal development mode
- `npm run dev:clean` - Development with cache cleared
- `npm run build` - Normal production build
- `npm run build:clean` - Production build with cache cleared
- `npm run clean` - Clear all caches only

## When to Clear Cache

Clear the cache when you experience:
- Module resolution errors (e.g., "Cannot find module './819.js'")
- CSS not loading properly
- TypeScript configuration changes not taking effect
- Weird webpack errors during development
- Hot reload not working correctly

## Manual Cache Clearing

If scripts don't work, manually clear caches:

```bash
# Navigate to frontend directory
cd frontend

# Clear Next.js build cache
rm -rf .next

# Clear node modules cache
rm -rf node_modules/.cache

# Clear TypeScript cache
rm -rf *.tsbuildinfo

# Restart dev server
npm run dev
```

## Configuration Changes

The following configurations have been optimized to reduce caching issues:

### Next.js Configuration (next.config.js)
- Webpack caching disabled in development mode
- Package import optimization for lucide-react
- Experimental features optimized for stability

### TypeScript Configuration (tsconfig.json)
- Removed deprecated `baseUrl` option
- Updated paths configuration for modern TypeScript

## Prevention Tips

1. **Use clean scripts** when making major configuration changes
2. **Restart dev server** after tsconfig.json changes
3. **Avoid frequent configuration changes** during active development
4. **Monitor webpack errors** in the dev server console

## Troubleshooting

If cache issues persist:

1. Stop all running dev servers
2. Clear all caches manually
3. Delete node_modules and reinstall: `rm -rf node_modules && npm install`
4. Restart with clean build: `npm run dev:clean`

## Production Deployment

For production builds, always use:
```bash
npm run build:clean
```

This ensures a clean build without any cache artifacts from development.