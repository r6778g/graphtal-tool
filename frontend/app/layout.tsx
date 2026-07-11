import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Intraclone ML Prediction Demo',
  description: 'Dynamic ML prediction and visualization for bioprocess optimization',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
