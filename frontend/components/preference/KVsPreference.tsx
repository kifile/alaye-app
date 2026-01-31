'use client';

import { useState, useCallback, useEffect, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Loader2, Plus, Trash2, Edit2, Check, X } from 'lucide-react';
import { toast } from 'sonner';
import log from '@/lib/log';
import { PreferenceWrapper } from './PreferenceWrapper';
import { useTranslation } from 'react-i18next';
import { loadAllComponentTranslations } from '@/lib/i18n';

// 编辑模式下输入框样式常量
const EDIT_INPUT_CLASS = 'h-8 rounded-md border border-slate-200 bg-white flex items-center justify-center px-2.5';
const EDIT_INPUT_TEXT_CLASS = 'w-full bg-transparent border-none outline-none text-[12px] text-slate-900 placeholder:text-slate-400';
const DELETE_BUTTON_CLASS = 'shrink-0 p-1.5 text-slate-400 hover:text-red-600 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed';
const DISPLAY_ROW_CLASS = 'flex items-center gap-3 h-8 rounded-md bg-slate-50 px-3';

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
  infoLink?: string;
}

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
  infoLink,
}: KVsPreferenceProps) {
  const { t } = useTranslation('preference');
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [showSaveConfirm, setShowSaveConfirm] = useState(false);
  const [isEditingMode, setIsEditingMode] = useState(false);
  const [tempKvPairs, setTempKvPairs] = useState<KVPair[]>([]);
  const [kvPairs, setKvPairs] = useState<KVPair[]>(() =>
    Object.entries(value).map(([key, val]) => ({ key, value: val }))
  );

  // Load translations on mount
  useEffect(() => {
    loadAllComponentTranslations('preference');
  }, []);

  // Use translated placeholders if not provided
  const finalKeyPlaceholder = keyPlaceholder || t('kvs.keyPlaceholder');
  const finalValuePlaceholder = valuePlaceholder || t('kvs.valuePlaceholder');

  useEffect(() => {
    const pairs = Object.entries(value).map(([key, val]) => ({ key, value: val }));
    setKvPairs(pairs);
    if (!isEditingMode) {
      setTempKvPairs(pairs);
    }
  }, [value, isEditingMode]);

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

  const enterEditMode = useCallback(() => {
    setTempKvPairs([...kvPairs]);
    setIsEditingMode(true);
  }, [kvPairs]);

  const cancelEditMode = useCallback(() => {
    setIsEditingMode(false);
    setTempKvPairs([]);
  }, []);

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
          toast.error(`${pair.key}: ${t('kvs.keyExists')}`);
          return false;
        }
      }
    }

    return true;
  }, [tempKvPairs, keyValidator, valueValidator, t]);

  const handleSaveAll = useCallback(() => {
    if (!validateAllPairs()) {
      return;
    }
    setShowSaveConfirm(true);
  }, [validateAllPairs]);

  const confirmSaveAll = useCallback(async () => {
    const success = await saveSetting(convertToString(tempKvPairs));

    if (success) {
      setKvPairs([...tempKvPairs]);
      setIsEditingMode(false);
      setShowSaveConfirm(false);
    }
  }, [saveSetting, convertToString, tempKvPairs]);

  const cancelSaveAll = useCallback(() => {
    setShowSaveConfirm(false);
  }, []);

  const addNewPair = useCallback(() => {
    if (maxItems && tempKvPairs.length >= maxItems) {
      toast.error(t('kvs.maxItemsError', { max: maxItems }));
      return;
    }
    setTempKvPairs([...tempKvPairs, { key: '', value: '' }]);
  }, [maxItems, tempKvPairs, t]);

  const handleAddAndEnterEditMode = useCallback(() => {
    if (kvPairs.length === 0) {
      // 空状态：进入编辑模式并自动添加一个空项
      setTempKvPairs([{ key: '', value: '' }]);
      setIsEditingMode(true);
    } else {
      // 有数据：只进入编辑模式
      enterEditMode();
    }
  }, [kvPairs, enterEditMode]);

  const deletePair = useCallback(
    (index: number) => {
      setTempKvPairs(tempKvPairs.filter((_, i) => i !== index));
    },
    [tempKvPairs]
  );

  const handleInputChange = useCallback(
    (index: number, field: keyof KVPair, inputValue: string) => {
      const newPairs = [...tempKvPairs];
      newPairs[index][field] = inputValue;
      setTempKvPairs(newPairs);
    },
    [tempKvPairs]
  );

  const currentPairs = isEditingMode ? tempKvPairs : kvPairs;
  const isMaxItemsReached = maxItems ? tempKvPairs.length >= maxItems : false;

  const rightElement = useMemo(() => {
    // 空状态：显示"添加配置项"按钮
    if (currentPairs.length === 0 && !isEditingMode) {
      return (
        <Button
          onClick={handleAddAndEnterEditMode}
          disabled={disabled || isSaving}
          size='sm'
          variant='outline'
          className='h-8 px-3 text-[12px] gap-1.5'
        >
          <Plus className='w-3 h-3' />
          {t('kvs.addConfigItem')}
        </Button>
      );
    }

    // 编辑模式：显示"取消"和"保存"按钮
    if (isEditingMode) {
      return (
        <div className='flex items-center gap-2'>
          <Button
            onClick={cancelEditMode}
            disabled={disabled || isSaving}
            size='sm'
            variant='outline'
            className='h-8 px-3 text-[12px] gap-1.5'
          >
            <X className='w-3 h-3' />
            {t('kvs.cancel')}
          </Button>
          <Button
            onClick={handleSaveAll}
            disabled={disabled || isSaving}
            size='sm'
            variant='default'
            className='h-8 px-3 text-[12px] gap-1.5 bg-slate-900 hover:bg-slate-800'
          >
            <Check className='w-3 h-3' />
            {t('kvs.save')}
          </Button>
        </div>
      );
    }

    // 有数据且非编辑模式：显示"编辑"按钮
    return (
      <Button
        onClick={enterEditMode}
        disabled={disabled || isSaving}
        size='sm'
        variant='outline'
        className='h-8 px-3 text-[12px] gap-1.5'
      >
        <Edit2 className='w-3 h-3' />
        {t('kvs.edit')}
      </Button>
    );
  }, [isEditingMode, currentPairs.length, cancelEditMode, handleSaveAll, enterEditMode, handleAddAndEnterEditMode, disabled, isSaving, t]);

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
      >
        {/* KVsPreference 不使用 children，内容独立展示 */}
      </PreferenceWrapper>

      {/* Content Area - Independent outside Wrapper */}
      {currentPairs.length === 0 && !isEditingMode ? (
        <div className='flex flex-col items-center justify-center gap-3 rounded-lg bg-slate-50 h-32 mt-2'>
          <div className='w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center'>
            <Plus className='w-5 h-5 text-slate-400' />
          </div>
          <p className='text-[13px] text-slate-500'>{t('kvs.noEnvironmentVariables')}</p>
          <p className='text-[12px] text-slate-400'>{t('kvs.noEnvironmentVariablesHint')}</p>
        </div>
      ) : (
        <div className='flex flex-col gap-1.5 mt-2'>
          {currentPairs.map((pair, index) => (
            <div key={index}>
              {isEditingMode ? (
                <div className='flex items-center gap-2'>
                  <div className={`${EDIT_INPUT_CLASS} w-[180px]`}>
                    <input
                      type='text'
                      value={pair.key}
                      onChange={e => handleInputChange(index, 'key', e.target.value)}
                      placeholder={finalKeyPlaceholder}
                      disabled={disabled || isSaving}
                      className={EDIT_INPUT_TEXT_CLASS}
                    />
                  </div>
                  <div className={`${EDIT_INPUT_CLASS} flex-1`}>
                    <input
                      type='text'
                      value={pair.value}
                      onChange={e => handleInputChange(index, 'value', e.target.value)}
                      placeholder={finalValuePlaceholder}
                      disabled={disabled || isSaving}
                      className={EDIT_INPUT_TEXT_CLASS}
                    />
                  </div>
                  <button
                    onClick={() => deletePair(index)}
                    disabled={disabled || isSaving}
                    className={DELETE_BUTTON_CLASS}
                    title={t('kvs.delete')}
                  >
                    <Trash2 className='w-3.5 h-3.5' />
                  </button>
                </div>
              ) : (
                <div className={DISPLAY_ROW_CLASS}>
                  <span className='text-[12px] font-medium font-mono text-slate-700'>{pair.key}</span>
                  <span className='text-[12px] text-slate-500'>{pair.value}</span>
                </div>
              )}
            </div>
          ))}

          {isEditingMode && (
            <button
              onClick={addNewPair}
              disabled={disabled || isSaving || isMaxItemsReached}
              className='flex items-center justify-center gap-2 h-8 rounded-md bg-slate-50 px-3 text-[12px] text-slate-400 border border-slate-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-100'
            >
              <Plus className='w-3.5 h-3.5' />
              {t('kvs.addNewItem', { itemType: t('kvs.environmentVariable') })}
            </button>
          )}
        </div>
      )}

      <Dialog open={showSaveConfirm} onOpenChange={setShowSaveConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('kvs.confirmSaveTitle')}</DialogTitle>
            <DialogDescription>
              {t('kvs.confirmSaveMessage')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant='outline' onClick={cancelSaveAll} disabled={isSaving}>
              {t('kvs.keepEditing')}
            </Button>
            <Button onClick={confirmSaveAll} disabled={isSaving}>
              {isSaving ? (
                <>
                  <Loader2 className='w-4 h-4 mr-2 animate-spin' />
                  {t('kvs.saving')}
                </>
              ) : (
                t('kvs.confirm')
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
