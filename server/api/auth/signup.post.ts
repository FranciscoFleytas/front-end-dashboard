export default defineEventHandler(async (event) => {
  const body = await readBody(event)

  if (!body.name || !body.email || !body.password) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Name, email and password are required'
    })
  }

  if (body.password.length < 8) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Password must be at least 8 characters'
    })
  }

  await new Promise(resolve => setTimeout(resolve, 500))

  setCookie(event, 'auth_token', 'mock-jwt-token', {
    httpOnly: true,
    maxAge: 60 * 60 * 24 * 7
  })

  return {
    user: {
      id: Date.now(),
      name: body.name,
      email: body.email,
      avatar: null
    },
    token: 'mock-jwt-token'
  }
})
