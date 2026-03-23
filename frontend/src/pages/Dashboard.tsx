import { useAuth } from '../contexts/AuthContext'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'

type ProjectMember = {
  user_id: string
  role: 'owner' | 'admin' | 'developer' | 'reporter'
  email?: string | null
  full_name?: string | null
  avatar_url?: string | null
}

type UserSearchResult = {
  id: string
  email?: string | null
  full_name?: string | null
  avatar_url?: string | null
  is_member: boolean
}

const projectRoles: Array<'admin' | 'developer' | 'reporter'> = ['admin', 'developer', 'reporter']

export default function Dashboard() {
  const {
    user,
    profile,
    loading,
    projects,
    currentProject,
    currentProjectId,
    setCurrentProjectId,
    refreshProjects,
  } = useAuth()
  const [projectName, setProjectName] = useState('')
  const [projectDescription, setProjectDescription] = useState('')
  const [memberSearch, setMemberSearch] = useState('')
  const [selectedRoleByUserId, setSelectedRoleByUserId] = useState<Record<string, 'admin' | 'developer' | 'reporter'>>({})

  const canManageMembers = currentProject?.my_role === 'owner'

  const createProjectMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: projectName.trim(),
        description: projectDescription.trim() || null,
      }
      return api.post('/projects', payload)
    },
    onSuccess: async (response) => {
      const newProjectId = response.data?.id as string | undefined
      await refreshProjects()
      if (newProjectId) {
        setCurrentProjectId(newProjectId)
      }
      setProjectName('')
      setProjectDescription('')
      toast.success('Project created')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create project')
    },
  })

  const { data: members, refetch: refetchMembers } = useQuery<ProjectMember[]>({
    queryKey: ['project-members', currentProjectId],
    queryFn: async () => {
      const response = await api.get(`/projects/${currentProjectId}/members`)
      return Array.isArray(response.data) ? response.data : []
    },
    enabled: !!currentProjectId,
  })

  const { data: searchResults } = useQuery<UserSearchResult[]>({
    queryKey: ['project-user-search', currentProjectId, memberSearch],
    queryFn: async () => {
      const response = await api.get(`/projects/${currentProjectId}/users/search`, {
        params: { q: memberSearch.trim() },
      })
      return Array.isArray(response.data) ? response.data : []
    },
    enabled: !!currentProjectId && canManageMembers && memberSearch.trim().length >= 2,
  })

  const addMemberMutation = useMutation({
    mutationFn: async ({ userId, role }: { userId: string; role: 'admin' | 'developer' | 'reporter' }) => {
      return api.post(`/projects/${currentProjectId}/members`, {
        user_id: userId,
        role,
      })
    },
    onSuccess: async () => {
      await refetchMembers()
      toast.success('Member added to project')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to add member')
    },
  })

  const updateRoleMutation = useMutation({
    mutationFn: async ({ userId, role }: { userId: string; role: 'admin' | 'developer' | 'reporter' }) => {
      return api.patch(`/projects/${currentProjectId}/members/${userId}`, { role })
    },
    onSuccess: async () => {
      await refetchMembers()
      toast.success('Member role updated')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update role')
    },
  })

  useEffect(() => {
    const defaults: Record<string, 'admin' | 'developer' | 'reporter'> = {}
    ;(members || []).forEach((member) => {
      if (member.role === 'owner') {
        return
      }
      defaults[member.user_id] = member.role
    })
    setSelectedRoleByUserId(defaults)
  }, [members])

  const sortedProjects = useMemo(
    () => [...projects].sort((a, b) => a.name.localeCompare(b.name)),
    [projects]
  )

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-red-600">You are not logged in.</div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="bg-white shadow rounded-lg p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          Welcome, {profile?.full_name || user?.email}!
        </h1>
        <p className="text-gray-600 mb-4">
          Create projects, switch between them, and manage project-specific roles.
        </p>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="border border-gray-200 rounded-lg p-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Your Projects</h2>
            {sortedProjects.length === 0 ? (
              <p className="text-sm text-gray-500">You are not part of any projects yet.</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                {sortedProjects.map((project) => (
                  <button
                    key={project.id}
                    type="button"
                    onClick={() => setCurrentProjectId(project.id)}
                    className={`w-full text-left rounded-md border px-3 py-2 transition-colors ${
                      currentProjectId === project.id
                        ? 'border-indigo-500 bg-indigo-50'
                        : 'border-gray-200 hover:border-indigo-300'
                    }`}
                  >
                    <p className="text-sm font-semibold text-gray-900">{project.name}</p>
                    <p className="text-xs text-gray-500">Role: {project.my_role}</p>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="border border-gray-200 rounded-lg p-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Create Project</h2>
            <div className="space-y-3">
              <input
                value={projectName}
                onChange={(event) => setProjectName(event.target.value)}
                placeholder="Project name"
                className="block w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
              <textarea
                value={projectDescription}
                onChange={(event) => setProjectDescription(event.target.value)}
                placeholder="Description (optional)"
                rows={3}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
              <button
                type="button"
                disabled={!projectName.trim() || createProjectMutation.isPending}
                onClick={() => createProjectMutation.mutate()}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50"
              >
                {createProjectMutation.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>

          <div className="border border-gray-200 rounded-lg p-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Current Project</h2>
            {currentProject ? (
              <>
                <p className="text-sm font-semibold text-gray-900">{currentProject.name}</p>
                <p className="text-sm text-gray-600 mt-1">{currentProject.description || 'No description'}</p>
                <p className="text-xs text-gray-500 mt-2">Your role: {currentProject.my_role}</p>
              </>
            ) : (
              <p className="text-sm text-gray-500">Select a project to manage members and view bugs.</p>
            )}
          </div>
        </div>

        {currentProject && (
          <div className="mt-6 border border-gray-200 rounded-lg p-4">
            <h2 className="text-lg font-semibold text-gray-900">Project Members</h2>
            <p className="text-sm text-gray-600 mt-1 mb-4">
              Owner can add members and update their roles.
            </p>

            {canManageMembers && (
              <div className="mb-4">
                <input
                  value={memberSearch}
                  onChange={(event) => setMemberSearch(event.target.value)}
                  placeholder="Search users by name or email"
                  className="block w-full max-w-xl px-3 py-2 border border-gray-300 rounded-md text-sm"
                />
                {memberSearch.trim().length >= 2 && (
                  <div className="mt-2 border border-gray-200 rounded-md divide-y max-w-xl">
                    {(searchResults || []).map((searchUser) => {
                      const defaultRole = selectedRoleByUserId[searchUser.id] || 'developer'
                      return (
                        <div key={searchUser.id} className="p-2 flex items-center justify-between gap-2">
                          <div>
                            <p className="text-sm font-medium text-gray-900">{searchUser.full_name || searchUser.email}</p>
                            <p className="text-xs text-gray-500">{searchUser.email}</p>
                          </div>
                          {searchUser.is_member ? (
                            <span className="text-xs text-green-700">Already in project</span>
                          ) : (
                            <div className="flex items-center gap-2">
                              <select
                                value={defaultRole}
                                onChange={(event) =>
                                  setSelectedRoleByUserId((prev) => ({
                                    ...prev,
                                    [searchUser.id]: event.target.value as 'admin' | 'developer' | 'reporter',
                                  }))
                                }
                                className="px-2 py-1 border border-gray-300 rounded text-sm"
                              >
                                {projectRoles.map((role) => (
                                  <option key={role} value={role}>
                                    {role}
                                  </option>
                                ))}
                              </select>
                              <button
                                type="button"
                                onClick={() => addMemberMutation.mutate({ userId: searchUser.id, role: defaultRole })}
                                className="bg-indigo-600 text-white px-3 py-1 rounded text-sm"
                              >
                                Add
                              </button>
                            </div>
                          )}
                        </div>
                      )
                    })}
                    {(searchResults || []).length === 0 && (
                      <div className="p-2 text-sm text-gray-500">No matching users</div>
                    )}
                  </div>
                )}
              </div>
            )}

            <div className="space-y-2">
              {(members || []).map((member) => (
                <div key={member.user_id} className="flex items-center justify-between border border-gray-200 rounded-md p-2">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{member.full_name || member.email || member.user_id}</p>
                    <p className="text-xs text-gray-500">{member.email}</p>
                  </div>
                  {canManageMembers && member.role !== 'owner' ? (
                    <div className="flex items-center gap-2">
                      <select
                        value={selectedRoleByUserId[member.user_id] || member.role}
                        onChange={(event) =>
                          setSelectedRoleByUserId((prev) => ({
                            ...prev,
                            [member.user_id]: event.target.value as 'admin' | 'developer' | 'reporter',
                          }))
                        }
                        className="px-2 py-1 border border-gray-300 rounded text-sm"
                      >
                        {projectRoles.map((role) => (
                          <option key={role} value={role}>
                            {role}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() =>
                          updateRoleMutation.mutate({
                            userId: member.user_id,
                            role: selectedRoleByUserId[member.user_id] || member.role,
                          })
                        }
                        className="bg-gray-900 text-white px-3 py-1 rounded text-sm"
                      >
                        Save
                      </button>
                    </div>
                  ) : (
                    <span className="text-sm font-semibold text-gray-700">{member.role}</span>
                  )}
                </div>
              ))}
              {(members || []).length === 0 && <p className="text-sm text-gray-500">No members found.</p>}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
