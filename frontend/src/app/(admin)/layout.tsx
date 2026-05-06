'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore, useHydrated } from '@/stores/auth'
import { useApi } from '@/hooks/use-api'
import { useI18n } from '@/lib/i18n'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { ThemeToggle } from '@/components/theme-toggle'
import { LogoWithText } from '@/components/logo'

interface SidebarMenu {
  id: number
  name: string
  path: string | null
  type: number
  sort: number
  component: string | null
  meta: {
    title: string
    icon: string | null
    hideInMenu: boolean
    menuVisibleWithForbidden: boolean
  }
  children?: SidebarMenu[]
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, token, logout } = useAuthStore()
  const hydrated = useHydrated()
  const api = useApi()
  const { t } = useI18n()

  const { data: menuTree } = useQuery({
    queryKey: ['sidebar-menus'],
    queryFn: () => api.get<SidebarMenu[]>('/sys/menus/sidebar'),
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
  })

  useEffect(() => {
    if (!hydrated) return
    if (!token) {
      router.push('/login')
      return
    }
    if (user && !user.is_superuser && !user.is_staff) {
      router.push('/projects')
    }
  }, [hydrated, token, user, router])

  if (!hydrated || !token || (user && !user.is_superuser && !user.is_staff)) return null

  return (
    <div className="flex min-h-screen">
      <aside className="w-60 border-r bg-muted/40 p-4 flex flex-col">
        <Link href="/admin/dashboard" className="mb-1 block">
          <LogoWithText iconSize={22} textClassName="text-lg" />
        </Link>
        <span className="text-xs text-muted-foreground mb-6">{t('nav.backendAdmin')}</span>
        <nav className="space-y-1 flex-1 overflow-y-auto">
          {menuTree?.map((node) => (
            <MenuNode key={node.name} node={node} pathname={pathname} depth={0} />
          ))}
        </nav>
        <Separator className="my-2" />
        <Link
          href="/projects"
          className="block rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent/50 mb-2"
        >
          {t('nav.backToUser')}
        </Link>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground truncate">
            {user?.nickname || user?.username}
          </span>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                logout()
                router.push('/login')
              }}
            >
              {t('auth.logout')}
            </Button>
          </div>
        </div>
      </aside>
      <main className="flex-1 p-6">{children}</main>
    </div>
  )
}

function MenuNode({
  node,
  pathname,
  depth,
}: {
  node: SidebarMenu
  pathname: string
  depth: number
}) {
  const hasVisibleChildren = node.children?.some((c) => !c.meta.hideInMenu)
  const [expanded, setExpanded] = useState(true)

  if (node.meta.hideInMenu) return null

  if (node.type === 0 && hasVisibleChildren) {
    return (
      <div className={depth > 0 ? 'ml-3' : ''}>
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-1 px-3 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors"
        >
          <span className="text-[10px]">{expanded ? '▾' : '▸'}</span>
          {node.meta.title}
        </button>
        {expanded && (
          <div className="space-y-0.5">
            {node.children
              ?.filter((c) => !c.meta.hideInMenu)
              .map((child) => (
                <MenuNode key={child.name} node={child} pathname={pathname} depth={depth + 1} />
              ))}
          </div>
        )}
      </div>
    )
  }

  const href = node.path ?? '#'
  const isActive = href !== '#' && pathname.startsWith(href)

  return (
    <Link
      href={href}
      className={`block rounded-md px-3 py-1.5 text-sm transition-colors ${
        depth > 0 ? 'ml-3' : ''
      } ${
        isActive
          ? 'bg-accent text-accent-foreground font-medium'
          : 'hover:bg-accent/50'
      }`}
    >
      {node.meta.title}
    </Link>
  )
}
