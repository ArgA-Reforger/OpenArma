'use client'

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { useI18n } from '@/lib/i18n'

interface DeleteConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  itemName: string
  onConfirm: () => void
  titleKey?: string
  descriptionKey?: string
}

export function DeleteConfirmDialog({
  open,
  onOpenChange,
  itemName,
  onConfirm,
  titleKey = 'error.confirmDelete',
  descriptionKey,
}: DeleteConfirmDialogProps) {
  const { t } = useI18n()

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t(titleKey)}</AlertDialogTitle>
          <AlertDialogDescription>
            {descriptionKey
              ? t(descriptionKey, { name: itemName })
              : `${itemName}`}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>
            {t('common.delete')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
