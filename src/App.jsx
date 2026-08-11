import { WorkspaceProvider } from './context/WorkspaceContext.jsx'
import Mast from './components/Mast.jsx'
import DishSidebar from './components/DishSidebar.jsx'
import Surface from './components/Surface.jsx'

export default function App() {
  return (
    <WorkspaceProvider>
      <Mast />
      <div className="shell">
        <DishSidebar />
        <Surface />
      </div>
    </WorkspaceProvider>
  )
}
