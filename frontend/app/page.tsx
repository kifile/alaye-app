'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Home page - Redirects to projects page
 * This page serves as a redirect to the main projects page
 */
export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to projects page
    router.push('/projects');
  }, [router]);

  // Show loading state while redirecting
  return (
    <div className='flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-black'>
      <div className='text-center'>
        <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-zinc-900 dark:border-zinc-50 mx-auto'></div>
        <p className='mt-4 text-zinc-600 dark:text-zinc-400'>Loading...</p>
      </div>
    </div>
  );
}
