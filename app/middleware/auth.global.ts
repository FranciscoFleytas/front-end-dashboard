export default defineNuxtRouteMiddleware((to) => {
  const { isAuthenticated } = useAuth()

  // Rutas protegidas que requieren autenticación
  const protectedRoutes = ['/dashboard']
  const isProtectedRoute = protectedRoutes.some(route => to.path.startsWith(route))

  // Si es una ruta protegida y el usuario no está autenticado
  if (isProtectedRoute && !isAuthenticated.value) {
    return navigateTo('/login')
  }

  // Si está intentando acceder a login/signup y ya está autenticado
  const authRoutes = ['/login', '/signup']
  const isAuthRoute = authRoutes.includes(to.path)

  if (isAuthRoute && isAuthenticated.value) {
    return navigateTo('/dashboard')
  }
})
