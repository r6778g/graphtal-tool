'use client'

import Link from 'next/link'
import { 
  TrendingUp, 
  Filter, 
  TestTube, 
  Scale, 
  BarChart3, 
  Activity 
} from 'lucide-react'

export default function Home() {
  const tools = [
    // Row 1
    {
      id: 'upstream',
      title: 'Upstream Modeling',
      description: 'Predictive modeling tools',
      icon: TrendingUp,
      href: '/upstream'
    },
    {
      id: 'downstream',
      title: 'Downstream Modeling',
      description: 'Purification & chromatography tools',
      icon: Filter,
      href: '/upstream'
    },
    {
      id: 'formulation',
      title: 'Formulation',
      description: 'Formulation & fill-finish analytics',
      icon: TestTube,
      href: '/formulation'
    },
    // Row 2
    {
      id: 'scale-up',
      title: 'Scale up/Scale insights',
      description: 'Optimize your bioprocess scaling',
      icon: Scale,
      href: '/upstream'
    },
    {
      id: 'apqr',
      title: 'Annual Product Quality Review (APQR)',
      description: 'APQR reporting and analysis',
      icon: BarChart3,
      href: '/upstream'
    },
    {
      id: 'process-economics',
      title: 'Process Economics',
      description: 'Analyze cost and efficiency',
      icon: Activity,
      href: '/upstream'
    }
  ]

  return (
    <div className="min-h-screen bg-[#faf8f5] text-[#1b2535] flex flex-col justify-between relative overflow-hidden font-sans">
      {/* Soft Ambient Background Light Effect */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-amber-200/30 blur-[120px] rounded-full pointer-events-none -translate-x-1/3 -translate-y-1/3" />
      <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-amber-200/40 blur-[140px] rounded-full pointer-events-none translate-x-1/4 translate-y-1/4" />

      {/* Main Container */}
      <main className="container mx-auto px-4 py-16 flex-1 flex flex-col items-center justify-center max-w-6xl relative z-10">

        {/* Logo and Title Row */}
        <div className="flex items-center gap-4 mb-6">
          {/* Logo Box */}
          <div className="w-20 h-20 rounded-[22px] bg-[#f2ebe2] border border-[#e5dcd0] flex items-center justify-center shadow-xs">
            <img
              src="/logo.svg"
              alt="Graphtal Tool Logo"
              className="w-10 h-10"
            />
          </div>

          {/* Title */}
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-[#1e293b]">
            Graphtal <span className="text-[#d97706]">Toolbox</span>
          </h1>
        </div>

        {/* Description Paragraph */}
        <p className="text-center text-[#475569] max-w-xl text-xs sm:text-sm leading-relaxed mb-12 font-normal">
          Unleash the power of advanced machine learning with our Next generation Toolbox. 
          This cloud based application, effortlessly, revolutionizes how you scale-up, 
          process economics and bioprocess modelling.
        </p>

        {/* 6 Tool Cards Grid (3 Columns x 2 Rows) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-5xl">
          {tools.map((tool) => {
            const Icon = tool.icon
            return (
              <Link
                key={tool.id}
                href={tool.href}
                className="group bg-[#f4efe8] hover:bg-[#eee7dc] transition-all duration-300 rounded-[22px] p-8 flex flex-col items-center text-center justify-center min-h-[190px] border border-[#e8dfd3]/70 shadow-2xs hover:shadow-md cursor-pointer"
              >
                {/* Two-Tone Icon Container */}
                <div className="mb-4 relative flex items-center justify-center">
                  <Icon className="w-9 h-9 text-[#1e293b] stroke-[1.75]" />
                  {/* Subtle orange accent bar/dot for APQR bar chart or icons */}
                  {tool.id === 'apqr' && (
                    <div className="absolute right-0 bottom-0 w-2 h-5 bg-[#d97706] rounded-xs" />
                  )}
                </div>

                <h3 className="font-bold text-base text-[#1e293b] mb-1.5 leading-snug">
                  {tool.title}
                </h3>

                <p className="text-xs text-[#64748b] leading-relaxed">
                  {tool.description}
                </p>
              </Link>
            )
          })}
        </div>
      </main>

      {/* Minimal Footer */}
      <footer className="py-6 text-center text-xs text-[#94a3b8]">
        <p>© 2026 Graphtal Tool • Bioprocess Intelligence Platform</p>
      </footer>
    </div>
  )
}
