const backendOrigin = (process.env['FLOWDESK_BACKEND_URL'] || 'https://backend-pendiente.invalid')
  .trim()
  .replace(/\/+$/, '');

export const config = {
  buildCommand: 'npm run build',
  outputDirectory: 'dist/app/browser',
  rewrites: [
    {
      source: '/api/:path*',
      destination: `${backendOrigin}/api/:path*`,
    },
    {
      source: '/:path*',
      destination: '/index.html',
    },
  ],
};
