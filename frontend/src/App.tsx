import { Routes, Route } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { DashboardPage } from '@/pages/DashboardPage'
import { ConversationsPage } from '@/pages/ConversationsPage'
import { EvaluationsPage } from '@/pages/EvaluationsPage'
import { JobsPage } from '@/pages/JobsPage'
import { MetaEvaluationPage } from '@/pages/MetaEvaluationPage'
import { RubricsPage } from '@/pages/RubricsPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="conversations" element={<ConversationsPage />} />
        <Route path="evaluations" element={<EvaluationsPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="meta-evaluation" element={<MetaEvaluationPage />} />
        <Route path="rubrics" element={<RubricsPage />} />
      </Route>
    </Routes>
  )
}

export default App
