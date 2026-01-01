import React from 'react';

interface GroupWrapperProps {
  children: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: string;
  className?: string;
}

export function GroupWrapper({
  children,
  title,
  subtitle,
  className = '',
}: GroupWrapperProps) {
  return (
    <div className={`border border-gray-200 rounded-lg p-4 space-y-4 ${className}`}>
      {(title || subtitle) && (
        <div className='flex items-center justify-between border-b border-gray-100 pb-2 mb-2'>
          <div>
            {title && <h4 className='text-md font-medium text-gray-900'>{title}</h4>}
            {subtitle && <p className='text-sm text-gray-500'>{subtitle}</p>}
          </div>
        </div>
      )}
      {children}
    </div>
  );
}
