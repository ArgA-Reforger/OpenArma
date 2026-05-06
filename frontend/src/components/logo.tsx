import Image from 'next/image'

interface LogoIconProps {
  size?: number
  className?: string
}

export function LogoIcon({ size = 28, className }: LogoIconProps) {
  return (
    <Image
      src="/logo.svg"
      alt="OpenArma"
      width={size}
      height={size}
      className={className}
      priority
    />
  )
}

interface LogoWithTextProps {
  iconSize?: number
  className?: string
  textClassName?: string
}

export function LogoWithText({ iconSize = 24, className, textClassName }: LogoWithTextProps) {
  return (
    <span className={`inline-flex items-center gap-2 ${className ?? ''}`}>
      <LogoIcon size={iconSize} />
      <span className={`font-bold ${textClassName ?? ''}`}>
        <span className="font-extrabold">OPEN</span>
        <span className="font-light text-muted-foreground">ARMA</span>
      </span>
    </span>
  )
}
