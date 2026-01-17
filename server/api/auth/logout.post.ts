export default defineEventHandler(async (event) => {
  const token = getCookie(event, 'auth_token')

  if (!token) {
    throw createError({
      statusCode: 401,
      statusMessage: 'No active session'
    })
  }

  deleteCookie(event, 'auth_token')

  return { success: true, message: 'Logged out successfully' }
})
