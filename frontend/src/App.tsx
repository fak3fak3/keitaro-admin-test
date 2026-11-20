import { Link, Route, Routes } from 'react-router'

import { CampaignsPage } from '@/pages/CampaignsPage'

export function AppRoutes() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <nav className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
          <Link to="/" className="font-semibold">
            Keitaro wrapper
          </Link>
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Routes>
          <Route path="/" element={<CampaignsPage />} />
        </Routes>
      </main>
    </div>
  )
}
