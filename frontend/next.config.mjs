/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  ...(process.env.STANDALONE === 'true' ? { output: 'standalone' } : {}),
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://ecdat-backend-2bn6.onrender.com';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${apiUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
