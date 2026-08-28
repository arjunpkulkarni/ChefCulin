import { WorkspaceProvider } from './context/WorkspaceContext.jsx'
import Mast from './components/Mast.jsx'
import DishSidebar from './components/DishSidebar.jsx'
import Surface from './components/Surface.jsx'

export default function App({ initialFocus = null }) {
  return (
    <WorkspaceProvider initialFocus={initialFocus}>
      <Mast />
      <div className="shell">
        <DishSidebar />
        <Surface />
      </div>
    </WorkspaceProvider>
  )
}
