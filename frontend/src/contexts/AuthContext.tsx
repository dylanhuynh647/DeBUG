import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import { User } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'
import { api } from '../lib/api'

interface UserProfile {
  id: string
  email: string
  role: 'reporter' | 'developer' | 'admin'
  full_name: string | null
  avatar_url: string | null
  dark_mode?: boolean | null
}

interface AuthContextType {
  user: User | null
  profile: UserProfile | null
  loading: boolean
  signOut: () => Promise<void>
  refreshProfile: () => Promise<void>
  setDarkModePreference: (enabled: boolean) => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const getThemeStorageKey = (userId: string) => `user-theme:${userId}`

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const profileFetchInFlightRef = useRef(false)
  const profileFetchPendingRef = useRef(false)
  const profileFetchTimeoutRef = useRef<number | null>(null)

  const fetchProfile = async () => {
    if (profileFetchInFlightRef.current) {
      profileFetchPendingRef.current = true
      return
    }

    profileFetchInFlightRef.current = true
    try {
      const response = await api.get('/user/me')
      const fetchedProfile = response.data as UserProfile
      const storedTheme = window.localStorage.getItem(getThemeStorageKey(fetchedProfile.id))
      const hasStoredTheme = storedTheme === 'true' || storedTheme === 'false'
      const resolvedDarkMode = hasStoredTheme
        ? storedTheme === 'true'
        : typeof fetchedProfile.dark_mode === 'boolean'
          ? fetchedProfile.dark_mode
          : false

      setProfile({
        ...fetchedProfile,
        dark_mode: resolvedDarkMode,
      })
    } catch (error) {
      console.error('Error fetching profile:', error)
      setProfile(null)
    } finally {
      profileFetchInFlightRef.current = false
      if (profileFetchPendingRef.current) {
        profileFetchPendingRef.current = false
        void fetchProfile()
      }
    }
  }

  const scheduleProfileFetch = () => {
    if (profileFetchTimeoutRef.current) {
      window.clearTimeout(profileFetchTimeoutRef.current)
    }

    profileFetchTimeoutRef.current = window.setTimeout(() => {
      profileFetchTimeoutRef.current = null
      void fetchProfile()
    }, 150)
  }

  const refreshProfile = async () => {
    if (user) {
      await fetchProfile()
    }
  }

  const setDarkModePreference = async (enabled: boolean) => {
    if (!user) {
      return
    }

    const userId = user.id
    document.documentElement.classList.toggle('dark', enabled)
    window.localStorage.setItem(getThemeStorageKey(userId), String(enabled))

    setProfile((current) =>
      current
        ? {
            ...current,
            dark_mode: enabled,
          }
        : current
    )

    try {
      const response = await api.patch('/user/me', { dark_mode: enabled })
      const resolvedDarkMode =
        typeof response.data?.dark_mode === 'boolean'
          ? response.data.dark_mode
          : enabled

      setProfile((current) =>
        current
          ? {
              ...current,
              ...response.data,
              dark_mode: resolvedDarkMode,
            }
          : current
      )
      window.localStorage.setItem(getThemeStorageKey(userId), String(resolvedDarkMode))
    } catch (error) {
      // Keep the optimistic preference so the user's selected theme does not flicker off.
      console.error('Failed to persist theme preference to backend:', error)
    }
  }

  useEffect(() => {
    const loadingTimeout = window.setTimeout(() => {
      setLoading(false)
    }, 5000)

    // Get initial session
    supabase.auth
      .getSession()
      .then(({ data: { session } }) => {
        setUser(session?.user ?? null)
        if (session?.user) {
          scheduleProfileFetch()
        }
      })
      .catch((error) => {
        console.error('Error getting initial session:', error)
        setUser(null)
        setProfile(null)
      })
      .finally(() => {
        window.clearTimeout(loadingTimeout)
        setLoading(false)
      })

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
      if (session?.user) {
        scheduleProfileFetch()
      } else {
        if (profileFetchTimeoutRef.current) {
          window.clearTimeout(profileFetchTimeoutRef.current)
          profileFetchTimeoutRef.current = null
        }
        setProfile(null)
      }
      setLoading(false)
    })

    return () => {
      window.clearTimeout(loadingTimeout)
      if (profileFetchTimeoutRef.current) {
        window.clearTimeout(profileFetchTimeoutRef.current)
      }
      subscription.unsubscribe()
    }
  }, [])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', !!profile?.dark_mode)
  }, [profile?.dark_mode])

  const signOut = async () => {
    await supabase.auth.signOut()
    setUser(null)
    setProfile(null)
    document.documentElement.classList.remove('dark')
  }

  return (
    <AuthContext.Provider value={{ user, profile, loading, signOut, refreshProfile, setDarkModePreference }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
