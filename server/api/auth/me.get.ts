export default defineEventHandler(async (event) => {
  const token = getCookie(event, 'auth_token')

  if (!token || token !== 'mock-jwt-token') {
    throw createError({
      statusCode: 401,
      statusMessage: 'Unauthorized'
    })
  }

  return {
    user: {
      id: 1,
      name: 'Demo User',
      email: 'demo@example.com',
      avatar: 'https://github.com/benjamincanac.png'
    }
  }
})
