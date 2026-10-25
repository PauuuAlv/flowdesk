import { routes, type VercelConfig } from '@vercel/config/v1';

const backendOrigin = (process.env['FLOWDESK_BACKEND_URL'] || 'https://backend-pendiente.invalid')
  .trim()
  .replace(/\/+$/, '');

export const config: VercelConfig = {
  buildCommand: 'npm run build',
  outputDirectory: 'dist/app/browser',
  rewrites: [
    routes.rewrite('/health', `${backendOrigin}/health`),
    routes.rewrite('/api/:path*', `${backendOrigin}/api/:path*`),
    routes.rewrite('/:path*', '/index.html'),
  ],
};
