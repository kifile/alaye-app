'use client';

import { useState, useCallback, useEffect, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Loader2, Plus, Trash2, Edit2, Check, X } from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { loadComponentTranslations, getCurrentLanguage } from '@/lib/i18n';
import log from '@/lib/log';
import { PreferenceWrapper } from './PreferenceWrapper';

interface KVPair {
  key: string;
  value: string;
}

interface KVsPreferenceProps {
  title: string | React.ReactNode;
  description?: string | React.ReactNode;
  value: Record<string, string>;
  settingKey: string;
  onSettingChange: (key: string, value: string) => Promise<boolean>;
  disabled?: boolean;
  keyPlaceholder?: string;
  valuePlaceholder?: string;
  allowEmptyValues?: boolean;
  maxItems?: number;
  keyValidator?: (key: string) => string | null;
  valueValidator?: (value: string) => string | null;
  itemHeight?: 'sm' | 'default' | 'lg';
  infoLink?: string;
  prefix?: React.ReactNode;
}

const INPUT_SIZE_STYLES = {
  sm: 'text-sm px-2 py-1 h-8',
  default: 'px-3 py-2 h-10',
  lg: 'text-lg px-4 py-3 h-12',
} as const;

export function KVsPreference({
  title,
  description,
  value,
  settingKey,
  onSettingChange,
  disabled = false,
  keyPlaceholder,
  valuePlaceholder,
  allowEmptyValues = false,
  maxItems,
  keyValidator,
  valueValidator,
  itemHeight = 'default',
  infoLink,
  prefix,
}: KVsPreferenceProps) {
  loadComponentTranslations('preference', getCurrentLanguage());

  const { t } = useTranslation('preference');
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [showSaveConfirm, setShowSaveConfirm] = useState(false);
  const [isEditingMode, setIsEditingMode] = useState(false);
  const [tempKvPairs, setTempKvPairs] = useState<KVPair[]>([]);
  const [kvPairs, setKvPairs] = useState<KVPair[]>(() =>
    Object.entries(value).map(([key, val]) => ({ key, value: val }))
  );

  // 监听 value prop 的变化，更新内部状态
  useEffect(() => {
    const pairs = Object.entries(value).map(([key, val]) => ({ key, value: val }));
    setKvPairs(pairs);
    if (!isEditingMode) {
      setTempKvPairs(pairs);
    }
  }, [value, isEditingMode]);

  // 缓存计算值
  const inputSizeClass = INPUT_SIZE_STYLES[itemHeight];
  const currentPairs = isEditingMode ? tempKvPairs : kvPairs;
  const isPairsEmpty = currentPairs.length === 0;
  const isMaxItemsReached = maxItems ? tempKvPairs.length >= maxItems : false;
  const keyPlaceholderText = keyPlaceholder || t('kvs.keyPlaceholder');
  const valuePlaceholderText = valuePlaceholder || t('kvs.valuePlaceholder');

  // 将状态转换为对象字符串
  const convertToString = useCallback(
    (pairs: KVPair[]) => {
      const obj: Record<string, string> = {};
      pairs.forEach(pair => {
        if (pair.key && (allowEmptyValues || pair.value)) {
          obj[pair.key] = pair.value;
        }
      });
      return JSON.stringify(obj);
    },
    [allowEmptyValues]
  );

  // 保存配置到后端
  const saveSetting = useCallback(
    async (newValue: string) => {
      try {
        setIsSaving(true);
        setSaveError(false);
        const success = await onSettingChange(settingKey, newValue);

        if (success) {
          setSaveError(false);
          return true;
        }
        setSaveError(true);
        return false;
      } catch (error) {
        setSaveError(true);
        log.error(`${t('kvs.saveFailed')}: ${error}`);
        return false;
      } finally {
        setIsSaving(false);
      }
    },
    [onSettingChange, settingKey, t]
  );

  // 进入编辑模式
  const enterEditMode = useCallback(() => {
    setTempKvPairs([...kvPairs]);
    setIsEditingMode(true);
  }, [kvPairs]);

  // 取消编辑模式
  const cancelEditMode = useCallback(() => {
    setIsEditingMode(false);
  }, []);

  // 验证所有键值对
  const validateAllPairs = useCallback((): boolean => {
    for (let i = 0; i < tempKvPairs.length; i++) {
      const pair = tempKvPairs[i];

      if (keyValidator && pair.key) {
        const keyError = keyValidator(pair.key);
        if (keyError) {
          toast.error(`${t('kvs.key')}: ${keyError}`);
          return false;
        }
      }

      if (valueValidator) {
        const valueError = valueValidator(pair.value);
        if (valueError) {
          toast.error(`${pair.key || t('kvs.key')}: ${valueError}`);
          return false;
        }
      }

      if (pair.key) {
        const isDuplicate = tempKvPairs.some((p, j) => j !== i && p.key === pair.key);
        if (isDuplicate) {
          toast.error(`${pair.key}: ${t('kvs.duplicateKey')}`);
          return false;
        }
      }
    }

    return true;
  }, [tempKvPairs, keyValidator, valueValidator, t]);

  // 保存所有更改
  const handleSaveAll = useCallback(() => {
    if (!validateAllPairs()) {
      return;
    }
    setShowSaveConfirm(true);
  }, [validateAllPairs]);

  // 确认保存
  const confirmSaveAll = useCallback(async () => {
    const success = await saveSetting(convertToString(tempKvPairs));

    if (success) {
      setKvPairs([...tempKvPairs]);
      setIsEditingMode(false);
      setShowSaveConfirm(false);
    }
  }, [saveSetting, convertToString, tempKvPairs]);

  // 取消保存
  const cancelSaveAll = useCallback(() => {
    setShowSaveConfirm(false);
  }, []);

  // 添加新的键值对
  const addNewPair = useCallback(() => {
    if (isMaxItemsReached) {
      toast.error(t('kvs.maxItemsError', { max: maxItems }));
      return;
    }
    setTempKvPairs([...tempKvPairs, { key: '', value: '' }]);
  }, [isMaxItemsReached, maxItems, tempKvPairs, t]);

  // 删除键值对
  const deletePair = useCallback(
    (index: number) => {
      setTempKvPairs(tempKvPairs.filter((_, i) => i !== index));
    },
    [tempKvPairs]
  );

  // 处理输入变化
  const handleInputChange = useCallback(
    (index: number, field: keyof KVPair, inputValue: string) => {
      const newPairs = [...tempKvPairs];
      newPairs[index][field] = inputValue;
      setTempKvPairs(newPairs);
    },
    [tempKvPairs]
  );

  // 右上角按钮区域
  const rightElement = useMemo(() => {
    const buttonClass = 'h-8';
    const iconClass = 'w-3 h-3 mr-1';

    if (isEditingMode) {
      return (
        <div className='flex items-center gap-2'>
          <Button
            onClick={handleSaveAll}
            disabled={disabled || isSaving}
            size='sm'
            variant='default'
            className={buttonClass}
          >
            <Check className={iconClass} />
            {t('kvs.save')}
          </Button>
          <Button
            onClick={cancelEditMode}
            disabled={disabled || isSaving}
            size='sm'
            variant='outline'
            className={buttonClass}
          >
            <X className={iconClass} />
            {t('kvs.cancel')}
          </Button>
        </div>
      );
    }

    return (
      <Button
        onClick={enterEditMode}
        disabled={disabled || isSaving}
        size='sm'
        variant='outline'
        className={buttonClass}
      >
        <Edit2 className={iconClass} />
        {t('kvs.edit')}
      </Button>
    );
  }, [
    isEditingMode,
    handleSaveAll,
    cancelEditMode,
    enterEditMode,
    disabled,
    isSaving,
    t,
  ]);

  // 渲染单个列表项
  const renderListItem = useCallback(
    (pair: KVPair, index: number) => (
      <div key={index} className='flex items-center gap-2'>
        {isEditingMode ? (
          <>
            <Input
              value={pair.key}
              onChange={e => handleInputChange(index, 'key', e.target.value)}
              placeholder={keyPlaceholderText}
              disabled={disabled || isSaving}
              className={`flex-1 font-mono font-medium ${inputSizeClass}`}
              style={{
                fontFamily:
                  'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
              }}
            />
            <Input
              value={pair.value}
              onChange={e => handleInputChange(index, 'value', e.target.value)}
              placeholder={valuePlaceholderText}
              disabled={disabled || isSaving}
              className={`flex-1 ${inputSizeClass}`}
            />
            <Button
              onClick={() => deletePair(index)}
              disabled={disabled || isSaving}
              size='sm'
              variant='outline'
              className='h-8 px-2 text-red-600 hover:text-red-700 hover:bg-red-50'
            >
              <Trash2 className='w-3 h-3' />
            </Button>
          </>
        ) : (
          <div className='flex-1 min-w-0'>
            <div className='font-mono text-sm truncate'>{pair.key}</div>
            <div className='text-xs text-muted-foreground truncate'>{pair.value}</div>
          </div>
        )}
      </div>
    ),
    [
      isEditingMode,
      handleInputChange,
      deletePair,
      keyPlaceholderText,
      valuePlaceholderText,
      inputSizeClass,
      disabled,
      isSaving,
    ]
  );

  // 渲染空状态
  const renderEmptyState = useCallback(
    () => (
      <div className='text-center py-6 text-muted-foreground border-2 border-dashed border-gray-300 rounded-lg'>
        <div className='text-sm'>{t('kvs.noItems')}</div>
        <div className='text-xs mt-1'>{t('kvs.noItemsHint')}</div>
      </div>
    ),
    [t]
  );

  return (
    <>
      <PreferenceWrapper
        title={title}
        description={description}
        infoLink={infoLink}
        disabled={disabled}
        saveError={saveError}
        isSaving={isSaving}
        rightElement={rightElement}
        className='space-y-3'
        prefix={prefix}
      >
        <div className='space-y-2'>
          {currentPairs.map(renderListItem)}

          {isPairsEmpty && renderEmptyState()}

          {isEditingMode && (
            <Button
              onClick={addNewPair}
              disabled={disabled || isSaving || isMaxItemsReached}
              size='sm'
              variant='outline'
              className='w-full h-8'
            >
              <Plus className='w-3 h-3 mr-1' />
              {t('kvs.add')}
            </Button>
          )}
        </div>
      </PreferenceWrapper>

      <Dialog open={showSaveConfirm} onOpenChange={setShowSaveConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('kvs.unsavedChanges')}</DialogTitle>
            <DialogDescription>{t('kvs.unsavedChangesMessage')}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant='outline' onClick={cancelSaveAll} disabled={isSaving}>
              {t('kvs.keepEditing')}
            </Button>
            <Button onClick={confirmSaveAll} disabled={isSaving}>
              {isSaving ? (
                <>
                  <Loader2 className='w-4 h-4 mr-2 animate-spin' />
                  {t('kvs.save')}
                </>
              ) : (
                t('kvs.save')
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
