import { useTranslation } from 'react-i18next';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Home, Folder, User, Puzzle } from 'lucide-react';
import type { ConfigScope } from '@/api/types';

const SCOPE_ICONS = {
  user: Home,
  project: Folder,
  local: User,
  plugin: Puzzle,
};

interface ScopeBadgeProps {
  scope: ConfigScope;
  showLabel?: boolean;
  className?: string;
}

export function ScopeBadge({
  scope,
  showLabel = true,
  className = '',
}: ScopeBadgeProps) {
  const { t } = useTranslation('projects');
  const Icon = SCOPE_ICONS[scope] || SCOPE_ICONS.project;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge variant='outline' className={`gap-1 border-0 bg-transparent ${className}`}>
            <Icon className='w-3 h-3' />
            {showLabel && <span>{t(`detail.scopeBadge.${scope}.label`)}</span>}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p>{t(`detail.scopeBadge.${scope}.description`)}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
