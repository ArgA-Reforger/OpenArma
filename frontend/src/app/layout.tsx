import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { ThemeProvider } from 'next-themes'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { QueryProvider } from '@/providers/query-provider'
import { I18nWrapper } from '@/providers/i18n-provider'
import { AuthGuardProvider } from '@/providers/auth-guard-provider'
import './globals.css'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'OpenArma',
  description: 'Configurable Multi-Agent Platform',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <QueryProvider>
            <I18nWrapper>
              <AuthGuardProvider>
                <TooltipProvider>
                  {children}
                  <Toaster />
                </TooltipProvider>
              </AuthGuardProvider>
            </I18nWrapper>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
