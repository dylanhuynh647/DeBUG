import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import logoIcon from '../assets/NavBar/logo-icon.svg'

export const Navbar = () => {
  const { user, profile, projects, currentProjectId, setCurrentProjectId, signOut } = useAuth()
  const navigate = useNavigate()
  const profileInitial = (profile?.full_name || profile?.email || 'U').charAt(0).toUpperCase()

  const handleSignOut = async () => {
    await signOut()
    navigate('/auth')
  }

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200 fixed top-0 left-0 right-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 gap-4 overflow-x-auto">
          <div className="flex items-center">
            <Link to="/" className="flex items-center" aria-label="DeBUG home">
              <img src={logoIcon} alt="DeBUG logo" className="h-16 w-16" />
              <span className="ml-2 text-3xl leading-none font-bold text-[#3D6BBA]">DeBUG</span>
            </Link>
            {user && (
              <div className="ml-6 flex items-center gap-2 overflow-x-auto whitespace-nowrap pr-2">
                <Link
                  to="/dashboard"
                  className="max-w-28 truncate text-gray-700 hover:text-indigo-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Dashboard
                </Link>
                <Link
                  to="/artifacts"
                  className="max-w-28 truncate text-gray-700 hover:text-indigo-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Artifacts
                </Link>
                <Link
                  to="/bugs"
                  className="max-w-20 truncate text-gray-700 hover:text-indigo-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Bugs
                </Link>
                {profile?.role === 'admin' && (
                  <Link
                    to="/admin"
                    className="max-w-32 truncate text-gray-700 hover:text-indigo-600 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Admin Panel
                  </Link>
                )}
                {projects.length > 0 && (
                  <select
                    value={currentProjectId || ''}
                    onChange={(event) => setCurrentProjectId(event.target.value || null)}
                    className="ml-1 border border-gray-300 rounded-md text-sm px-2 py-1 bg-white text-gray-700"
                    aria-label="Select current project"
                  >
                    {projects.map((project) => (
                      <option key={project.id} value={project.id}>
                        {project.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 whitespace-nowrap">
            {user ? (
              <>
                <Link
                  to="/profile"
                  aria-label="Profile"
                  className="inline-flex h-10 w-10 items-center justify-center overflow-hidden rounded-full border border-gray-300 bg-gray-100"
                >
                  {profile?.avatar_url ? (
                    <img src={profile.avatar_url} alt="Profile" className="h-full w-full object-cover" />
                  ) : (
                    <span className="text-sm font-semibold text-gray-700">{profileInitial}</span>
                  )}
                </Link>
                <button
                  onClick={handleSignOut}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium whitespace-nowrap"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/auth"
                  className="max-w-20 truncate text-gray-700 hover:text-indigo-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Login
                </Link>
                <Link
                  to="/auth?mode=signup"
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium whitespace-nowrap"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
