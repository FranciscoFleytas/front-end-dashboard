import type { User, AuthResponse } from '~/types/auth'

export const useAuth = () => {
  const user = useState<User | null>('user', () => null)
  const loading = useState<boolean>('authLoading', () => false)
  const error = useState<string | null>('authError', () => null)

  const isAuthenticated = computed(() => !!user.value)

  async function login(email: string, password: string, rememberMe: boolean = false) {
    loading.value = true
    error.value = null

    try {
      const response = await $fetch<AuthResponse>('/api/auth/login', {
        method: 'POST',
        body: { email, password, rememberMe }
      })

      user.value = response.user

      // Show success toast
      const toast = useToast()
      toast.add({
        title: 'Welcome back!',
        description: 'You have been logged in successfully.',
        icon: 'i-lucide-check-circle',
        color: 'success'
      })

      return { success: true }
    } catch (err) {
      const errorData = err as { data?: { statusMessage?: string } }
      error.value = errorData.data?.statusMessage || 'Login failed'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  async function signup(name: string, email: string, password: string) {
    loading.value = true
    error.value = null

    try {
      const response = await $fetch<AuthResponse>('/api/auth/signup', {
        method: 'POST',
        body: { name, email, password }
      })

      user.value = response.user

      // Show success toast
      const toast = useToast()
      toast.add({
        title: 'Welcome!',
        description: 'Your account has been created successfully.',
        icon: 'i-lucide-check-circle',
        color: 'success'
      })

      return { success: true }
    } catch (err) {
      const errorData = err as { data?: { statusMessage?: string } }
      error.value = errorData.data?.statusMessage || 'Signup failed'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    const toast = useToast()

    try {
      await $fetch('/api/auth/logout', { method: 'POST' })

      toast.add({
        title: 'Logged out',
        description: 'You have been logged out successfully.',
        icon: 'i-lucide-log-out',
        color: 'neutral'
      })
    } catch {
      // Ignore logout errors
    } finally {
      user.value = null
      navigateTo('/login')
    }
  }

  async function fetchUser() {
    try {
      const response = await $fetch<{ user: User }>('/api/auth/me')
      user.value = response.user
    } catch {
      user.value = null
    }
  }

  // Auto-fetch user on client-side navigation
  if (import.meta.client) {
    onMounted(async () => {
      await fetchUser()
    })
  }

  return {
    user,
    loading,
    error,
    isAuthenticated,
    login,
    signup,
    logout,
    fetchUser
  }
}
